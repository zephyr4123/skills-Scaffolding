#!/usr/bin/env bash
# 一键恢复全部 skill（可重复执行，已就位的自动跳过）。
# 同时支持 Claude Code 与 Codex —— 只装机器上真正存在的那些引擎。
#
#   1/4 skills/ 收编副本   → 符号链接进各引擎的 skill 根
#   2/4 manifest 的 clone 行 → git clone 一份，再链接进各引擎的 skill 根
#   3/4 manifest 的 plugin 行 → <引擎> plugin marketplace add + install
#   4/4 生成 scaffold/AGENTS.md（Codex 侧注入入口）
#
# 每个 skill 的 frontmatter 可声明 `engines:`（缺省视为两个引擎都支持）：
#   engines: [claude-code, codex]   两边都链
#   engines: [claude-code]          只链进 Claude Code 的 skill 根
#   engines: [codex]                只链进 Codex 的 skill 根
# 这样 Codex 用户的 skill 列表里不会混进跑不通的 Claude 专属 skill。
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_ROOT="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
CODEX_ROOT="${CODEX_SKILLS_DIR:-${HOME}/.agents/skills}"
MANIFEST="${INSTALL_MANIFEST:-${REPO_DIR}/install.manifest}"
FAIL=0

# —— 引擎探测：CLI 在 PATH 上，或该引擎的 skill 根已存在，都算「这台机器有它」——
HAS_CLAUDE=0
if command -v claude >/dev/null 2>&1 || [ -d "${HOME}/.claude" ]; then HAS_CLAUDE=1; fi
HAS_CODEX=0
if command -v codex >/dev/null 2>&1 || [ -d "${HOME}/.codex" ] || [ -d "${HOME}/.agents" ]; then HAS_CODEX=1; fi

if [ "$HAS_CLAUDE" -eq 0 ] && [ "$HAS_CODEX" -eq 0 ]; then
  echo "两个引擎都没检测到（既没有 claude 也没有 codex）。"
  echo "装好 Claude Code 或 Codex 之后重跑本脚本即可。"
  exit 1
fi

echo "仓库位置：${REPO_DIR}"
[ "$HAS_CLAUDE" -eq 1 ] && echo "检测到 Claude Code → skill 根 ${CLAUDE_ROOT}"
[ "$HAS_CODEX" -eq 1 ]  && echo "检测到 Codex       → skill 根 ${CODEX_ROOT}"
echo

# 读 skill 的 engines 字段（frontmatter 顶层）。缺省 = 两个引擎都支持。
skill_engines() {
  local f="$1/SKILL.md"
  [ -f "$f" ] || { echo "claude-code codex"; return; }
  local line
  line="$(awk '/^---[[:space:]]*$/{n++; next} n==1 && /^engines:/{print; exit}' "$f")"
  if [ -z "$line" ]; then echo "claude-code codex"; return; fi
  local out=""
  case "$line" in *claude-code*) out="claude-code" ;; esac
  case "$line" in *codex*) out="${out} codex" ;; esac
  # 写了 engines 但一个都没认出来 → 当成没写，宁可多链不要漏
  [ -z "$out" ] && out="claude-code codex"
  echo "$out"
}

link_one() {  # $1=源目录 $2=目标根
  local src="${1%/}" root="$2" name dest
  name="$(basename "$src")"
  dest="${root}/${name}"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  跳过 ${name}（本机已有真实目录，如需接管请先手动删除）"
    return
  fi
  ln -sfn "$src" "$dest"
  echo "  已链接 ${name}"
}

echo "== 1/4 链接收编 skill =="
[ "$HAS_CLAUDE" -eq 1 ] && mkdir -p "$CLAUDE_ROOT"
[ "$HAS_CODEX" -eq 1 ]  && mkdir -p "$CODEX_ROOT"
for skill in "$REPO_DIR"/skills/*/*/; do
  eng="$(skill_engines "${skill%/}")"
  if [ "$HAS_CLAUDE" -eq 1 ]; then
    case "$eng" in *claude-code*) link_one "$skill" "$CLAUDE_ROOT" ;; esac
  fi
  if [ "$HAS_CODEX" -eq 1 ]; then
    case "$eng" in
      *codex*) link_one "$skill" "$CODEX_ROOT" ;;
      *) echo "  略过 $(basename "${skill%/}") → Codex（该 skill 标了仅 Claude Code 可用）" ;;
    esac
  fi
done

