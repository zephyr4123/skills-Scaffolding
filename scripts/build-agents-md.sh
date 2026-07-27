#!/usr/bin/env bash
# 生成 scaffold/AGENTS.md —— Codex 侧的会话注入入口。
#
# 为什么需要这个文件：
#   Claude Code 的 CLAUDE.md 支持 @import，可以一次引两份（GUIDE + HABITS）；
#   Codex 没有 loader 级 import，且每级目录**最多只读一份**指令文件。
#   所以 Codex 侧需要一份把两者拼好的产物，项目里的 AGENTS.md 符号链接指向它。
#
# 单一来源不变：手改的永远只有 scaffold/GUIDE.md 与 scaffold/HABITS.md，
# 本文件是纯派生产物，由 CI 校验是否与源同步（scripts/build-agents-md.sh --check）。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GUIDE="${REPO_DIR}/scaffold/GUIDE.md"
HABITS="${REPO_DIR}/scaffold/HABITS.md"
OUT="${REPO_DIR}/scaffold/AGENTS.md"

for f in "$GUIDE" "$HABITS"; do
  [ -f "$f" ] || { echo "缺少源文件：$f" >&2; exit 2; }
done

render() {
  cat <<'EOF'
<!-- 本文件由 scripts/build-agents-md.sh 从 scaffold/GUIDE.md + scaffold/HABITS.md 生成，请勿手改。 -->
<!-- 改内容请改那两个源文件，然后跑 bash scripts/build-agents-md.sh 重新生成。 -->

EOF
  cat "$GUIDE"
  printf '\n---\n\n'
  cat "$HABITS"
}

if [ "${1:-}" = "--check" ]; then
  if [ ! -f "$OUT" ]; then
    echo "✗ scaffold/AGENTS.md 不存在，请跑 bash scripts/build-agents-md.sh 生成" >&2
    exit 1
  fi
  if ! render | diff -q - "$OUT" >/dev/null 2>&1; then
    echo "✗ scaffold/AGENTS.md 与源文件不同步" >&2
    echo "  改了 GUIDE.md / HABITS.md 之后要跑：bash scripts/build-agents-md.sh" >&2
    render | diff -u "$OUT" - | head -40 >&2 || true
    exit 1
  fi
  echo "✓ scaffold/AGENTS.md 与源同步"
  exit 0
fi

render > "$OUT"
echo "✓ 已生成 scaffold/AGENTS.md（$(wc -c < "$OUT" | tr -d ' ') 字节 / Codex 默认预算 32768）"
