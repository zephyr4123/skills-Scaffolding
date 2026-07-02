#!/usr/bin/env bash
# 环境预检查（纯只读，不安装、不下载、不改任何东西）
# 报告三类东西的就位情况：收编 skill、git 来源 skill、第三方插件
# 退出码：0 = 环境完整；1 = 有缺口（按提示跑 install.sh 补齐）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
MANIFEST="${INSTALL_MANIFEST:-$REPO_DIR/install.manifest}"
MISSING=0

echo "仓库位置：$REPO_DIR"
echo "skill 目录：$TARGET"

echo "== 收编 skill =="
total=0; ok=0
for skill in "$REPO_DIR"/skills/*/*/; do
  name="$(basename "$skill")"
  total=$((total+1))
  if [ -e "$TARGET/$name" ]; then
    ok=$((ok+1))
  else
    echo "  [缺] $name"
    MISSING=1
  fi
done
echo "  $ok/$total 已就位"

echo "== git 来源 skill =="
gtotal=0; gok=0
while read -r _ url name; do
  [ -z "${name:-}" ] && continue
  gtotal=$((gtotal+1))
  if [ -e "$TARGET/$name" ]; then
    gok=$((gok+1))
  else
    echo "  [缺] $name（来源 $url）"
    MISSING=1
  fi
done < <(grep -E '^clone[[:space:]]' "$MANIFEST" 2>/dev/null || true)
echo "  $gok/$gtotal 已就位"

echo "== 第三方插件 =="
if command -v claude >/dev/null 2>&1; then
  installed="$(claude plugin list 2>/dev/null || true)"
  ptotal=0; pok=0
  while read -r _ _ id; do
    [ -z "${id:-}" ] && continue
    ptotal=$((ptotal+1))
    if printf '%s' "$installed" | grep -q "${id%%@*}"; then
      pok=$((pok+1))
    else
      echo "  [缺] $id"
      MISSING=1
    fi
  done < <(grep -E '^plugin[[:space:]]' "$MANIFEST" 2>/dev/null || true)
  echo "  $pok/$ptotal 已装"
else
  echo "  claude CLI 不可用，插件状态未知"
  MISSING=1
fi

echo
if [ "$MISSING" -ne 0 ]; then
  echo "结论：有缺口 → 运行 bash $REPO_DIR/scripts/install.sh 补齐"
  echo "（install.sh 幂等：已就位的链接、已装的插件、已克隆的仓库都会跳过，不会重复下载）"
  exit 1
fi
echo "结论：环境完整，无需任何安装"
