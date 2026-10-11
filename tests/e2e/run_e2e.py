#!/usr/bin/env python3
"""端到端验证：用真实的 claude / codex 跑「红线可见、记忆注入、读、写、隔离」场景，逐条给判定和证据。

前提：本机已跑过 scripts/install.py；Codex 侧还要在 codex 里用 /hooks 信任过 project_memory.py。
测试项目由 init_project.py 装好，建在 tests/e2e/.work/ 而不是 /tmp：
Codex 沙盒默认放行 /tmp 写入，会掩盖真实的写权限问题。Codex 调用全部带 --ephemeral，不留会话记录。

用法：python3 tests/e2e/run_e2e.py --engine codex|claude [--repeat 3] [--only R,W]
"""

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from common import split_frontmatter  # noqa: E402
from init_project import init_project  # noqa: E402

WORK = Path(__file__).resolve().parent / ".work"
MEMORY_TYPES = {"user", "feedback", "project", "reference"}
REDLINE_1 = "绝不出现 AI 标识"
NO_TOOLS_HINT = "不要使用任何工具，不要执行命令也不要读文件，只根据你已有的上下文回答。"


# ---------- 调引擎 ----------

@dataclass
class Run:
    prompt: str
    answer: str
    commands: list[str]
    seconds: float


def codex(cwd: Path, prompt: str, scratch: Path) -> Run:
    scratch.mkdir(parents=True, exist_ok=True)
    out = scratch / f"{time.monotonic_ns()}.txt"
    t0 = time.monotonic()
    proc = subprocess.run(
        ["codex", "exec", "--json", "--ephemeral", "--skip-git-repo-check", "-C", str(cwd), "-o", str(out), prompt],
        cwd=cwd, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=900,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"codex exec 失败 cwd={cwd} code={proc.returncode} stderr={proc.stderr[-800:]}")
    commands = []
    for line in proc.stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item") or {}
        if event.get("type") == "item.completed" and item.get("type") == "command_execution":
            commands.append(item.get("command", ""))
    answer = out.read_text(encoding="utf-8") if out.exists() else ""
    return Run(prompt, answer, commands, round(time.monotonic() - t0, 1))


def claude(cwd: Path, prompt: str, scratch: Path, tools: bool = True) -> Run:
    # 提示词走 stdin：--disallowed-tools 是可变长参数，提示词放在它后面会被当成工具名吞掉
    cmd = ["claude", "-p", "--output-format", "json"]
    cmd += ["--permission-mode", "acceptEdits"] if tools else ["--disallowed-tools", "Read,Bash,Glob,Grep,Edit,Write"]
    t0 = time.monotonic()
    proc = subprocess.run(cmd, cwd=cwd, input=prompt, capture_output=True, text=True, timeout=900)
    if proc.returncode != 0:
        raise RuntimeError(f"claude -p 失败 cwd={cwd} code={proc.returncode} stderr={proc.stderr[-800:]}")
    answer = json.loads(proc.stdout).get("result", "")
    return Run(prompt, answer, [], round(time.monotonic() - t0, 1))


# ---------- 测试项目 ----------

def make_project(root: Path, files: dict[str, str]) -> Path:
    for rel, text in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    # claude_home 指向一个空目录：测试项目不该去碰真实 ~/.claude/projects 下的记忆
    init_project(root, ["claude-code", "codex"], WORK / "_no_claude_home", apply=True)
    return root


def add_memory(root: Path, name: str, title: str, desc: str, mtype: str, body: str) -> None:
    doc = f"---\nname: {name}\ndescription: {desc}\nmetadata:\n  type: {mtype}\n---\n\n{body}\n"
    (root / ".memory" / f"{name}.md").write_text(doc, encoding="utf-8")
    with (root / ".memory" / "MEMORY.md").open("a", encoding="utf-8") as f:
        f.write(f"- [{title}]({name}.md) — {desc}\n")


