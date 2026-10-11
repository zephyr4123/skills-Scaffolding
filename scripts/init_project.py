#!/usr/bin/env python3
"""项目层安装：给一个项目装上红线与共享记忆。可重复执行，脚手架更新后重跑即同步。

  两个引擎共享：AGENTS.md 里的红线区块、.memory/ 里的种子记忆（都随 git 走）
  Claude Code ：CLAUDE.md 引用 @AGENTS.md；.claude/settings.local.json 把自动记忆目录指向 .memory，
                原先存在 ~/.claude/projects/ 下的本项目记忆一并搬进 .memory
  Codex       ：项目里不用装东西，全局 hook 会自动找到 .memory（机器层由 install.py 负责）

同步规则：脚手架写入的东西都记了指纹。重跑时项目没改过的跟着脚手架更新，改过的跳过并提示。

用法：python3 scripts/init_project.py [项目目录，默认当前目录] [--check]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from common import (
    FAIL, FIX, OK, ORIGIN, SEED_DIR, SKIP, Result, detect_engines, find_project_root, fingerprint,
    print_results, read_block, render_frontmatter, split_frontmatter, text_sha, upsert_block,
    write_if_changed,
)

REDLINES_TAG = "skills-scaffolding:redlines"
REDLINES_NOTE = "由 skills-scaffolding 写入；可直接修改，改过后脚手架更新会跳过本段"
_LEGACY_CLAUDE_SECTION = re.compile(r"\n*## Skill 脚手架\n(?:@\.claude/(?:skills-guide|habits)\.md\n?)+")


def claude_project_key(root: Path) -> str:
    """Claude Code 在 ~/.claude/projects/ 下给项目起的目录名：路径里非字母数字的字符都换成 -。"""
    return re.sub(r"[^A-Za-z0-9]", "-", str(root))


def _is_legacy_link(p: Path) -> bool:
    # 老版本把 CLAUDE.local.md / AGENTS.md 做成指向脚手架仓库的符号链接
    return p.is_symlink() and "skills-scaffolding" in os.readlink(p)


# ---------- 索引 ----------

def _ensure_index_line(mem: Path, filename: str, line: str) -> bool:
    index = mem / "MEMORY.md"
    text = index.read_text(encoding="utf-8") if index.exists() else ""
    if f"({filename})" in text:
        return False  # 已有条目就不动，措辞可能被 Claude 改过
    write_if_changed(index, (text.rstrip("\n") + "\n" if text.strip() else "") + line + "\n")
    return True


def _drop_index_line(mem: Path, filename: str) -> None:
    index = mem / "MEMORY.md"
    if index.exists():
        lines = index.read_text(encoding="utf-8").splitlines(keepends=True)
        write_if_changed(index, "".join(l for l in lines if f"({filename})" not in l))


# ---------- 各步骤 ----------

def cleanup_legacy(root: Path, apply: bool) -> list[Result]:
    results: list[Result] = []
    for name in ("CLAUDE.local.md", "AGENTS.md"):
        if _is_legacy_link(root / name):
            results.append((FIX, f"移除老的注入链接 {name}"))
            if apply:
                (root / name).unlink()
    for rel in (".claude/skills-guide.md", ".claude/habits.md"):
        if (root / rel).is_symlink():
            results.append((FIX, f"移除更早期的注入链接 {rel}"))
            if apply:
                (root / rel).unlink()

    claude_md = root / "CLAUDE.md"
    if claude_md.is_file() and not claude_md.is_symlink():
        text = claude_md.read_text(encoding="utf-8")
        new = _LEGACY_CLAUDE_SECTION.sub("\n", text)
        if new != text:
            results.append((FIX, "CLAUDE.md 删除早期的「Skill 脚手架」@ 引用（从来没生效过）"))
            if apply:
                write_if_changed(claude_md, new)

    gitignore = root / ".gitignore"
    if gitignore.is_file():
        lines = gitignore.read_text(encoding="utf-8").splitlines(keepends=True)
        kept = [l for l in lines if l.strip() not in ("AGENTS.md", "/AGENTS.md")]
        if kept != lines:
            results.append((FIX, ".gitignore 去掉 AGENTS.md（红线现在要提交进 git，跟项目走）"))
            if apply:
                write_if_changed(gitignore, "".join(kept))
    return results


def migrate_claude_memory(root: Path, claude_home: Path, apply: bool) -> list[Result]:
    """自动记忆目录切到 .memory 之后，Claude 就不再读老位置了，所以先把老记忆搬过来。"""
    old = claude_home / "projects" / claude_project_key(root) / "memory"
    if not old.is_dir():
        return []
    mem = root / ".memory"
    results: list[Result] = []
    movable = []
    for f in sorted(old.glob("*.md")):
        if f.name == "MEMORY.md":
            continue
        if (mem / f.name).exists():
            results.append((SKIP, f"Claude 旧记忆 {f.name} 与 .memory 里的同名文件冲突，没搬，原件留在 {old}"))
        else:
            movable.append(f)
            results.append((FIX, f"搬入 Claude 旧记忆 {f.name}"))
    if not apply:
        return results

    old_index = (old / "MEMORY.md").read_text(encoding="utf-8") if (old / "MEMORY.md").exists() else ""
    for f in movable:
        mem.mkdir(parents=True, exist_ok=True)
        shutil.move(str(f), mem / f.name)
        line = next((l for l in old_index.splitlines() if f"({f.name})" in l), None)
        _ensure_index_line(mem, f.name, line or f"- [{f.stem}]({f.name})")
    if not [p for p in old.iterdir() if p.name != "MEMORY.md"]:
        shutil.rmtree(old)
        results.append((FIX, f"清理已搬空的 Claude 旧记忆目录 {old}"))
    return results


def _seed_state(path: Path) -> tuple[str, str | None]:
    """missing / foreign（项目自己的同名文件）/ edited（脚手架写的但被改过）/ ours（原样未动）。"""
    if not path.exists():
        return "missing", None
    fields, body = split_frontmatter(path.read_text(encoding="utf-8"))
    meta = fields.get("metadata") if isinstance(fields.get("metadata"), dict) else {}
    if meta.get("origin") != ORIGIN:
        return "foreign", None
    if fingerprint(fields, body) != meta.get("scaffold_sha"):
        return "edited", None
    return "ours", meta.get("scaffold_sha")


def sync_seed_memory(root: Path, seed: Path, apply: bool) -> list[Result]:
    mem = root / ".memory"
    seed_mem = seed / "memory"
    seeds = {p.name: p for p in sorted(seed_mem.glob("*.md")) if p.name != "MEMORY.md"}
    seed_index = {}
    for line in (seed_mem / "MEMORY.md").read_text(encoding="utf-8").splitlines():
        m = re.search(r"\(([^)]+\.md)\)", line)
        if m:
            seed_index[m.group(1)] = line

    results: list[Result] = []
    for name, src in seeds.items():
        fields, body = split_frontmatter(src.read_text(encoding="utf-8"))
        sha = fingerprint(fields, body)
        fields.setdefault("metadata", {}).update(origin=ORIGIN, scaffold_sha=sha)
        dst = mem / name
        state, installed_sha = _seed_state(dst)
        if state == "foreign":
            results.append((SKIP, f"{name}：项目里已有同名记忆（不是脚手架写的），未覆盖"))
            continue
        if state == "edited":
            results.append((SKIP, f"{name}：项目改过这条记忆，未跟随脚手架更新"))
            continue
        if state == "missing" or installed_sha != sha:
            results.append((FIX, f"{'写入' if state == 'missing' else '更新'}记忆 {name}"))
            if apply:
                write_if_changed(dst, render_frontmatter(fields, body))
        if f"({name})" not in ((mem / "MEMORY.md").read_text(encoding="utf-8") if (mem / "MEMORY.md").exists() else ""):
            if state != "missing":
                results.append((FIX, f"索引补回 {name}"))
            if apply:
                _ensure_index_line(mem, name, seed_index.get(name, f"- [{name[:-3]}]({name})"))

    # 脚手架撤掉的种子：项目没改过就跟着撤，改过就留着
    for dst in sorted(mem.glob("*.md")) if mem.is_dir() else []:
        if dst.name == "MEMORY.md" or dst.name in seeds:
            continue
        state, _ = _seed_state(dst)
        if state == "ours":
            results.append((FIX, f"移除脚手架已撤掉的记忆 {dst.name}"))
            if apply:
                dst.unlink()
                _drop_index_line(mem, dst.name)
        elif state == "edited":
            results.append((SKIP, f"{dst.name}：脚手架已撤掉这条，但项目改过，保留"))

    return results or [(OK, f"{len(seeds)} 条种子记忆已就位")]


def sync_redlines(root: Path, seed: Path, apply: bool) -> list[Result]:
    agents = root / "AGENTS.md"
    if agents.is_symlink() and not _is_legacy_link(agents):
        return [(SKIP, "AGENTS.md 是指向别处的符号链接，没有写入红线，需要你手动决定")]
    inner = (seed / "redlines.md").read_text(encoding="utf-8").strip()
    sha = text_sha(inner)
    text = agents.read_text(encoding="utf-8") if agents.is_file() and not agents.is_symlink() else ""

    current = read_block(text, REDLINES_TAG)
    if current is not None:
        cur_inner, cur_sha = current
        if text_sha(cur_inner.strip()) != cur_sha:
            return [(SKIP, "AGENTS.md 的红线区块被项目改过，未跟随脚手架更新")]
        if cur_sha == sha:
            return [(OK, "AGENTS.md 红线区块已是最新")]
    if apply:
        if agents.is_symlink():
            agents.unlink()
        write_if_changed(agents, upsert_block(text, REDLINES_TAG, inner, sha=sha, note=REDLINES_NOTE))
    return [(FIX, "AGENTS.md 写入红线区块" if current is None else "AGENTS.md 红线区块更新到新版")]


def claude_entry(root: Path, apply: bool) -> list[Result]:
    results: list[Result] = []
    claude_md = root / "CLAUDE.md"
    if claude_md.is_symlink():
        results.append((SKIP, "CLAUDE.md 是符号链接，没改；请确认它能读到 AGENTS.md"))
    else:
        text = claude_md.read_text(encoding="utf-8") if claude_md.exists() else ""
        if not re.search(r"^@AGENTS\.md\s*$", text, re.M):
            # 项目里同时有 CLAUDE.md 和 AGENTS.md 时 Claude 默认只读 CLAUDE.md，靠这行把红线引进来
            results.append((FIX, "CLAUDE.md 引用 @AGENTS.md"))
            if apply:
                write_if_changed(claude_md, (text.rstrip("\n") + "\n\n" if text.strip() else "") + "@AGENTS.md\n")

    settings = root / ".claude" / "settings.local.json"
    try:
        data = json.loads(settings.read_text(encoding="utf-8")) if settings.exists() else {}
    except json.JSONDecodeError as e:
        results.append((FAIL, f"{settings} 不是合法 JSON，没改；请手动加 autoMemoryDirectory：{e}"))
    else:
        # 只接受绝对路径，所以写进不进 git 的 settings.local.json，每台机器各自写一次
        target = str(root / ".memory")
        if data.get("autoMemoryDirectory") != target:
            results.append((FIX, "Claude 自动记忆目录指向 .memory"))
            if apply:
                data["autoMemoryDirectory"] = target
                write_if_changed(settings, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    if (root / ".git").exists():
        # 不算本机的全局 excludes：项目会被别的机器 clone，必须靠仓库自己的 .gitignore 挡住
        ignored = subprocess.run(
            ["git", "-c", f"core.excludesFile={os.devnull}", "check-ignore", "-q", ".claude/settings.local.json"],
            cwd=root,
        )
        if ignored.returncode == 1:
            results.append((FIX, ".gitignore 加入 .claude/settings.local.json（里面是本机绝对路径）"))
            if apply:
                gitignore = root / ".gitignore"
                text = gitignore.read_text(encoding="utf-8") if gitignore.exists() else ""
                write_if_changed(gitignore, (text.rstrip("\n") + "\n" if text.strip() else "") + ".claude/settings.local.json\n")
    return results or [(OK, "Claude Code 已接入 AGENTS.md 与 .memory")]


def init_project(root: Path, engines: list[str], claude_home: Path, apply: bool, seed: Path = SEED_DIR) -> list[Result]:
    results = cleanup_legacy(root, apply)
    if "claude-code" in engines:
        results += migrate_claude_memory(root, claude_home, apply)
    results += sync_seed_memory(root, seed, apply)
    results += sync_redlines(root, seed, apply)
    if "claude-code" in engines:
        results += claude_entry(root, apply)
    return results


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="skills-scaffolding 项目层安装")
    parser.add_argument("project", nargs="?", default=".", help="项目目录，默认当前目录")
    parser.add_argument("--check", action="store_true", help="只读，列出会做的改动，有改动退出码 1")
    args = parser.parse_args(argv)

    root = find_project_root(Path(args.project))
    if root == Path.home().resolve():
        print("当前目录不在任何项目里（向上没找到 .git 或 .memory），不往家目录里装。")
        return 1
    claude_home = Path.home() / ".claude"
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    engines = detect_engines(claude_home, codex_home)
    print(f"项目：{root}（本机引擎：{'、'.join(engines) or '无'}）")

    apply = not args.check
    results = init_project(root, engines, claude_home, apply)
    print_results(results, apply)
    changed = [m for lvl, m in results if lvl == FIX]
    failed = [m for lvl, m in results if lvl == FAIL]
    print()
    if args.check:
        print(f"会做 {len(changed)} 处改动、{len(failed)} 处失败。" if changed or failed else "已是最新。")
        return 1 if changed or failed else 0
    print(f"完成：{len(changed)} 处改动、{len(failed)} 处失败。" if changed or failed else "已是最新，无改动。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
