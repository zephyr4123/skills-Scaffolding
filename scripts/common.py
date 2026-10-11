"""install.py 与 init_project.py 共用的小工具：frontmatter 读写、内容指纹、受管区块、文件写入。"""

import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SKILLS_DIR = REPO / "skills"
SEED_DIR = REPO / "seed"
CODEX_DIR = REPO / "engines" / "codex"
ENGINES = ("claude-code", "codex")
# 写进种子记忆 metadata.origin 的值，用来认出「这条是脚手架放进来的」
ORIGIN = "skills-scaffolding"

# 每一步的结果等级：已就位 / 需要改（--check）或已改 / 跳过 / 失败
OK, FIX, SKIP, FAIL = "ok", "fix", "skip", "fail"
Result = tuple[str, str]


def print_results(results: list[Result], apply: bool) -> None:
    mark = {OK: "✓", FIX: "已" if apply else "缺", SKIP: "-", FAIL: "✗"}
    for level, msg in results:
        print(f"  {mark[level]} {msg}")

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def split_frontmatter(text: str) -> tuple[dict, str]:
    """解析记忆文件用到的 frontmatter 子集：顶层 `key: value`，外加一层缩进的嵌套 map（如 metadata）。

    不引入 PyYAML：记忆文件的格式由 Claude Code 决定，只用到这个子集。
    """
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fields: dict = {}
    nested: dict | None = None
    for line in m.group(1).splitlines():
        if line.startswith("  ") and nested is not None:
            key, _, value = line.strip().partition(":")
            nested[key.strip()] = value.strip()
            continue
        key, _, value = line.partition(":")
        if value.strip():
            fields[key.strip()] = value.strip()
            nested = None
        else:
            nested = fields[key.strip()] = {}
    return fields, text[m.end():]


def render_frontmatter(fields: dict, body: str) -> str:
    lines = ["---"]
    for key, value in fields.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            lines.extend(f"  {k}: {v}" for k, v in value.items())
        else:
            lines.append(f"{key}: {value}")
    lines.append("---")
    return "\n".join(lines) + "\n" + body


def fingerprint(fields: dict, body: str) -> str:
    """记忆内容的指纹，用来判断「项目有没有改过这条」。

    只看 name、description、type 和正文：metadata 里工具自己维护的字段
    （Claude 的 modified / originSessionId、我们的 scaffold_sha）变了不算改内容。
    """
    meta = fields.get("metadata") if isinstance(fields.get("metadata"), dict) else {}
    key = [fields.get("name", ""), fields.get("description", ""), meta.get("type", ""), body.strip()]
    return text_sha(json.dumps(key, ensure_ascii=False))


def text_sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


# ---------- 受管区块：<!-- tag sha=... --> 内容 <!-- /tag --> ----------

def _block_re(tag: str) -> re.Pattern:
    t = re.escape(tag)
    return re.compile(rf"<!-- {t}(?P<attrs> [^\n]*?)? -->\n(?P<inner>.*?)\n<!-- /{t} -->", re.S)


def read_block(text: str, tag: str) -> tuple[str, str | None] | None:
    """返回 (区块内容, 写入时记录的 sha)；没有该区块返回 None。"""
    m = _block_re(tag).search(text)
    if not m:
        return None
    sha = re.search(r"\bsha=([0-9a-f]+)", m.group("attrs") or "")
    return m.group("inner"), sha.group(1) if sha else None


def upsert_block(text: str, tag: str, inner: str, sha: str | None = None, note: str = "") -> str:
    """区块已存在就原位替换（前后的用户内容不动），否则追加到末尾。"""
    attrs = "".join(f" {a}" for a in (f"sha={sha}" if sha else "", note) if a)
    block = f"<!-- {tag}{attrs} -->\n{inner.strip()}\n<!-- /{tag} -->"
    if _block_re(tag).search(text):
        return _block_re(tag).sub(lambda _: block, text, count=1)
    base = text.rstrip("\n")
    return (base + "\n\n" if base else "") + block + "\n"


def remove_block(text: str, tag: str) -> str:
    stripped = re.sub(r"\n*" + _block_re(tag).pattern, "", text, flags=re.S).strip("\n")
    return stripped + "\n" if stripped else ""


# ---------- 其他 ----------

def write_if_changed(path: Path, text: str) -> bool:
    if path.exists() and not path.is_symlink() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)
    return True


def skill_engines(skill_dir: Path) -> set[str]:
    """读 SKILL.md frontmatter 的 `engines: [...]`；没写视为两个引擎都支持。"""
    fm = _FRONTMATTER_RE.match((skill_dir / "SKILL.md").read_text(encoding="utf-8"))
    m = re.search(r"^engines:\s*\[(.*?)\]\s*$", fm.group(1) if fm else "", re.M)
    if not m:
        return set(ENGINES)
    return {v.strip() for v in m.group(1).split(",") if v.strip()}


def repo_skills() -> dict[str, Path]:
    return {p.parent.name: p.parent for p in sorted(SKILLS_DIR.glob("*/*/SKILL.md"))}


def detect_engines(claude_home: Path, codex_home: Path) -> list[str]:
    """命令在 PATH 上，或配置目录已存在，都算这台机器有该引擎。"""
    found = []
    if shutil.which("claude") or claude_home.is_dir():
        found.append("claude-code")
    if shutil.which("codex") or codex_home.is_dir():
        found.append("codex")
    return found


def find_project_root(start: Path) -> Path:
    """与 Codex hook 用同一个函数定位项目根：装在哪，hook 就去哪找，两边不可能对不上。"""
    spec = importlib.util.spec_from_file_location("project_memory", CODEX_DIR / "project_memory.py")
    hook = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(hook)
    return hook.find_project_root(start.resolve(), Path.home().resolve())
