#!/usr/bin/env bash
# SessionStart hook：把 scaffold/ 下的注入文件打到 stdout，Claude Code 会将其并入会话上下文
# （插件安装模式下的注入通道；git 仓库模式由 zephyr-scaffold-init 把项目入口文件
#   CLAUDE.local.md / AGENTS.md 做成指向 scaffold/AGENTS.md 的符号链接，二选一即可）
set -euo pipefail

cat "${CLAUDE_PLUGIN_ROOT}/scaffold/GUIDE.md"
echo
echo "---"
echo
cat "${CLAUDE_PLUGIN_ROOT}/scaffold/HABITS.md"
