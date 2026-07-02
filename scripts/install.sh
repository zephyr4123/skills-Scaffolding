#!/usr/bin/env bash
# 一键恢复全部 skill（可重复执行，已就位的自动跳过）：
#   1/3 skills/ 收编副本   → 符号链接进 ~/.claude/skills
#   2/3 manifest 的 clone 行 → git clone 进 ~/.claude/skills（已存在则 git pull）
#   3/3 manifest 的 plugin 行 → claude plugin marketplace add + install
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
MANIFEST="${INSTALL_MANIFEST:-$REPO_DIR/install.manifest}"
FAIL=0

echo "== 1/3 链接收编 skill =="
mkdir -p "$TARGET"
for skill in "$REPO_DIR"/skills/*/*/; do
  name="$(basename "$skill")"
  dest="$TARGET/$name"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  跳过 ${name}（本机已有真实目录，如需接管请先手动删除）"
    continue
  fi
  ln -sfn "${skill%/}" "$dest"
  echo "  已链接 $name"
done

echo "== 2/3 克隆 git 来源 skill =="
while read -r _ url name; do
  [ -z "${name:-}" ] && continue
  dest="$TARGET/$name"
  if [ -d "$dest/.git" ]; then
    echo "  更新 $name"
    git -C "$dest" pull --ff-only -q || { echo "  [失败] $name 更新失败"; FAIL=1; }
  elif [ -e "$dest" ]; then
    echo "  跳过 ${name}（已存在非 git 目录）"
  else
    echo "  克隆 $name <- $url"
    git clone -q "$url" "$dest" || { echo "  [失败] $name 克隆失败"; FAIL=1; }
  fi
done < <(grep -E '^clone[[:space:]]' "$MANIFEST" 2>/dev/null || true)

echo "== 3/3 安装第三方插件 =="
if ! command -v claude >/dev/null 2>&1; then
  echo "  [失败] 未找到 claude CLI，请装好 Claude Code 后重跑，或按 catalog/ 档案手动安装"
  FAIL=1
else
  known_mkts="$(claude plugin marketplace list 2>/dev/null || true)"
  installed="$(claude plugin list 2>/dev/null || true)"
  while read -r _ src id; do
    [ -z "${id:-}" ] && continue
    mkt="${id##*@}"
    plugin_name="${id%%@*}"
    if [ "$src" != "-" ] && ! printf '%s' "$known_mkts" | grep -q "$mkt"; then
      echo "  添加市场 $src"
      claude plugin marketplace add "$src" || { echo "  [失败] 市场 $src 添加失败"; FAIL=1; continue; }
    fi
    if printf '%s' "$installed" | grep -q "$plugin_name"; then
      echo "  已装 ${id}，跳过"
    else
      echo "  安装 $id"
      claude plugin install "$id" || { echo "  [失败] $id 安装失败"; FAIL=1; }
    fi
  done < <(grep -E '^plugin[[:space:]]' "$MANIFEST" 2>/dev/null || true)
fi

echo
if [ "$FAIL" -ne 0 ]; then
  echo "完成，但存在失败项（见上方 [失败] 标记）"
  exit 1
fi
echo "全部就位。"
