#!/usr/bin/env bash
# 把仓库 skills/ 下收编的 skill 以符号链接装进 ~/.claude/skills
# 已存在真实目录的跳过（不覆盖本机手动装的东西），旧符号链接会更新为指向本仓库
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET="${HOME}/.claude/skills"
mkdir -p "$TARGET"

for skill in "$REPO_DIR"/skills/*/*/; do
  name="$(basename "$skill")"
  dest="$TARGET/$name"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "跳过 $name（本机已有真实目录，如需接管请先手动删除）"
    continue
  fi
  ln -sfn "${skill%/}" "$dest"
  echo "已链接 $name -> ${skill%/}"
done

echo "完成。catalog/ 里的第三方插件请按各自档案中的安装命令重装。"
