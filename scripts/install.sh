#!/usr/bin/env bash
# 一键恢复全部 skill（可重复执行，已就位的自动跳过）。
# 同时支持 Claude Code 与 Codex —— 只装机器上真正存在的那些引擎。
#
#   1/5 skills/ 收编副本   → 符号链接进各引擎的 skill 根
#   2/5 manifest 的 clone 行 → git clone 一份，再链接进各引擎的 skill 根
#   3/5 manifest 的 plugin 行 → <引擎> plugin marketplace add + install
#   4/5 生成 scaffold/AGENTS.md（Codex 侧注入入口）
#   5/5 mcp/registry.json 的 server → claude mcp add-json 注入 user scope
#       （按裁决仅 Claude Code 侧；幂等，已配置的跳过；凭据 fail-closed，
#         env_required 里的键当前环境缺任何一个就不注入，绝不写入空凭据）
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

LINKED_CLAUDE=0
LINKED_CODEX=0

link_one() {  # $1=源目录 $2=目标根 $3=计数用引擎名
  local src="${1%/}" root="$2" which="$3" name dest
  name="$(basename "$src")"
  dest="${root}/${name}"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "  跳过 ${name}（本机已有真实目录，如需接管请先手动删除）"
    return
  fi
  # 符号链接一律重建：ln -sfn 幂等，目标不变，只刷新 mtime
  ln -sfn "$src" "$dest"
  echo "  [${which}] 已链接 ${name}"
  case "$which" in
    claude) LINKED_CLAUDE=$((LINKED_CLAUDE+1)) ;;
    codex)  LINKED_CODEX=$((LINKED_CODEX+1)) ;;
  esac
}

echo "== 1/5 链接收编 skill =="
[ "$HAS_CLAUDE" -eq 1 ] && mkdir -p "$CLAUDE_ROOT"
[ "$HAS_CODEX" -eq 1 ]  && mkdir -p "$CODEX_ROOT"
for skill in "$REPO_DIR"/skills/*/*/; do
  eng="$(skill_engines "${skill%/}")"
  if [ "$HAS_CLAUDE" -eq 1 ]; then
    case "$eng" in *claude-code*) link_one "$skill" "$CLAUDE_ROOT" claude ;; esac
  fi
  if [ "$HAS_CODEX" -eq 1 ]; then
    case "$eng" in
      *codex*) link_one "$skill" "$CODEX_ROOT" codex ;;
      *) echo "  略过 $(basename "${skill%/}") → Codex（该 skill 标了仅 Claude Code 可用）" ;;
    esac
  fi
done

echo "== 2/5 克隆 git 来源 skill =="
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

echo "== 3/5 安装第三方插件 =="
# Claude Code:  claude plugin marketplace add / claude plugin install
# Codex:        codex  plugin marketplace add / codex  plugin add
# 实测：Codex 原生读 .claude-plugin/marketplace.json 与 plugin.json，所以同一份清单两边通用。
install_plugins() {  # $1=引擎名(claude|codex) $2=安装子命令(install|add) $3=engines 关键字
  local cli="$1" sub="$2" key="$3" known installed
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
  while read -r _ src id eng; do
    [ -z "${id:-}" ] && continue
    # 第 4 列声明适用引擎（省略 = 两个都装）。声明里没有本引擎的**明确跳过、不计失败**——
    # 这类"装不了"由上游仓库形态决定（如只有 plugin.json 没有 marketplace.json，
    # Claude 会自动合成单插件市场、Codex 不会），不是本机环境有问题，
    # 别让它把整体退出码染红、吓得新用户以为全废了。
    if [ -n "${eng:-}" ]; then
      case "$eng" in
        *"$key"*) ;;
        *) echo "  [不适用] ${cli}: ${id} 按清单声明仅适用 ${eng}，跳过（非错误）"; continue ;;
      esac
    fi
    local mkt="${id##*@}" plugin_name="${id%%@*}" known_has_mkt=0 already=0
    case "$known" in *"$mkt"*) known_has_mkt=1 ;; esac
    case "$installed" in *"$plugin_name"*) already=1 ;; esac
    if [ "$known_has_mkt" -eq 0 ]; then
      if [ "$src" = "-" ]; then
        echo "  [未就绪] ${cli}: 内建市场 ${mkt} 尚未落地，${id} 本次跳过"
        if [ "$cli" = "claude" ]; then
          # 实测：Anthropic 官方市场只在**交互式 TUI 首次启动**时落地，-p/脚本模式不触发。
          # 只打「跳过」太轻，新用户会当成正常而漏装。
          echo "           → 先在终端起一次交互式 \`claude\`（进到界面即可，然后退出），再重跑本脚本"
        fi
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
[ "$HAS_CLAUDE" -eq 1 ] && install_plugins claude install claude-code
[ "$HAS_CODEX" -eq 1 ]  && install_plugins codex  add    codex