echo "== 2/4 克隆 git 来源 skill =="
# 只 clone 一份（放主引擎的根），另一个引擎用符号链接指过去，避免同一仓库克隆两遍。
if [ "$HAS_CLAUDE" -eq 1 ]; then PRIMARY="$CLAUDE_ROOT"; else PRIMARY="$CODEX_ROOT"; fi
while read -r _ url name; do
  [ -z "${name:-}" ] && continue
  dest="${PRIMARY}/${name}"
  if [ -d "$dest/.git" ]; then
    echo "  更新 ${name}"
    git -C "$dest" pull --ff-only -q || { echo "  [失败] ${name} 更新失败"; FAIL=1; }
  elif [ -e "$dest" ]; then
    echo "  跳过 ${name}（已存在非 git 目录）"
  else
    echo "  克隆 ${name} <- ${url}"
    git clone -q "$url" "$dest" || { echo "  [失败] ${name} 克隆失败"; FAIL=1; continue; }
  fi
  # 另一个引擎在的话，链过去共用同一份
  if [ "$HAS_CLAUDE" -eq 1 ] && [ "$HAS_CODEX" -eq 1 ]; then
    other="${CODEX_ROOT}/${name}"
    if [ ! -e "$other" ] || [ -L "$other" ]; then ln -sfn "$dest" "$other"; fi
  fi
done < <(grep -E '^clone[[:space:]]' "$MANIFEST" 2>/dev/null || true)

echo "== 3/4 安装第三方插件 =="
# Claude Code:  claude plugin marketplace add / claude plugin install
# Codex:        codex  plugin marketplace add / codex  plugin add
# 实测：Codex 原生读 .claude-plugin/marketplace.json 与 plugin.json，所以同一份清单两边通用。
install_plugins() {  # $1=引擎名(claude|codex) $2=安装子命令(install|add)
  local cli="$1" sub="$2" known installed
  if ! command -v "$cli" >/dev/null 2>&1; then
    echo "  [跳过] 未找到 ${cli} CLI，${cli} 侧插件未处理"
    return
  fi
  known="$("$cli" plugin marketplace list 2>/dev/null || true)"
  installed="$("$cli" plugin list 2>/dev/null || true)"
  # ⚠️ 这里用 bash 内建 case 做子串匹配，**不要**写成 `printf '%s' "$big" | grep -q`：
  # grep -q 匹配到就立刻退出，printf 还在写大输出时会吃 SIGPIPE(141)，
  # 而 `set -o pipefail` 会把整条管道判为失败 —— 形成「匹配越靠前越容易假阴性」的反直觉 bug。
  # （实测：codex plugin list 输出 116KB，命中位置在 1.7KB 处即稳定误报未安装。）
  while read -r _ src id; do
    [ -z "${id:-}" ] && continue
    local mkt="${id##*@}" plugin_name="${id%%@*}" known_has_mkt=0 already=0
    case "$known" in *"$mkt"*) known_has_mkt=1 ;; esac
    case "$installed" in *"$plugin_name"*) already=1 ;; esac
    if [ "$known_has_mkt" -eq 0 ]; then
      if [ "$src" = "-" ]; then
        echo "  [跳过] ${cli}: 市场 ${mkt} 非内建且清单未给来源，${id} 无法安装"
        continue
      fi
      echo "  [${cli}] 添加市场 ${src}"
      "$cli" plugin marketplace add "$src" || { echo "  [失败] ${cli}: 市场 ${src} 添加失败"; FAIL=1; continue; }
    fi
    if [ "$already" -eq 1 ]; then
      echo "  [${cli}] 已装 ${id}，跳过"
    else
      echo "  [${cli}] 安装 ${id}"
      "$cli" plugin "$sub" "$id" || { echo "  [失败] ${cli}: ${id} 安装失败"; FAIL=1; }
    fi
  done < <(grep -E '^plugin[[:space:]]' "$MANIFEST" 2>/dev/null || true)
}
[ "$HAS_CLAUDE" -eq 1 ] && install_plugins claude install
[ "$HAS_CODEX" -eq 1 ]  && install_plugins codex  add

echo "== 4/4 生成 Codex 注入入口 =="
if bash "${REPO_DIR}/scripts/build-agents-md.sh" >/dev/null 2>&1; then
  echo "  scaffold/AGENTS.md 已就位"
else
  echo "  [失败] scaffold/AGENTS.md 生成失败"; FAIL=1
fi

echo
if [ "$FAIL" -ne 0 ]; then
  echo "完成，但存在失败项（见上方 [失败] 标记）"
  exit 1
fi
echo "全部就位。"
if [ "$HAS_CODEX" -eq 1 ]; then
  echo
  echo "提示（Codex）：插件自带的 SessionStart hook 默认不被信任，首次启动 Codex 时"
  echo "会弹信任确认屏，选 Trust 之后 GUIDE + HABITS 才会自动注入。仅安装插件不够。"
fi
