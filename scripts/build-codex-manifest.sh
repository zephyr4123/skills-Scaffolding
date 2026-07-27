#!/usr/bin/env bash
# 生成 .codex-plugin/plugin.json —— Codex 侧的插件清单。
#
# 为什么需要它：
#   插件模式下，引擎直接读插件清单的 `skills` 数组来注册 skill，
#   **不经过 install.sh 的 `engines:` 过滤**。所以只有一份 .claude-plugin/plugin.json 时，
#   Codex 会把 28 个全注册，包括 5 个只适用 Claude Code 的。
#
#   Codex 按 DISCOVERABLE_PLUGIN_MANIFEST_PATHS 顺序探测清单：
#       .codex-plugin/plugin.json  →  .claude-plugin/plugin.json  →  .cursor-plugin/plugin.json
#   Claude Code 只读 .claude-plugin/plugin.json。
#   所以两份清单共存 = 两个引擎各读各的，各自拿到正确的 skill 集合。
#
# 单一来源不变：手工维护的永远是 .claude-plugin/plugin.json 与各 skill 的 `engines:` 字段；
# 本文件是纯派生产物，由 CI 校验是否与源同步（scripts/build-codex-manifest.sh --check）。
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${REPO_DIR}/.claude-plugin/plugin.json"
OUT="${REPO_DIR}/.codex-plugin/plugin.json"

[ -f "$SRC" ] || { echo "缺少源文件：$SRC" >&2; exit 2; }

render() {
  python3 - "$REPO_DIR" "$SRC" <<'PY'
import json, os, re, sys
repo, src = sys.argv[1], sys.argv[2]
plugin = json.load(open(src, encoding='utf-8'))

def engines_of(rel):
    f = os.path.join(repo, rel, 'SKILL.md')
    try:
        txt = open(f, encoding='utf-8').read()
    except OSError:
        return {'claude-code', 'codex'}          # 读不到就不过滤，宁可多列不要漏
    m = re.match(r'^---\r?\n(.*?)\r?\n---', txt, re.S)
    if not m:
        return {'claude-code', 'codex'}
    em = re.search(r'^engines:\s*\[(.*?)\]\s*$', m.group(1), re.M)
    if not em:
        return {'claude-code', 'codex'}          # 没声明 = 两个引擎都适用
    vals = {v.strip() for v in em.group(1).split(',') if v.strip()}
    return vals or {'claude-code', 'codex'}

codex_skills = [s for s in plugin.get('skills', []) if 'codex' in engines_of(s.lstrip('./'))]

out = {
    "name": plugin["name"],
    "description": plugin["description"],
    "version": plugin["version"],
    "author": plugin.get("author", {}),
    "homepage": plugin.get("homepage", ""),
    "license": plugin.get("license", ""),
    "_comment": ("本文件由 scripts/build-codex-manifest.sh 从 .claude-plugin/plugin.json "
                 "与各 skill 的 engines: 字段生成，请勿手改。"
                 "只列 Codex 适用的 skill —— Claude 侧读 .claude-plugin/plugin.json 拿全量。"),
    "skills": codex_skills,
}
print(json.dumps(out, ensure_ascii=False, indent=2))
PY
}

if [ "${1:-}" = "--check" ]; then
  if [ ! -f "$OUT" ]; then
    echo "✗ .codex-plugin/plugin.json 不存在，请跑 bash scripts/build-codex-manifest.sh 生成" >&2
    exit 1
  fi
  if ! render | diff -q - "$OUT" >/dev/null 2>&1; then
    echo "✗ .codex-plugin/plugin.json 与源不同步" >&2
    echo "  改了 plugin.json 的 skills 数组或某个 skill 的 engines: 之后要跑：" >&2
    echo "  bash scripts/build-codex-manifest.sh" >&2
    render | diff -u "$OUT" - | head -30 >&2 || true
    exit 1
  fi
  n=$(python3 -c "import json,sys; print(len(json.load(open('$OUT'))['skills']))")
  echo "✓ .codex-plugin/plugin.json 与源同步（Codex 适用 ${n} 个）"
  exit 0
fi

mkdir -p "$(dirname "$OUT")"
render > "$OUT"
n=$(python3 -c "import json; print(len(json.load(open('$OUT'))['skills']))")
echo "✓ 已生成 .codex-plugin/plugin.json（Codex 适用 ${n} 个 skill）"