echo "== 4/5 生成 Codex 注入入口 =="
if bash "${REPO_DIR}/scripts/build-agents-md.sh" >/dev/null 2>&1; then
  echo "  scaffold/AGENTS.md 已就位"
else
  echo "  [失败] scaffold/AGENTS.md 生成失败"; FAIL=1
fi

echo "== 5/5 注入 MCP server（仅 Claude Code，来源 mcp/registry.json）=="
MCP_OK=0; MCP_ADD=0; MCP_SKIP=0
if [ "$HAS_CLAUDE" -eq 1 ] && command -v claude >/dev/null 2>&1 && command -v python3 >/dev/null 2>&1; then
  # python 只做判定并逐行吐 <动作>TAB<名字>TAB<载荷>，注入动作由 bash 调 claude CLI 执行。
  # 凭据红线：env_required 的键要求已在当前环境（如经 keychain 按需加载）就位，
  # 缺任何一个就 SKIP——宁可不注入，绝不写入空凭据让 server 带病上线。
  while IFS=$'\t' read -r act name payload; do
    [ -z "${act:-}" ] && continue
    case "$act" in
      OK)   echo "  已配置 ${name}，跳过"; MCP_OK=$((MCP_OK+1)) ;;
      SKIP) echo "  [缺凭据] ${name} 需要 ${payload}，本次不注入；键就位后重跑本脚本"; MCP_SKIP=$((MCP_SKIP+1)) ;;
      ADD)
        if claude mcp add-json "$name" "$payload" --scope user >/dev/null 2>&1; then
          echo "  [claude] 已注入 ${name}"; MCP_ADD=$((MCP_ADD+1))
        else
          echo "  [失败] ${name} 注入失败（claude mcp add-json 报错）"; FAIL=1
        fi ;;
    esac
  done < <(REPO_DIR="$REPO_DIR" python3 - <<'PY'
import json, os
reg = json.load(open(os.path.join(os.environ['REPO_DIR'], 'mcp', 'registry.json')))
try:
    existing = json.load(open(os.path.expanduser('~/.claude.json'))).get('mcpServers', {})
except Exception:
    existing = {}
for s in reg.get('servers', []):
    if 'claude-code' not in s.get('engines', []):
        continue
    name = s['name']
    if name in existing:
        print('OK\t' + name + '\t-'); continue
    missing = [k for k in s.get('env_required', []) if not os.environ.get(k)]
    if missing:
        print('SKIP\t' + name + '\t' + ' / '.join(missing)); continue
    cfg = json.loads(json.dumps(s['config']).replace('${HOME}', os.environ['HOME']))
    if s.get('env_required'):
        cfg.setdefault('env', {}).update({k: os.environ[k] for k in s['env_required']})
    print('ADD\t' + name + '\t' + json.dumps(cfg, ensure_ascii=False))
PY
)
else
  if [ "$HAS_CLAUDE" -eq 1 ]; then
    echo "  [跳过] claude CLI 或 python3 不可用，MCP 未处理"
  else
    echo "  [跳过] 本机无 Claude Code（按裁决 Codex 侧暂不做 MCP）"
  fi
fi

echo
# ★ 无论成败都先报「你已经拿到了什么」——只报失败会让新用户以为整个安装废了，
#   而实际上核心的 skill 链接可能早就全部成功了（第三方插件失败不影响它们）。
echo "── 本次结果 ──"
[ "$HAS_CLAUDE" -eq 1 ] && echo "  Claude Code：${LINKED_CLAUDE} 个 skill 已链接进 ${CLAUDE_ROOT}"
[ "$HAS_CODEX" -eq 1 ]  && echo "  Codex：      ${LINKED_CODEX} 个 skill 已链接进 ${CODEX_ROOT}"
[ "$HAS_CLAUDE" -eq 1 ] && echo "  MCP（Claude）：${MCP_OK} 已配置 / ${MCP_ADD} 新注入 / ${MCP_SKIP} 缺凭据跳过"
if [ "$FAIL" -ne 0 ]; then
  echo
  echo "⚠️ 有失败项（见上方 [失败] 标记），但**上面列出的 skill 已经可用**。"
  echo "   失败的通常是第三方插件——它们由各自作者维护，不影响本脚手架自身的 skill。"
  echo "   可按 catalog/ 里对应档案手动安装，或直接重跑本脚本（幂等，只补缺的）。"
  exit 1
fi
echo "  第三方插件：按 install.manifest 处理完毕"
echo
echo "全部就位。"
if [ "$HAS_CODEX" -eq 1 ]; then
  echo
  echo "提示（Codex）：插件自带的 SessionStart hook 默认不被信任，首次启动 Codex 时"
  echo "会弹信任确认屏，选 Trust 之后 GUIDE + HABITS 才会自动注入。仅安装插件不够。"
fi
