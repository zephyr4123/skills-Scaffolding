#!/usr/bin/env python3
"""机器层安装：每台机器跑一次，按探测到的引擎各装各的。可重复执行，只补缺。

  两个引擎都做：把 skills/ 下适用的 skill 链进引擎的 skill 根、装 install.manifest 里的第三方插件
  Claude Code ：注入 mcp/registry.json 里的 MCP（user scope）。自带的自动记忆保持开启，不动
  Codex       ：上下文窗口写 100 万、关原生 memories、装 SessionStart hook、全局 AGENTS.md 写入记忆读写规则

用法：
  python3 scripts/install.py            安装 / 补缺
  python3 scripts/install.py --check    只读体检：列出缺口，有缺口退出码 1
  python3 scripts/install.py --uninstall 撤掉本脚本装的 skill 链接与 Codex 记忆组件
"""

import argparse
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from common import (
    CODEX_DIR, FAIL, FIX, OK, REPO, SKILLS_DIR, SKIP, Result, detect_engines, print_results, read_block,
    remove_block, repo_skills, skill_engines, upsert_block, write_if_changed,
)

HOOK_FILENAME = "project_memory.py"
RULES_TAG = "skills-scaffolding:codex-memory-rules"
RULES_NOTE = "由 skills-scaffolding/scripts/install.py 写入：改源文件 engines/codex/memory-rules.md 后重装，不要直接改这里"
# 今天之前的研究版（codex-memory-research）用的区块标记，装新版时顺手清掉
_LEGACY_RULES_RE = re.compile(r"\n*<!-- codex-memory:begin.*?<!-- codex-memory:end -->\n?", re.S)
CONTEXT_WINDOW = "1000000"  # 写满 100 万，实际生效多少由 Codex 按模型上限自己截


@dataclass(frozen=True)
class Machine:
    """本机各引擎配置的位置；测试时整体换成临时目录。"""

    home: Path
    codex_home_override: Path | None = None

    @property
    def claude_home(self) -> Path:
        return self.home / ".claude"

    @property
    def codex_home(self) -> Path:
        return self.codex_home_override or self.home / ".codex"

    def skill_root(self, engine: str) -> Path:
        return self.claude_home / "skills" if engine == "claude-code" else self.home / ".agents" / "skills"


# ---------- skill 链接 ----------

def _points_into(link: Path, base: Path) -> bool:
    target = Path(os.readlink(link))
    if not target.is_absolute():
        target = link.parent / target
    return os.path.normpath(target).startswith(os.path.normpath(base) + os.sep)


def link_skills(m: Machine, engine: str, apply: bool) -> list[Result]:
    root = m.skill_root(engine)
    wanted = {n: d for n, d in repo_skills().items() if engine in skill_engines(d)}
    results: list[Result] = []
    for name, src in wanted.items():
        dest = root / name
        if dest.is_symlink() and os.readlink(dest) == str(src):
            continue
        if dest.exists() and not dest.is_symlink():
            results.append((SKIP, f"{name}：本机已有同名真实目录，不接管"))
            continue
        results.append((FIX, f"链接 skill {name}"))
        if apply:
            root.mkdir(parents=True, exist_ok=True)
            if dest.is_symlink():
                dest.unlink()
            dest.symlink_to(src)
    # 仓库里删掉或改成别的引擎专属的 skill，留在 skill 根里的链接要清掉，否则模型会看到失效的 skill
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if p.is_symlink() and p.name not in wanted and _points_into(p, SKILLS_DIR):
                results.append((FIX, f"移除已不适用的 skill 链接 {p.name}"))
                if apply:
                    p.unlink()
    if not any(level == FIX for level, _ in results):
        results.append((OK, f"{len(wanted)} 个 skill 已链接进 {root}"))
    return results


def unlink_skills(m: Machine, engine: str) -> list[Result]:
    root = m.skill_root(engine)
    results = []
    if root.is_dir():
        for p in sorted(root.iterdir()):
            if p.is_symlink() and _points_into(p, SKILLS_DIR):
                p.unlink()
                results.append((FIX, f"移除 skill 链接 {p.name}"))
    return results


