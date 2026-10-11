#!/usr/bin/env python3
"""Codex SessionStart hook：把当前项目的 .memory/MEMORY.md 索引注入会话上下文。

Codex 只会自动加载 AGENTS.md，且不支持 include；SessionStart hook 的
additionalContext 是官方唯一能把某个文件内容确定性塞进上下文的通道。
读写规则写在全局 AGENTS.md，这里只负责「本项目记忆在哪、索引是什么」。
"""

import json
import os
import sys
from pathlib import Path

MEMORY_DIRNAME = ".memory"
INDEX_FILENAME = "MEMORY.md"
# 与 Claude Code 一致：索引只注入前 200 行，逼索引保持精简
MAX_INDEX_LINES = 200


def find_project_root(cwd: Path, home: Path) -> Path:
    """从 cwd 向上找最近的含 .memory/ 或 .git 的目录，找不到就用 cwd。

    向上查找止于 home（不含 home）：否则 ~/.memory 会变成所有无 git 目录
    共享的一份记忆，破坏项目隔离。
    """
    for d in (cwd, *cwd.parents):
        if d == home and d != cwd:
            break
        if (d / MEMORY_DIRNAME).is_dir() or (d / ".git").exists():
            return d
    return cwd


def build_context(root: Path) -> str:
    mem_dir = root / MEMORY_DIRNAME
    index = mem_dir / INDEX_FILENAME
    lines = [
        "# 项目记忆",
        f"记忆目录：{mem_dir}/（读写规则见 AGENTS.md「项目记忆」一节）",
        "",
    ]
    if not index.is_file():
        lines.append("（本项目还没有记忆。需要写入时创建该目录和 MEMORY.md。）")
        return "\n".join(lines)

    index_lines = index.read_text(encoding="utf-8").splitlines()
    lines.append("## MEMORY.md")
    lines.extend(index_lines[:MAX_INDEX_LINES])
    if len(index_lines) > MAX_INDEX_LINES:
        lines.append(
            f"…（MEMORY.md 共 {len(index_lines)} 行，只注入了前 {MAX_INDEX_LINES} 行；"
            "请把索引精简到 200 行以内）"
        )
    return "\n".join(lines)


def main(stdin, stdout, stderr, home: Path) -> int:
    # Codex 以会话 cwd 作为 hook 的工作目录，stdin 缺失或坏掉时退回进程 cwd
    try:
        cwd = Path(json.load(stdin).get("cwd") or os.getcwd())
    except (json.JSONDecodeError, AttributeError):
        cwd = Path(os.getcwd())

    try:
        root = find_project_root(cwd.resolve(), home.resolve())
        context = build_context(root)
    except OSError as e:
        # 失败放行：记忆注入不了不该阻断会话，但要留下能定位的信息
        print(f"[project-memory] 注入失败 cwd={cwd} error={e!r}", file=stderr)
        return 0

    payload = {
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }
    print(json.dumps(payload, ensure_ascii=False), file=stdout)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.stdin, sys.stdout, sys.stderr, Path.home()))
