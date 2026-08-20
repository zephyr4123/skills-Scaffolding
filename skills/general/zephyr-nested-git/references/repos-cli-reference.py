#!/usr/bin/env python3
"""repos —— nested-git 拓扑的跨仓 git 运维 CLI（参考实现）。

用法：拷进外层仓根（建议改名 `repos` 并 chmod +x），随外层仓进版本控制。
项目不应依赖「这台机器装了 skill 库」—— CLI 归项目所有，这个文件只是模板。

设计约定见 zephyr-nested-git skill 第四节。红线全部写在代码里，不靠人记：
  - pull 只 --ff-only，绝不自动 merge / rebase
  - push 只 fast-forward，--force 这个选项在代码路径里不存在
  - fetch 失败绝不吞 —— 陈旧数据算出的「同步」比报错更危险
  - 失败一律非 0 退出码
依赖：Python 3.8+ 标准库 + git。
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "repos.json"


# ── 输出 ────────────────────────────────────────────────────────────────────

def c(s, col):
    """终端着色；非 TTY（管道、日志、agent 捕获）时输出纯文本。"""
    codes = {"r": "31", "g": "32", "y": "33", "b": "34", "d": "2"}
    return f"\033[{codes[col]}m{s}\033[0m" if sys.stdout.isatty() else str(s)


def die(msg):
    print(c(msg, "r"), file=sys.stderr)
    sys.exit(1)


# ── manifest：拓扑的唯一真相源 ──────────────────────────────────────────────

def _safe_dir(name, path):
    """nested 位必须落在外层仓内 —— path 来自配置文件，
    不能让一份被改错（或被恶意改动）的 JSON 把 git 操作指到仓外。"""
    p = str(path).rstrip("/")
    if not p or p.startswith("/") or ".." in Path(p).parts:
        die(f"{MANIFEST.name} 的 {name}.path 非法：{path!r}（必须是外层仓内的相对路径）")
    return p


def load_manifest():
    """repos.json → 注册表 name → {dir, url, cfg}。

    `_` 开头的键是注释（JSON 没有注释语法，取证与理由写进 _note），一律跳过。
    改拓扑改 json 不改本文件；这里不允许硬编码任何仓名。"""
    if not MANIFEST.exists():
        die(f"缺 {MANIFEST} —— 多仓拓扑的唯一真相源")
    try:
        data = json.loads(MANIFEST.read_text())
    except json.JSONDecodeError as e:
        die(f"{MANIFEST.name} 不是合法 JSON：{e}")
    out = {}
    for name, cfg in (data.get("repos") or {}).items():
        if name.startswith("_") or not isinstance(cfg, dict):
            continue
        url = cfg.get("url")
        if not url:
            die(f"{MANIFEST.name} 的 {name} 缺 url")
        out[name] = {"dir": _safe_dir(name, cfg.get("path", name)), "url": url, "cfg": cfg}
    if not out:
        die(f"{MANIFEST.name} 里没解析出任何仓（需要顶层 repos.* 条目）")
    return out


def resolve(name):
    """name|all → [(name, reg)]；未知仓名提示可选值，不静默跳过。"""
    reg = load_manifest()
    if name == "all":
        return list(reg.items())
    if name not in reg:
        die(f"未知仓 {name}（有：{', '.join(reg)}）")
    return [(name, reg[name])]


# ── git 基础 ────────────────────────────────────────────────────────────────

def sh(cmd, cwd=None, check=True, capture=True):
    r = subprocess.run(cmd, cwd=cwd, text=True, capture_output=capture)
    if check and r.returncode != 0:
        if capture and r.stderr:
            sys.stderr.write(r.stderr)
        die(f"命令失败（{r.returncode}）：{' '.join(cmd)}")
    return r


def git(dir_, *args, capture=True, check=True):
    """对 nested 仓执行 git 的唯一原语：`git -C <目录>`，本 CLI 自己从不 cd。"""
    return sh(["git", "-C", str(ROOT / dir_), *args], capture=capture, check=check)


def has_git(dir_):
    return (ROOT / dir_ / ".git").exists()


def branch(dir_):
    """当前分支名；**没有可用分支时返回 None**，逼调用方显式处理。

    两种 None：① detached HEAD —— `rev-parse --abbrev-ref HEAD` 返回字面量 "HEAD"，
    把它当分支名传给 `git pull --ff-only origin HEAD`，git 会拉远端默认分支并快进过去，
    正在 bisect / 对着某个 tag 复现问题的现场会被**静默销毁**，而输出还是绿的；
    ② HEAD 指向未诞生分支（clone 了一个还没首推的空远端）—— rev-parse 直接失败，
    不能让这一个仓的 128 把整条 status/sync 带崩。两种都不给「看起来成功」的机会。"""
    r = git(dir_, "rev-parse", "--abbrev-ref", "HEAD", check=False)
    br = r.stdout.strip()
    return None if r.returncode != 0 or br == "HEAD" else br


def dirty_count(dir_):
    return len([l for l in git(dir_, "status", "--short").stdout.splitlines() if l.strip()])


def ensure_remote(dir_, url):
    """每次网络操作前把 origin 归正到 manifest 的 url —— manifest 是权威，
    手工改过的 remote、克隆时用的旧地址，都在这里被拉回来。"""
    git(dir_, "remote", "set-url", "origin", url, check=False)


def _detached(name):
    print(f"{name:18s} {c('⚠ 无可用分支（detached HEAD 或空仓）—— 先 checkout 到分支再来（不猜目标分支）', 'r')}")
    return 1


# ── 动词 ────────────────────────────────────────────────────────────────────

def cmd_doctor(_a):
    """只读体检：manifest 合法性 / 各仓 clone 态 / remote 一致性。发现要动手修的问题退非 0。"""
    bad = 0
    reg = load_manifest()  # 不合法在这里就 die 了
    print(f"manifest  {c('✓', 'g')} {MANIFEST.name}（{len(reg)} 个仓）")
    for name, r in reg.items():
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('· 未 clone（./repos clone all）', 'y')}")
            continue
        cur = git(r["dir"], "remote", "get-url", "origin", check=False).stdout.strip()
        if cur != r["url"]:
            bad += 1
            print(f"{name:18s} {c('✗ remote 与 manifest 不一致（./repos remotes --fix）', 'r')}")
            continue
        br = branch(r["dir"])
        print(f"{name:18s} {c('✓', 'g')} {br or c('detached / 无分支', 'y')}")
    return 1 if bad else 0


def cmd_clone(a):
    """把缺失的仓 clone 到位。承接期的第一条命令 —— 外层 clone 下来是没有代码的。"""
    bad = 0
    for name, r in resolve(a.name):
        d = ROOT / r["dir"]
        if has_git(r["dir"]):
            print(f"{name:18s} {c('✓ 已存在，跳过', 'g')}")
            continue
        if d.exists() and any(d.iterdir()):
            # 有东西但不是 git 仓：可能是手工放的文件、也可能是上次 clone 断在半路。
            # 盖掉它可能销毁没提交的工作 —— 宁可停下来要一次人工确认。
            print(f"{name:18s} {c('⚠ 目录非空但不是 git 仓，不动它（请人工确认）', 'y')}")
            bad += 1
            continue
        print(f"{name:18s} {c('clone', 'b')} {r['url']} → {r['dir']}")
        d.parent.mkdir(parents=True, exist_ok=True)
        rc = sh(["git", "clone", r["url"], str(d)], capture=False, check=False).returncode
        bad += 0 if rc == 0 else 1
        print(f"{name:18s} {c('✓ cloned', 'g') if rc == 0 else c('✗ 失败（看上面 git 的报错）', 'r')}")
    return 1 if bad else 0


def cmd_status(_a):
    """各仓分支 / 领先落后 / 脏数一屏总览。本地对账不联网（要新鲜数据先 sync）。"""
    for name, r in load_manifest().items():
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('未 clone', 'y')}")
            continue
        br = branch(r["dir"])
        if br is None:
            label, sync_s = c("detached / 无分支", "r"), c("—", "d")
        else:
            label = br
            ab = git(r["dir"], "rev-list", "--left-right", "--count",
                     f"origin/{br}...{br}", check=False)
            if ab.returncode == 0 and ab.stdout.strip():
                behind, ahead = ab.stdout.split()
                sync_s = c("同步", "g") if ahead == behind == "0" else c(f"↑{ahead} ↓{behind}", "y")
            else:
                sync_s = c("远端无此分支", "y")
        n = dirty_count(r["dir"])
        last = git(r["dir"], "log", "--oneline", "-1", check=False).stdout.strip()[:42]
        print(f"{name:18s} {label:22s} {sync_s:14s} "
              f"{c(f'{n}脏', 'y') if n else '净':6s} {c(last, 'd')}")
        _warn_prod_drift(name, r, br)
    return 0


def _warn_prod_drift(name, r, br):
    """本地 HEAD 与 manifest 记的 prod_branch 不一致时告警。

    「同步」只说明本地分支追平了它自己的远端，**不说明这条分支就是线上那条**。
    事故形态：在本地旧分支上 grep，据此断言「这一端没有某功能」并往下推了一串结论，
    而线上跑的是另一条 feature 分支。grep 查的是工作副本，不是线上产物 ——
    这是仓库级指针松掉提交级锁定后必须补的那格。"""
    cfg = r.get("cfg") or {}
    prod = cfg.get("prod_branch")
    if not prod:
        return
    ver = cfg.get("prod_version")
    d = r["dir"]
    tail = f"（线上 {ver}）" if ver else ""
    pad = " " * 18
    if br is None:
        print(pad + " " + c(f"⚠ detached HEAD —— 线上分支是 {prod} {tail}", "y"))
    elif br != prod:
        print(pad + " " + c(f"🔴 本地在 {br}，线上跑的是 {prod} {tail}"
                            f" —— 在这里 grep 出的结论不代表线上", "r"))
        print(pad + " " + c(f"  切过去：  git -C {d} checkout {prod}", "d"))


def cmd_fetch(a):
    bad = 0
    for name, r in resolve(a.name):
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('跳过（未 clone）', 'y')}")
            continue
        ensure_remote(r["dir"], r["url"])
        rc = git(r["dir"], "fetch", "origin", capture=False, check=False).returncode
        bad += 0 if rc == 0 else 1
        print(f"{name:18s} {c('✓ fetched', 'g') if rc == 0 else c('✗ fetch 失败（网络 / 凭据，看上面报错）', 'r')}")
    return 1 if bad else 0


def cmd_sync(_a):
    """fetch 全部 + 领先落后一览。只读，不改本地任何分支。

    ⚠️ fetch 失败绝不能被吞掉：远端跟踪 ref 会停在上次成功 fetch 的状态，
    此时算出来的「同步 / 落后 N」是**基于陈旧数据的肯定结论** —— 比报错更危险。"""
    bad = 0
    for name, r in load_manifest().items():
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('未 clone', 'y')}")
            continue
        ensure_remote(r["dir"], r["url"])
        f = git(r["dir"], "fetch", "origin", check=False)
        if f.returncode != 0:
            bad += 1
            tail = (f.stderr or "").strip().splitlines()[-1:] or [""]
            print(f"{name:18s} {c('✗ fetch 失败，不做对账（下面的领先落后一律不可信）', 'r')}")
            print(f"{'':18s} {c(tail[0][:100], 'd')}")
            continue
        br = branch(r["dir"])
        if br is None:
            print(f"{name:18s} {c('detached / 无分支 —— 无可对账分支', 'y')}")
            bad += 1
            continue
        ab = git(r["dir"], "rev-list", "--left-right", "--count",
                 f"origin/{br}...{br}", check=False)
        if ab.returncode == 0 and ab.stdout.strip():
            behind, ahead = ab.stdout.split()
            state = c("同步", "g") if ahead == behind == "0" else c(f"本地↑{ahead} 远端↓{behind}", "y")
        else:
            state = c("远端无此分支（未 push）", "y")
        print(f"{name:18s} {br:22s} {state}")
    return 1 if bad else 0


def cmd_pull(a):
    """只 --ff-only：自动 merge 会在没人看着的时候制造合并提交；分叉就该停下来让人处理。"""
    bad = 0
    for name, r in resolve(a.name):
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('跳过（未 clone）', 'y')}")
            continue
        br = branch(r["dir"])
        if br is None:
            bad += _detached(name)
            continue
        ensure_remote(r["dir"], r["url"])
        rc = git(r["dir"], "pull", "--ff-only", "origin", br, capture=False, check=False).returncode
        bad += 0 if rc == 0 else 1
        print(f"{name:18s} {c('✓ ' + br, 'g') if rc == 0 else c('✗ 失败 —— 非快进则手动合并；也可能是网络/凭据，看上面报错', 'r')}")
    return 1 if bad else 0


def cmd_push(a):
    """push 只做 fast-forward、**绝不 --force**。

    事故形态：远端多出同事的提交（如 CI 配置升级），裸 `push -f` 会把它静默盖掉，
    要等下次流水线跑挂才发现。被拒之后的 SOP：合进来 → 重跑门禁 → 再推。不 force。
    这类歪路收益当场兑现、代价延后转嫁给别人 —— 修路救不了，只能焊死：
    这个选项在本文件的代码路径里不存在。"""
    bad = 0
    for name, r in resolve(a.name):
        if not has_git(r["dir"]):
            print(f"{name:18s} {c('跳过（未 clone）', 'y')}")
            continue
        if dirty_count(r["dir"]):
            print(f"{name:18s} {c('⚠ 有未提交改动，先 commit 再 push', 'y')}")
            bad += 1
            continue
        br = branch(r["dir"])
        if br is None:
            bad += _detached(name)
            continue
        ensure_remote(r["dir"], r["url"])
        print(f"{name:18s} {c('push', 'b')} {br} → {r['url']}")
        # 完整 refspec 写死源和目标，不让分支名被 git 当成 refspec 再解析一遍。
        rc = git(r["dir"], "push", "-u", "origin",
                 f"refs/heads/{br}:refs/heads/{br}", capture=False, check=False).returncode
        bad += 0 if rc == 0 else 1
        print(f"{name:18s} {c('✓ pushed', 'g') if rc == 0 else c('✗ 被拒 —— 非快进则合进来重跑门禁再推，不要 force；也可能是凭据/权限，看上面报错', 'r')}")
    return 1 if bad else 0


def cmd_remotes(a):
    """remote 与 manifest 对账。默认只报告，--fix 才归正。"""
    bad = 0
    for name, r in load_manifest().items():
        if not has_git(r["dir"]):
            continue
        cur = git(r["dir"], "remote", "get-url", "origin", check=False).stdout.strip()
        if cur == r["url"]:
            print(f"{name:18s} {c('✓', 'g')} {cur}")
        elif a.fix:
            git(r["dir"], "remote", "set-url", "origin", r["url"])
            print(f"{name:18s} {c('已归正', 'g')} {r['url']}")
        else:
            bad += 1
            print(f"{name:18s} {c('需 --fix', 'y')} {cur} → {r['url']}")
    return 1 if bad else 0


# ── 入口 ────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(
        prog="repos", description="nested-git 拓扑的跨仓 git 运维 CLI（读 repos.json，改拓扑改 json 不改代码）")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("doctor", help="只读体检：manifest / clone 态 / remote 一致性")
    pc = sub.add_parser("clone", help="clone 缺失的仓；仓名 或 all")
    pc.add_argument("name")
    sub.add_parser("status", help="各仓分支 / 领先落后 / 脏数总览（本地对账不联网）")
    sub.add_parser("sync", help="fetch 全部 + 领先落后一览（fetch 失败的仓不出对账）")
    pf = sub.add_parser("fetch", help="fetch；仓名 或 all")
    pf.add_argument("name")
    pl = sub.add_parser("pull", help="pull --ff-only；仓名 或 all")
    pl.add_argument("name")
    pp = sub.add_parser("push", help="push 当前分支（只 fast-forward，永不 force）；仓名 或 all")
    pp.add_argument("name")
    pr = sub.add_parser("remotes", help="remote 与 manifest 对账")
    pr.add_argument("--fix", action="store_true")
    a = p.parse_args()
    handlers = {"doctor": cmd_doctor, "clone": cmd_clone, "status": cmd_status,
                "sync": cmd_sync, "fetch": cmd_fetch, "pull": cmd_pull,
                "push": cmd_push, "remotes": cmd_remotes}
    rc = handlers[a.cmd](a)
    # 「没写 return 的 handler」若被默认成 0，就是「永远成功」—— push 被拒、clone
    # 全挂都会退 0，上层脚本与 agent 拿着假成功继续跑。所以这里对 None 直接炸。
    if not isinstance(rc, int):
        die(f"内部错误：{a.cmd} 的 handler 没有返回退出码（修代码，别放过它）")
    sys.exit(rc)


if __name__ == "__main__":
    main()