# ---------- 第三方插件 ----------

def plugin_installed(engine: str, listing: str, plugin_id: str) -> bool:
    pid = re.escape(plugin_id)
    if engine == "claude-code":
        return bool(re.search(rf"^\s*❯\s+{pid}\s*$", listing, re.M))
    # Codex 的列表会把市场里没装的插件也列出来（状态 not installed），不能只看名字出现没有
    return bool(re.search(rf"^{pid}\s+installed\b", listing, re.M))


def _marketplace_known(engine: str, listing: str, name: str) -> bool:
    n = re.escape(name)
    pattern = rf"^\s*❯\s+{n}\s*$" if engine == "claude-code" else rf"^{n}\s"
    return bool(re.search(pattern, listing, re.M))


def _manifest_plugins(engine: str) -> list[tuple[str, str]]:
    plugins = []
    for line in (REPO / "install.manifest").read_text(encoding="utf-8").splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[0] == "plugin":
            engines = parts[3].split(",") if len(parts) > 3 else ["claude-code", "codex"]
            if engine in engines:
                plugins.append((parts[1], parts[2]))
    return plugins


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=300)


def plugins(engine: str, apply: bool) -> list[Result]:
    cli = "claude" if engine == "claude-code" else "codex"
    wanted = _manifest_plugins(engine)
    if not wanted:
        return []
    if not shutil.which(cli):
        return [(SKIP, f"找不到 {cli} 命令，第三方插件未处理")]
    results: list[Result] = []
    for source, plugin_id in wanted:
        if plugin_installed(engine, _run([cli, "plugin", "list"]).stdout, plugin_id):
            results.append((OK, f"插件 {plugin_id} 已安装"))
            continue
        if not apply:
            results.append((FIX, f"安装插件 {plugin_id}"))
            continue
        market = plugin_id.split("@", 1)[1]
        if not _marketplace_known(engine, _run([cli, "plugin", "marketplace", "list"]).stdout, market):
            if source == "-":
                # 来源写 - 表示引擎内建的市场；Claude 的内建市场只在交互式界面首次启动时才落地
                results.append((FAIL, f"内建市场 {market} 还没落地：先在终端起一次交互式 {cli} 再重跑"))
                continue
            _run([cli, "plugin", "marketplace", "add", source])
        _run([cli, "plugin", "install" if cli == "claude" else "add", plugin_id])
        # 不信退出码：claude plugin marketplace add 失败时也返回 0，装完重新查一遍才算数
        if plugin_installed(engine, _run([cli, "plugin", "list"]).stdout, plugin_id):
            results.append((FIX, f"安装插件 {plugin_id}"))
        else:
            results.append((FAIL, f"插件 {plugin_id} 安装失败，手动步骤见 catalog/ 下对应档案"))
    return results


# ---------- MCP（仅 Claude Code）----------

def mcp(m: Machine, apply: bool) -> list[Result]:
    registry = json.loads((REPO / "mcp" / "registry.json").read_text(encoding="utf-8"))
    claude_json = m.home / ".claude.json"
    existing = json.loads(claude_json.read_text(encoding="utf-8")).get("mcpServers", {}) if claude_json.exists() else {}
    results: list[Result] = []
    for server in registry.get("servers", []):
        name = server["name"]
        if "claude-code" not in server.get("engines", []):
            continue
        if name in existing:
            results.append((OK, f"MCP {name} 已配置"))
            continue
        missing = [k for k in server.get("env_required", []) if not os.environ.get(k)]
        if missing:
            # 凭据 fail-closed：缺任何一把钥匙就不注入，绝不写入空凭据
            results.append((SKIP, f"MCP {name} 缺凭据 {' / '.join(missing)}，键就位后重跑"))
            continue
        if not apply:
            results.append((FIX, f"注入 MCP {name}"))
            continue
        config = json.loads(json.dumps(server["config"]).replace("${HOME}", str(m.home)))
        if server.get("env_required"):
            config.setdefault("env", {}).update({k: os.environ[k] for k in server["env_required"]})
        proc = _run(["claude", "mcp", "add-json", name, json.dumps(config, ensure_ascii=False), "--scope", "user"])
        results.append((FIX, f"注入 MCP {name}") if proc.returncode == 0 else
                       (FAIL, f"MCP {name} 注入失败：{proc.stderr.strip()[:200]}"))
    return results