def project_with_memory(root: Path) -> Path:
    """代号只靠索引就能答；部署要读正文；导出那条已过时（v1 已换成 v2）。"""
    make_project(root, {"README.md": "# demo\n", "src/deep/.keep": "", "scripts/export_v2.py": "print('v2')\n"})
    add_memory(root, "codename", "项目代号", "本项目对外代号是「青柠-42」", "project", "本项目对外代号是「青柠-42」。")
    add_memory(root, "deploy", "部署流程", "部署到各环境的命令和禁忌", "project",
               "部署到 stg 用 `make ship ENV=stg`。\n\n**Why:** scripts/deploy.sh 会跳过数据库迁移。\n"
               "**How to apply:** 任何环境都不要直接跑 scripts/deploy.sh。")
    add_memory(root, "export", "数据导出", "导出数据用 scripts/export_v1.py", "reference",
               "导出全部数据：`python scripts/export_v1.py --all`。")
    return root


def plain_project(root: Path) -> Path:
    return make_project(root, {"README.md": "# plain\n", "src/app.py": "def load():\n    return 1\n\n\ndef save(x):\n    return x\n"})


# ---------- 检查工具 ----------

def own_memories(root: Path) -> dict[str, str]:
    """项目自己写的记忆（去掉脚手架的种子和索引）。"""
    d = root / ".memory"
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(d.glob("*.md"))
            if p.name != "MEMORY.md" and "origin: skills-scaffolding" not in p.read_text(encoding="utf-8")}


def memory_type(text: str) -> str | None:
    fields, _ = split_frontmatter(text)
    meta = fields.get("metadata")
    return meta.get("type") if isinstance(meta, dict) else None


def indexed(root: Path, filename: str) -> bool:
    return f"({filename})" in (root / ".memory" / "MEMORY.md").read_text(encoding="utf-8")


def touched(run: Run, needle: str) -> bool:
    return any(needle in c for c in run.commands)


@dataclass
class Result:
    case: str
    ok: bool
    detail: str
    runs: list[Run] = field(default_factory=list)


def check(case: str, cond, detail: str, *runs: Run) -> Result:
    return Result(case, bool(cond), detail, list(runs))


def short(run: Run, n: int = 90) -> str:
    return "答：" + run.answer.strip().replace("\n", " ")[:n]


# ---------- Codex 场景 ----------

def codex_read(base: Path, scratch: Path) -> list[Result]:
    proj = project_with_memory(base / "with-memory")
    other = plain_project(base / "no-memory")
    res = []
    r = codex(proj, NO_TOOLS_HINT + "原样引用「协作红线与工作习惯」里的红线第 1 条。", scratch)
    res.append(check("R0 红线整份可见（不读文件）", REDLINE_1 in r.answer and not r.commands, short(r), r))
    r = codex(proj / "src" / "deep", "这个项目的对外代号是什么？", scratch)
    res.append(check("R1 子目录启动也拿到索引", "青柠-42" in r.answer, short(r), r))
    r = codex(proj, "怎么把这个项目部署到 stg？", scratch)
    res.append(check("R2 需要时读正文", "make ship ENV=stg" in r.answer and touched(r, "deploy.md"),
                     f"读了 deploy.md={touched(r, 'deploy.md')}；{short(r)}", r))
    r = codex(proj, "我要导出全部数据，该运行什么命令？", scratch)
    stale = re.search(r"export_v1.{0,60}(不存在|失效|找不到|没有)|(不存在|失效|找不到|没有).{0,60}export_v1", r.answer, re.S)
    res.append(check("R3 过时记忆先核实", "export_v2" in r.answer and stale, short(r), r))
    r = codex(other, "这个项目的对外代号是什么？", scratch)
    res.append(check("R4 别的项目看不到", "青柠" not in r.answer and not touched(r, "with-memory"), short(r), r))
    return res


