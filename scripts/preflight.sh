#!/usr/bin/env bash
# 环境预检查（纯只读，不安装、不下载、不改任何东西）
# 按引擎分别报告：收编 skill、git 来源 skill、第三方插件、Codex 注入入口
# 退出码：0 = 环境完整；1 = 有缺口（按提示跑 install.sh 补齐）
set -uo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CLAUDE_ROOT="${CLAUDE_SKILLS_DIR:-${HOME}/.claude/skills}"
CODEX_ROOT="${CODEX_SKILLS_DIR:-${HOME}/.agents/skills}"
MANIFEST="${INSTALL_MANIFEST:-${REPO_DIR}/install.manifest}"
MISSING=0

HAS_CLAUDE=0
if command -v claude >/dev/null 2>&1 || [ -d "${HOME}/.claude" ]; then HAS_CLAUDE=1; fi
HAS_CODEX=0
if command -v codex >/dev/null 2>&1 || [ -d "${HOME}/.codex" ] || [ -d "${HOME}/.agents" ]; then HAS_CODEX=1; fi

echo "仓库位置：${REPO_DIR}"
if [ "$HAS_CLAUDE" -eq 0 ] && [ "$HAS_CODEX" -eq 0 ]; then
  echo "未检测到任何引擎（既没有 Claude Code 也没有 Codex）"
  exit 1
fi
[ "$HAS_CLAUDE" -eq 1 ] && echo "引擎：Claude Code → ${CLAUDE_ROOT}"
[ "$HAS_CODEX" -eq 1 ]  && echo "引擎：Codex       → ${CODEX_ROOT}"

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
  [ -z "$out" ] && out="claude-code codex"
  echo "$out"
}

check_root() {  # $1=引擎标签 $2=engines关键字 $3=根目录
  local label="$1" key="$2" root="$3"
  local total=0 ok=0 name eng
  echo "== 收编 skill · ${label} =="
  for skill in "$REPO_DIR"/skills/*/*/; do
    eng="$(skill_engines "${skill%/}")"
    case "$eng" in *"$key"*) ;; *) continue ;; esac
    name="$(basename "${skill%/}")"
    total=$((total+1))
    if [ -e "${root}/${name}" ]; then
      ok=$((ok+1))
    else
      echo "  [缺] ${name}"
      MISSING=1
    fi
  done
  echo "  ${ok}/${total} 已就位（该引擎适用的）"
}

[ "$HAS_CLAUDE" -eq 1 ] && check_root "Claude Code" "claude-code" "$CLAUDE_ROOT"
[ "$HAS_CODEX" -eq 1 ]  && check_root "Codex"       "codex"       "$CODEX_ROOT"

echo "== git 来源 skill =="
if [ "$HAS_CLAUDE" -eq 1 ]; then PRIMARY="$CLAUDE_ROOT"; else PRIMARY="$CODEX_ROOT"; fi
gtotal=0; gok=0
while read -r _ url name; do
  [ -z "${name:-}" ] && continue
  gtotal=$((gtotal+1))
  if [ -e "${PRIMARY}/${name}" ]; then
    gok=$((gok+1))
  else
    echo "  [缺] ${name}（来源 ${url}）"
    MISSING=1
  fi
done < <(grep -E '^clone[[:space:]]' "$MANIFEST" 2>/dev/null || true)
echo "  ${gok}/${gtotal} 已就位"

check_plugins() {  # $1=cli
  local cli="$1" installed ptotal=0 pok=0 id
  echo "== 第三方插件 · ${cli} =="
  if ! command -v "$cli" >/dev/null 2>&1; then
    echo "  ${cli} CLI 不可用，插件状态未知"
    MISSING=1
    return
  fi
  installed="$("$cli" plugin list 2>/dev/null || true)"
  # ⚠️ 用 bash 内建 case 匹配，别写成 `printf '%s' "$big" | grep -q`：
  # grep -q 命中即退出 → printf 写大输出时吃 SIGPIPE(141) → pipefail 判整条管道失败，
  # 形成「命中位置越靠前越容易假阴性」的反直觉 bug（实测 codex plugin list 输出 116KB 时稳定误报）。
  while read -r _ _ id; do
    [ -z "${id:-}" ] && continue
    ptotal=$((ptotal+1))
    case "$installed" in
      *"${id%%@*}"*) pok=$((pok+1)) ;;
      *) echo "  [缺] ${id}"; MISSING=1 ;;
    esac
  done < <(grep -E '^plugin[[:space:]]' "$MANIFEST" 2>/dev/null || true)
  echo "  ${pok}/${ptotal} 已装"
}

[ "$HAS_CLAUDE" -eq 1 ] && check_plugins claude
[ "$HAS_CODEX" -eq 1 ]  && check_plugins codex

if [ "$HAS_CODEX" -eq 1 ]; then
  echo "== Codex 注入入口 =="
  if bash "${REPO_DIR}/scripts/build-agents-md.sh" --check >/dev/null 2>&1; then
    echo "  scaffold/AGENTS.md 与源同步"
  else
    echo "  [缺] scaffold/AGENTS.md 未生成或与 GUIDE/HABITS 不同步"
    MISSING=1
  fi
fi

echo
if [ "$MISSING" -ne 0 ]; then
  echo "结论：有缺口 → 运行 bash ${REPO_DIR}/scripts/install.sh 补齐"
  echo "（install.sh 幂等：符号链接会无条件重建但目标不变、已有的真实目录不接管、"
  echo "  已装的插件跳过、已克隆的仓库 git pull——不会重复下载任何东西）"
  exit 1
fi
echo "结论：环境完整，无需任何安装"