# ---------- Codex 引擎配置 ----------

def _set_top_level_key(text: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    first_table = next((i for i, l in enumerate(lines) if re.match(r"\s*\[", l)), len(lines))
    for i in range(first_table):
        if re.match(rf"\s*{re.escape(key)}\s*=", lines[i]):
            lines[i] = f"{key} = {value}\n"
            return "".join(lines)
    # 顶层键必须写在第一个表头之前，否则会被 TOML 归进那张表
    at = first_table
    while at > 0 and not lines[at - 1].strip():
        at -= 1
    if at > 0 and not lines[at - 1].endswith("\n"):
        lines[at - 1] += "\n"
    lines.insert(at, f"{key} = {value}\n")
    return "".join(lines)


def _set_table_key(text: str, table: str, key: str, value: str) -> str:
    lines = text.splitlines(keepends=True)
    header = re.compile(rf"\s*\[{re.escape(table)}\]\s*(#.*)?$")
    start = next((i for i, l in enumerate(lines) if header.match(l.rstrip("\n"))), None)
    if start is None:
        base = text.rstrip("\n")
        return (base + "\n\n" if base else "") + f"[{table}]\n{key} = {value}\n"
    end = next((i for i in range(start + 1, len(lines)) if re.match(r"\s*\[", lines[i])), len(lines))
    for i in range(start + 1, end):
        if re.match(rf"\s*{re.escape(key)}\s*=", lines[i]):
            lines[i] = f"{key} = {value}\n"
            return "".join(lines)
    lines.insert(start + 1, f"{key} = {value}\n")
    return "".join(lines)


def codex_config(m: Machine, apply: bool) -> list[Result]:
    path = m.codex_home / "config.toml"
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    new = _set_top_level_key(text, "model_context_window", CONTEXT_WINDOW)
    new = _set_table_key(new, "features", "memories", "false")
    if new == text:
        return [(OK, "config.toml：上下文窗口 100 万、原生 memories 已关闭")]
    if apply:
        write_if_changed(path, new)
    return [(FIX, "config.toml：model_context_window = 1000000、[features] memories = false")]


def _hook_entry(script: Path) -> dict:
    # 定义保持不变：Codex 按 hooks.json 里的定义算信任哈希，改一个字段就要用户重新 /hooks 信任
    return {
        "matcher": "startup|resume|clear|compact",
        "hooks": [{
            "type": "command",
            # -I：hook 以会话 cwd（任意项目目录）运行，防止项目里的同名模块劫持 import
            "command": f"python3 -I {shlex.quote(str(script))}",
            "timeout": 5,
            # 200 行索引约 6000 token；Codex 默认上限 2500，超出会被截成预览
            "additionalContextLimit": 6000,
        }],
    }


def _without_our_hook(groups: list) -> list:
    kept = []
    for group in groups:
        handlers = group.get("hooks", [])
        others = [h for h in handlers if HOOK_FILENAME not in h.get("command", "")]
        if len(others) == len(handlers):
            kept.append(group)
        elif others:
            kept.append({**group, "hooks": others})
    return kept


def _hooks_json_with(m: Machine, entry: dict | None) -> tuple[Path, dict, bool]:
    path = m.codex_home / "hooks.json"
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"hooks": {}}
    hooks = data.setdefault("hooks", {})
    before = json.dumps(hooks, sort_keys=True)
    # 本系统的组永远放在末尾：用户原有组的位置不动，Codex 的信任记录按位置索引
    groups = _without_our_hook(hooks.get("SessionStart", []))
    if entry:
        groups.append(entry)
    if groups:
        hooks["SessionStart"] = groups
    else:
        hooks.pop("SessionStart", None)
    return path, data, json.dumps(hooks, sort_keys=True) != before