def codex_write(base: Path, scratch: Path) -> list[Result]:
    proj = plain_project(base / "fresh")
    sub = proj / "src"
    res = []

    r = codex(sub, "记住：这个项目的数据库迁移一律用 alembic，不要手写 SQL 迁移脚本。", scratch)
    docs = own_memories(proj)
    name, text = next(iter(docs.items()), ("", ""))
    fields, _ = split_frontmatter(text)
    ok = (len(docs) == 1 and not (sub / ".memory").exists() and fields.get("name") == name[:-3]
          and memory_type(text) in MEMORY_TYPES and fields.get("description") and indexed(proj, name))
    res.append(check("W1 「记住」→ 写在项目根、Claude 格式", ok,
                     f"文件={list(docs)} type={memory_type(text)} 子目录误写={(sub / '.memory').exists()}", r))

    before = set(own_memories(proj))
    r = codex(sub, "以后调试别再加 print 了，用 logging 模块——print 会污染我们 CLI 的 stdout 输出协议。", scratch)
    new = {k: v for k, v in own_memories(proj).items() if k not in before}
    doc = next(iter(new.values()), "")
    ok = len(new) == 1 and memory_type(doc) == "feedback" and "Why" in doc and "How to apply" in doc
    res.append(check("W2 纠正 → feedback 带 Why/How", ok, f"新增={list(new)} type={memory_type(doc)}", r))

    snapshot = set(own_memories(proj))
    r = codex(sub, "记住：数据库迁移用 alembic。", scratch)
    res.append(check("W3 重复内容不新建", set(own_memories(proj)) == snapshot, f"文件={list(own_memories(proj))}", r))

    snapshot = set(own_memories(proj))
    r = codex(sub, "记住：src 目录下有 app.py，里面有 load 和 save 两个函数。", scratch)
    res.append(check("W4 代码结构不记", set(own_memories(proj)) == snapshot, short(r, 70), r))

    snapshot = own_memories(proj)
    r = codex(sub, "src/app.py 里有几个函数？", scratch)
    res.append(check("W5 普通任务不乱写", own_memories(proj) == snapshot, short(r, 50), r))

    r = codex(proj, "这个项目的数据库迁移该怎么做？", scratch)
    res.append(check("W6 新会话用上之前的记忆", "alembic" in r.answer.lower(), short(r), r))
    return res


# ---------- Claude 场景 ----------

def claude_suite(base: Path, scratch: Path) -> list[Result]:
    proj = plain_project(base / "claude-proj")
    res = []
    r = claude(proj, NO_TOOLS_HINT + "原样引用「协作红线与工作习惯」里的红线第 1 条。", scratch, tools=False)
    res.append(check("C1 红线经 @AGENTS.md 可见", REDLINE_1 in r.answer, short(r), r))
    r = claude(proj, NO_TOOLS_HINT + "列出你的自动记忆索引（MEMORY.md）里每一条记忆的标题。", scratch, tools=False)
    res.append(check("C2 .memory 索引被当作自动记忆加载", "skill 路由" in r.answer, short(r), r))

    r = claude(proj, "记住：这个项目的数据库迁移一律用 alembic，不要手写 SQL 迁移脚本。", scratch)
    docs = own_memories(proj)
    text = next(iter(docs.values()), "")
    ok = len(docs) >= 1 and memory_type(text) in MEMORY_TYPES and any(indexed(proj, n) for n in docs)
    res.append(check("C3 自动记忆写进项目 .memory", ok, f"文件={list(docs)} type={memory_type(text)}", r))

    r = claude(proj, NO_TOOLS_HINT + "这个项目的数据库迁移该用什么工具？", scratch, tools=False)
    res.append(check("C4 新会话用上刚写的记忆", "alembic" in r.answer.lower(), short(r), r))
    return res


SUITES = {
    "codex": {"R": codex_read, "W": codex_write},
    "claude": {"C": claude_suite},
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--engine", choices=SUITES, required=True)
    parser.add_argument("--repeat", type=int, default=3, help="每组场景独立重复几遍")
    parser.add_argument("--only", help="只跑哪些组，逗号分隔（默认该引擎全部）")
    args = parser.parse_args()

    suites = SUITES[args.engine]
    names = args.only.split(",") if args.only else list(suites)
    work = WORK / args.engine
    shutil.rmtree(work, ignore_errors=True)
    jobs = [(s, i) for s in names for i in range(1, args.repeat + 1)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {(s, i): pool.submit(suites[s], work / f"{s}{i}", work / "_scratch" / f"{s}{i}") for s, i in jobs}
        results = {k: f.result() for k, f in futures.items()}

    passed = total = 0
    for (s, i), rs in sorted(results.items()):
        for r in rs:
            total += 1
            passed += r.ok
            print(f"{'PASS' if r.ok else 'FAIL'}  #{i} {r.case}  |  {r.detail}")
    print(f"\n合计 {passed}/{total} 通过")
    dump = {f"{s}{i}": [asdict(r) for r in rs] for (s, i), rs in results.items()}
    (work / "results.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"完整证据（回答、执行过的命令）：{work / 'results.json'}")
    return 0 if passed == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