def codex_memory(m: Machine, apply: bool) -> list[Result]:
    results: list[Result] = []
    script = m.codex_home / "hooks" / HOOK_FILENAME
    src = (CODEX_DIR / HOOK_FILENAME).read_text(encoding="utf-8")

    path, data, hooks_changed = _hooks_json_with(m, _hook_entry(script))
    if hooks_changed:
        results.append((FIX, "hooks.json 加入项目记忆 SessionStart hook（装完要在 codex 里 /hooks 信任一次）"))
        if apply:
            write_if_changed(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")

    if not script.exists() or script.read_text(encoding="utf-8") != src:
        results.append((FIX, f"安装 hook 脚本 {script}"))
        if apply:
            write_if_changed(script, src)

    agents = m.codex_home / "AGENTS.md"
    text = agents.read_text(encoding="utf-8") if agents.exists() else ""
    rules = (CODEX_DIR / "memory-rules.md").read_text(encoding="utf-8")
    new = upsert_block(_LEGACY_RULES_RE.sub("\n", text), RULES_TAG, rules, note=RULES_NOTE)
    if new != text:
        results.append((FIX, "全局 AGENTS.md 写入 Codex 记忆读写规则"))
        if apply:
            write_if_changed(agents, new)

    return results or [(OK, "项目记忆 hook 与读写规则已就位")]


def uninstall_codex_memory(m: Machine) -> list[Result]:
    results: list[Result] = []
    path, data, changed = _hooks_json_with(m, None)
    if changed:
        write_if_changed(path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        results.append((FIX, "hooks.json 移除项目记忆 hook"))
    script = m.codex_home / "hooks" / HOOK_FILENAME
    if script.exists():
        script.unlink()
        results.append((FIX, f"删除 {script}"))
        try:
            script.parent.rmdir()  # 只在空目录时成功，不碰用户自己放的 hook
        except OSError:
            pass
    agents = m.codex_home / "AGENTS.md"
    if agents.exists() and read_block(agents.read_text(encoding="utf-8"), RULES_TAG):
        write_if_changed(agents, remove_block(agents.read_text(encoding="utf-8"), RULES_TAG))
        results.append((FIX, "全局 AGENTS.md 移除记忆读写规则"))
    return results


# ---------- 入口 ----------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="skills-scaffolding 机器层安装")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="只读体检，有缺口退出码 1")
    mode.add_argument("--uninstall", action="store_true", help="撤掉 skill 链接与 Codex 记忆组件")
    args = parser.parse_args(argv)

    codex_home = os.environ.get("CODEX_HOME")
    m = Machine(Path.home(), Path(codex_home) if codex_home else None)
    engines = detect_engines(m.claude_home, m.codex_home)
    if not engines:
        print("没检测到 Claude Code 或 Codex，装好其中一个后重跑。")
        return 1

    apply = not args.check
    all_results: list[Result] = []
    try:
        for engine in engines:
            print(f"== {'Claude Code' if engine == 'claude-code' else 'Codex'} ==")
            if args.uninstall:
                steps = [unlink_skills(m, engine)] + ([uninstall_codex_memory(m)] if engine == "codex" else [])
            else:
                steps = [link_skills(m, engine, apply), plugins(engine, apply)]
                steps += [mcp(m, apply)] if engine == "claude-code" else [codex_config(m, apply), codex_memory(m, apply)]
            for results in steps:
                print_results(results, apply)
                all_results += results
    except json.JSONDecodeError as e:
        print(f"✗ 某个 JSON 配置文件格式不对，已停止，未写入半截内容：{e}", file=sys.stderr)
        return 1

    gaps = [msg for level, msg in all_results if level == FIX]
    failed = [msg for level, msg in all_results if level == FAIL]
    print()
    if args.check:
        print(f"体检结果：{len(gaps)} 处缺口、{len(failed)} 处失败" if gaps or failed else "体检通过，环境完整。")
        return 1 if gaps or failed else 0
    if apply and any("hooks.json" in g for g in gaps):
        print("⚠️ hook 定义有变化：打开 codex 输入 /hooks，审核并信任 project_memory.py 后才会生效。")
    print(f"完成：{len(gaps)} 处改动、{len(failed)} 处失败。" if gaps or failed else "已是最新，无改动。")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
