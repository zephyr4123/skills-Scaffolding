#!/usr/bin/env python3
"""multica-read —— 让任意 agent 只读读取 Multica workspace 的持久化记忆。

严格只读：所有 Multica CLI 调用只经 mc() 网关，白名单放行读动词、命中写词即 abort、
subprocess 列表调用无 shell 注入、恒 --output json、副作用仅限本地缓存文件。

用法: python3 mc_read.py <子命令> [flags]   （子命令见 --help / SKILL.md）
"""
import argparse
import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

# ═══════════════ 只读护栏 ═══════════════
# 白名单：允许的读动词(object, subcommand[, sub])。不在其中 → fail-closed 拒绝。
READ_VERBS = {
    ("issue", "list"), ("issue", "get"), ("issue", "search"), ("issue", "children"),
    ("issue", "runs"), ("issue", "run-messages"), ("issue", "usage"),
    ("issue", "comment", "list"), ("issue", "metadata", "list"),
    ("issue", "pull-requests"), ("issue", "subscriber", "list"),
    ("label", "list"), ("label", "get"),
    ("project", "list"), ("project", "get"), ("project", "resource"),
    ("agent", "list"), ("agent", "get"), ("agent", "tasks"),
    ("squad", "list"), ("squad", "get"), ("squad", "member"),
    ("autopilot", "list"), ("autopilot", "get"), ("autopilot", "runs"),
    ("runtime", "list"), ("runtime", "activity"), ("runtime", "usage"),
    ("repo", "list"), ("repo", "get"),
    ("workspace", "list"), ("workspace", "get"), ("workspace", "member"),
    ("auth", "status"), ("user", "get"),
}
# 兜底黑名单：只对"动词位"检查(不碰 flag 值/ID/查询词),命中即 abort。
WRITE_DENY = re.compile(
    r"^(create|update|delete|remove|assign|close|cancel|archive|restore|"
    r"set|switch|rerun|trigger.*|checkout|start|stop|env|add|status)$", re.I)

PROFILE = None
AUDIT = []  # 实发命令序列(可复现/可核对"确实只读")


def _verb_tokens(args):
    v = []
    for a in args:
        if a.startswith("-"):
            break
        v.append(a)
    return v


def mc(*args, want_json=True):
    """唯一 CLI 网关。返回解析后的 JSON(或 None)。"""
    verb = _verb_tokens(args)
    key = next((verb[:n] for n in (3, 2) if tuple(verb[:n]) in READ_VERBS), None)
    if key is None:
        sys.exit(f"[只读护栏] 拒绝非白名单读命令: {' '.join(verb) or '(空)'}")
    # 第 3 层：workspace 只允许 list/get(排除 switch/update)；黑名单查动词位
    non_verb = verb[len(key):]  # 白名单匹配后剩下的(应是 id/查询,不该是写子命令)
    for tok in [key[-1]] + non_verb[:1]:
        if WRITE_DENY.match(tok):
            sys.exit(f"[只读护栏] 命中写动词黑名单: {tok}")
    cmd = ["multica"]
    if PROFILE:
        cmd += ["--profile", PROFILE]
    cmd += list(args)
    if want_json and "--output" not in args:
        cmd += ["--output", "json"]
    AUDIT.append(" ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)  # 列表调用,无 shell 注入
    if r.returncode != 0:
        return None
    if not want_json:
        return r.stdout
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return None


# ═══════════════ 缓存(仅本地文件) ═══════════════
def cache_dir():
    base = os.environ.get("MC_READ_CACHE") or str(pathlib.Path.home() / ".cache" / "multica-read")
    ws = (WS or {}).get("id", "default")
    d = pathlib.Path(base) / (PROFILE or "default") / ws
    d.mkdir(parents=True, exist_ok=True)
    return d


WS = None  # 当前 workspace(bootstrap 后)


# ═══════════════ 工具 ═══════════════
def to_local(iso):
    if not iso:
        return None
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone()
    except (ValueError, AttributeError):
        return None


def fmt_t(iso):
    d = to_local(iso)
    return d.strftime("%m-%d %H:%M:%S") if d else "──────────"


def as_list(x, key):
    if x is None:
        return []
    return x if isinstance(x, list) else x.get(key, [])


EMO = {"done": "✅", "in_progress": "🔄", "backlog": "⬜", "todo": "◻️",
       "in_review": "👀", "blocked": "⛔", "cancelled": "✖️"}


def out(obj, args):
    if getattr(args, "json", False):
        print(json.dumps(obj, ensure_ascii=False, indent=2))
        return True
    return False


# ═══════════════ 身份 / 实体解析 ═══════════════
def resolve_ws(args):
    global WS
    wss = as_list(mc("workspace", "list"), "workspaces") or []
    if getattr(args, "workspace", None):
        w = getattr(args, "workspace")
        WS = next((x for x in wss if w in (x.get("id"), x.get("slug"), x.get("name"))), None)
        if not WS:
            sys.exit(f"[bootstrap] 未找到 workspace: {w}\n候选: {[x.get('name') for x in wss]}")
    else:
        WS = mc("workspace", "get")  # 当前默认
        if not WS and len(wss) == 1:
            WS = wss[0]
    if not WS:
        sys.exit(f"[bootstrap] workspace 歧义,请 --workspace 指定。候选: {[x.get('name') for x in wss]}")
    return wss


def load_entities(refresh=False):
    """id→可读名 映射(members/agents/labels/projects)。缓存。"""
    f = cache_dir() / "entities.json"
    if f.exists() and not refresh:
        return json.loads(f.read_text())
    ent = {"members": {}, "agents": {}, "labels": {}, "projects": {}, "label_meta": {}}
    for m in as_list(mc("workspace", "member", "list"), "members") or []:
        name = m.get("name") or m.get("email") or m.get("id")
        # issue.assignee_id/creator_id 用的是 user_id;member list 的 id 是另一套 → 两个都映射
        for k in (m.get("user_id"), m.get("id")):
            if k:
                ent["members"][k] = name
    for a in as_list(mc("agent", "list"), "agents") or []:
        ent["agents"][a.get("id")] = a.get("name") or a.get("id")
    for l in as_list(mc("label", "list"), "labels") or []:
        ent["labels"][l.get("id")] = l.get("name")
        ent["label_meta"][l.get("name")] = {"id": l.get("id"), "color": l.get("color")}
    for p in as_list(mc("project", "list"), "projects") or []:
        ent["projects"][p.get("id")] = p.get("name") or p.get("id")
    f.write_text(json.dumps(ent, ensure_ascii=False, indent=2))
    return ent


def who(assignee_id, assignee_type, ent):
    if not assignee_id:
        return "未分配"
    if assignee_type == "agent":
        return "🤖" + ent["agents"].get(assignee_id, assignee_id[:8])
    return ent["members"].get(assignee_id, assignee_id[:8])


# ═══════════════ sweep：全量分页取尽 ═══════════════
SKEL = ("id", "identifier", "title", "status", "priority", "assignee_id",
        "assignee_type", "labels", "parent_issue_id", "project_id",
        "created_at", "updated_at")


def do_sweep(args, quiet=False):
    filters = []
    for k in ("status", "priority", "project", "assignee"):
        v = getattr(args, k, None)
        if v:
            filters += [f"--{k}", v]
    for m in getattr(args, "metadata", None) or []:
        filters += ["--metadata", m]
    page = getattr(args, "page_size", 100) or 100
    maxp = getattr(args, "max_pages", 200) or 200
    all_rows, seen, offset, pages = [], set(), 0, 0
    while pages < maxp:
        d = mc("issue", "list", "--limit", str(page), "--offset", str(offset), *filters)
        rows = as_list(d, "issues")
        if not rows:
            break
        new = 0
        for r in rows:
            if r["id"] in seen:
                continue
            seen.add(r["id"])
            all_rows.append({k: r.get(k) for k in SKEL})
            new += 1
        pages += 1
        offset += page
        if len(rows) < page or new == 0:
            break
    # 落盘
    f = cache_dir() / "issues.jsonl"
    f.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in all_rows))
    meta = {"fetched_at": datetime.now(timezone.utc).isoformat(), "count": len(all_rows),
            "pages": pages, "filters": filters, "hit_cap": pages >= maxp}
    (cache_dir() / "sweep_meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2))
    if not quiet:
        cancelled = sum(1 for r in all_rows if r["status"] == "cancelled")
        report = {**meta, "active": len(all_rows) - cancelled, "cancelled": cancelled}
        if not out(report, args):
            cap = "  ⚠️达页数上限,可能有洞" if meta["hit_cap"] else ""
            print(f"sweep: {len(all_rows)} issue(活跃 {len(all_rows)-cancelled} / cancelled {cancelled})"
                  f" · {pages} 页 · fetched {fmt_t(meta['fetched_at'])}{cap}")
    return all_rows


def load_skeleton(args, auto=True):
    f = cache_dir() / "issues.jsonl"
    if not f.exists():
        if auto:
            return do_sweep(args, quiet=True)
        sys.exit("无缓存,先跑 sweep")
    return [json.loads(l) for l in f.read_text().splitlines() if l.strip()]


# ═══════════════ 子命令 ═══════════════
def cmd_bootstrap(args):
    wss = resolve_ws(args)
    info = {"profile": PROFILE or "(default)", "workspace": WS.get("name"),
            "workspace_id": WS.get("id"), "slug": WS.get("slug"),
            "candidates": [w.get("name") for w in wss]}
    if not out(info, args):
        print(f"身份确认 · profile={info['profile']} · workspace=「{info['workspace']}」"
              f"（{len(wss)} 个库可选: {', '.join(info['candidates'])}）")
        print("⚠️ 严格只读：本工具只读取，绝不改动任何 Multica 数据。")


def cmd_map(args):
    resolve_ws(args)
    ent = load_entities(refresh=getattr(args, "refresh_cache", False))
    projects = as_list(mc("project", "list"), "projects") or []
    squads = as_list(mc("squad", "list"), "squads") or []
    agents = as_list(mc("agent", "list"), "agents") or []
    repos = as_list(mc("repo", "list"), "repos") or []
    labels = as_list(mc("label", "list"), "labels") or []
    skel = load_skeleton(args)
    m = {"workspace": WS.get("name"),
         "topology": {"issues": len(skel), "projects": len(projects), "squads": len(squads),
                      "agents": len(agents), "repos": len(repos), "labels": len(labels)},
         "fingerprint": _fingerprint(skel, projects, labels, agents),
         "entities": {"members": ent["members"], "agents": ent["agents"],
                      "projects": ent["projects"]},
         "label_dict": ent["label_meta"],
         "agents_detail": [{"name": a.get("name"), "status": a.get("status")} for a in agents],
         "repos": [r.get("url") for r in repos]}
    if not out(m, args):
        t = m["topology"]
        print(f"【地图】workspace「{m['workspace']}」· 指纹: {m['fingerprint']}")
        print(f"  规模: issue {t['issues']} · project {t['projects']} · squad {t['squads']}"
              f" · agent {t['agents']} · repo {t['repos']} · label {t['labels']}")
        print(f"  标签词典: {', '.join(ent['label_meta'].keys()) or '(无)'}")
        print(f"  agents: {', '.join(a.get('name', '?') for a in agents) or '(无)'}")
        print(f"  实体解析表已缓存({len(ent['members'])} 成员 / {len(ent['agents'])} agent / {len(ent['projects'])} 项目)")


def _fingerprint(skel, projects, labels, agents):
    tags = []
    tags.append("multi-project" if len(projects) > 1 else "single-project")
    tags.append("label-heavy" if len(labels) > 8 else "flat")
    tags.append("has-agents" if agents else "no-agents")
    roots = [r for r in skel if not r.get("parent_issue_id")]
    tags.append("has-tree" if len(roots) < len(skel) else "flat-issues")
    return " · ".join(tags)


def cmd_sweep(args):
    resolve_ws(args)
    do_sweep(args)


def _filter_skel(skel, args, ent):
    rows = skel
    if getattr(args, "status", None):
        rows = [r for r in rows if r["status"] == args.status]
    if not getattr(args, "include_archived", False) and not getattr(args, "status", None):
        if getattr(args, "hot", False):
            rows = [r for r in rows if r["status"] not in ("cancelled", "done")]
        else:
            rows = [r for r in rows if r["status"] != "cancelled"]
    if getattr(args, "priority", None):
        rows = [r for r in rows if r.get("priority") == args.priority]
    if getattr(args, "label", None):
        want = args.label
        rows = [r for r in rows if any(l.get("name") == want for l in (r.get("labels") or []))]
    if getattr(args, "assignee", None):
        rows = [r for r in rows if who(r.get("assignee_id"), r.get("assignee_type"), ent) == args.assignee
                or (r.get("assignee_id") == args.assignee)]
    since, until = getattr(args, "since", None), getattr(args, "until", None)
    tf = getattr(args, "sort", "updated") or "updated"
    tkey = "updated_at" if tf == "updated" else "created_at"
    if since:
        rows = [r for r in rows if (r.get(tkey) or "") >= since]
    if until:
        rows = [r for r in rows if (r.get(tkey) or "") <= until]
    rows = sorted(rows, key=lambda r: r.get(tkey) or "", reverse=True)
    return rows, tkey


def cmd_list(args):
    resolve_ws(args)
    ent = load_entities()
    skel = load_skeleton(args)
    if getattr(args, "hygiene", False):
        return _hygiene(skel, ent, args)
    rows, tkey = _filter_skel(skel, args, ent)
    if getattr(args, "top", None):
        rows = rows[: args.top]
    if out({"count": len(rows), "issues": rows}, args):
        return
    print(f"【list】{len(rows)} 条  (排序: {tkey})")
    for r in rows:
        labs = ",".join(l.get("name", "") for l in (r.get("labels") or []))
        print(f"  {EMO.get(r['status'],'·')} {r['identifier']:<7} {r['title'][:34]:<34} "
              f"· {r.get('priority') or '-':<6} [{labs:<8}] {who(r.get('assignee_id'),r.get('assignee_type'),ent):<12} · {fmt_t(r.get(tkey))}")


def _hygiene(skel, ent, args):
    ids = {r["id"] for r in skel}
    no_assignee = [r for r in skel if not r.get("assignee_id") and r["status"] not in ("done", "cancelled")]
    no_label = [r for r in skel if not (r.get("labels")) and r["status"] not in ("cancelled",)]
    dangling = [r for r in skel if r.get("parent_issue_id") and r["parent_issue_id"] not in ids]
    rep = {"无负责人(未完成)": [r["identifier"] for r in no_assignee],
           "无标签": [r["identifier"] for r in no_label],
           "悬挂子(父不在集合)": [r["identifier"] for r in dangling]}
    if out(rep, args):
        return
    print("【卫生度扫描 · 读“缺什么”】")
    for k, v in rep.items():
        print(f"  {k}: {len(v)}  {', '.join(v[:12])}{' …' if len(v)>12 else ''}")


def cmd_tree(args):
    resolve_ws(args)
    ent = load_entities()
    skel = load_skeleton(args)
    by_id = {r["id"]: r for r in skel}
    kids = {}
    for r in skel:
        p = r.get("parent_issue_id")
        if p and p in by_id:
            kids.setdefault(p, []).append(r)
    orphans = [r for r in skel if r.get("parent_issue_id") and r["parent_issue_id"] not in by_id]
    roots = [r for r in skel if not r.get("parent_issue_id")]
    if getattr(args, "root", None):
        roots = [r for r in skel if r["identifier"] == args.root or r["id"] == args.root]
    num = lambda r: int(r["identifier"].split("-")[1]) if "-" in r["identifier"] else 0
    lines = []

    def walk(r, ind, seen):
        if r["id"] in seen:
            lines.append("  " * ind + f"↻(环) {r['identifier']}")
            return
        seen = seen | {r["id"]}
        labs = ",".join(l.get("name", "") for l in (r.get("labels") or []))
        lines.append("  " * ind + f"{EMO.get(r['status'],'·')} {r['identifier']} {r['title'][:30]} [{labs}]")
        for c in sorted(kids.get(r["id"], []), key=num):
            walk(c, ind + 1, seen)

    for r in sorted(roots, key=num):
        walk(r, 0, set())
    if out({"tree": lines, "orphans": [o["identifier"] for o in orphans]}, args):
        return
    print("\n".join(lines))
    if orphans:
        print(f"\n⚠️ 悬挂子(父不在本集合): {', '.join(o['identifier'] for o in orphans)}")


def cmd_stats(args):
    resolve_ws(args)
    ent = load_entities()
    skel = load_skeleton(args)
    from collections import Counter
    dims = {}
    for by in ("status", "priority"):
        dims[by] = dict(Counter(r.get(by) or "-" for r in skel))
    dims["assignee"] = dict(Counter(who(r.get("assignee_id"), r.get("assignee_type"), ent) for r in skel))
    labc = Counter()
    for r in skel:
        for l in (r.get("labels") or []):
            labc[l.get("name")] += 1
    dims["label"] = dict(labc)
    # 停滞:非终态按 now-updated 分档
    now = datetime.now(timezone.utc)
    stale = []
    for r in skel:
        if r["status"] in ("done", "cancelled"):
            continue
        d = to_local(r.get("updated_at"))
        if d:
            days = (now - d.astimezone(timezone.utc)).days
            if days >= 14:
                stale.append((r["identifier"], days, r.get("priority")))
    stale.sort(key=lambda x: -x[1])
    rep = {"total": len(skel), "distributions": dims,
           "stale_14d+": [{"issue": s[0], "days": s[1], "priority": s[2]} for s in stale]}
    if out(rep, args):
        return
    print(f"【stats】共 {len(skel)} issue")
    for by, c in dims.items():
        print(f"  by {by}: " + " · ".join(f"{k}={v}" for k, v in sorted(c.items(), key=lambda x: -x[1])))
    if stale:
        print(f"  停滞(≥14天未动): " + ", ".join(f"{s[0]}({s[1]}d/{s[2]})" for s in stale[:10]))


def cmd_get(args):
    resolve_ws(args)
    iid = args.id
    issue = mc("issue", "get", iid)
    if not issue:
        sys.exit(f"未找到 issue: {iid}")
    card = {"issue": issue,
            "metadata": mc("issue", "metadata", "list", iid),
            "pull_requests": mc("issue", "pull-requests", iid),
            "subscribers": mc("issue", "subscriber", "list", iid),
            "runs": mc("issue", "runs", iid)}
    mode = getattr(args, "comments", "summary")
    if mode != "none":
        flag = {"summary": ["--summary"], "roots": ["--roots-only"],
                "full": ["--full"], "tail": ["--tail", "20"]}.get(mode, ["--summary"])
        card["comments"] = mc("issue", "comment", "list", iid, *flag)
    if out(card, args):
        return
    print(f"═══ {issue.get('identifier')} · {issue.get('title')} ═══")
    print(f"状态 {issue.get('status')} · 优先级 {issue.get('priority')} · "
          f"创建 {fmt_t(issue.get('created_at'))} · 更新 {fmt_t(issue.get('updated_at'))}")
    print(f"\n{issue.get('description','')[:1500]}")
    cs = as_list(card.get("comments"), "comments")
    if cs:
        print(f"\n── 评论({len(cs)}) ──")
        for c in cs[:12]:
            body = (c.get("content") or "").replace("\n", " ")[:120]
            print(f"  · {fmt_t(c.get('created_at'))} {body}")


COMMIT_RE = re.compile(r"\b([0-9a-f]{7,40})\b|github\.com/[\w.-]+/[\w.-]+/(?:commit|pull)/(\S+)")
CORRECTION_RE = re.compile(r"⚠️|更正|推翻|作废|correction|revert|supersed", re.I)


def cmd_distill(args):
    resolve_ws(args)
    iid = args.id
    mode = getattr(args, "mode", "roots")
    flag = {"roots": ["--roots-only"], "summary": ["--summary"], "full": ["--full"]}.get(mode, ["--roots-only"])
    if getattr(args, "since", None):
        flag += ["--since", args.since]
    data = mc("issue", "comment", "list", iid, *flag)
    comments = sorted(as_list(data, "comments"), key=lambda c: c.get("created_at") or "")
    corrections, commits, concl = [], [], []
    for c in comments:
        body = c.get("content") or ""
        if CORRECTION_RE.search(body):
            corrections.append({"time": c.get("created_at"), "text": body[:200]})
        for m in COMMIT_RE.finditer(body):
            commits.append(m.group(0))
        concl.append({"time": c.get("created_at"), "text": body[:300]})
    rep = {"issue": iid, "conclusions": concl if not getattr(args, "corrections_only", False) else [],
           "corrections_chain": corrections, "commit_refs": sorted(set(commits))}
    if out(rep, args):
        return
    print(f"【distill {iid}】结论 {len(concl)} · ⚠️更正 {len(corrections)} · commit 引用 {len(set(commits))}")
    for c in corrections:
        print(f"  ⚠️ {fmt_t(c['time'])} {c['text'][:100]}")
    if not getattr(args, "corrections_only", False):
        for c in concl[:10]:
            print(f"  · {fmt_t(c['time'])} {c['text'][:100]}")


def cmd_timeline(args):
    resolve_ws(args)
    if getattr(args, "window", None):
        skel = load_skeleton(args)
        fr, to = (args.window.split("..") + [""])[:2]
        rows = sorted([r for r in skel if fr <= (r.get("updated_at") or "") <= (to or "9999")],
                      key=lambda r: r.get("updated_at") or "")
        if out({"window": args.window, "issues": rows}, args):
            return
        print(f"【时间窗活动 {args.window}】{len(rows)} issue 有更新")
        for r in rows:
            print(f"  {fmt_t(r.get('updated_at'))} {EMO.get(r['status'],'·')} {r['identifier']} {r['title'][:30]}")
        return
    iid = args.id
    issue = mc("issue", "get", iid)
    ev = []
    if issue:
        ev.append((issue.get("created_at"), "issue", "创建", issue.get("title", "")[:40]))
        ev.append((issue.get("updated_at"), "issue", "最后更新", ""))
    for c in as_list(mc("issue", "comment", "list", iid, "--full"), "comments"):
        ev.append((c.get("created_at"), "comment", c.get("author_id", "")[:8] if c.get("author_id") else "", (c.get("content") or "").replace("\n", " ")[:60]))
    for run in as_list(mc("issue", "runs", iid), "runs") or as_list(mc("issue", "runs", iid), "tasks"):
        ev.append((run.get("created_at") or run.get("started_at"), "run", run.get("status", ""), f"task {str(run.get('id',''))[:8]}"))
    for pr in as_list(mc("issue", "pull-requests", iid), "pull_requests"):
        ev.append((pr.get("created_at"), "pr", pr.get("state", ""), pr.get("title", "")[:40]))
    ev = sorted([e for e in ev if e[0]], key=lambda e: e[0])
    if out({"issue": iid, "events": [{"time": e[0], "source": e[1], "actor": e[2], "summary": e[3]} for e in ev]}, args):
        return
    print(f"【时间线 {iid}】{len(ev)} 事件")
    for t, src, actor, summ in ev:
        print(f"  {fmt_t(t)} [{src:<7}] {actor:<10} {summ}")


def cmd_runs(args):
    resolve_ws(args)
    if getattr(args, "task", None):
        msgs = mc("issue", "run-messages", args.task, *(["--since", str(args.since_seq)] if getattr(args, "since_seq", None) else []))
        if out(msgs, args):
            return
        for m in as_list(msgs, "messages"):
            print(f"  [{m.get('seq','')}] {m.get('role','')}: {str(m.get('content',''))[:160]}")
        return
    runs = mc("issue", "runs", args.id)
    if out(runs, args):
        return
    rows = as_list(runs, "runs") or as_list(runs, "tasks")
    print(f"【runs {args.id}】{len(rows)} 次执行")
    for r in rows:
        print(f"  task {str(r.get('id',''))[:8]} · {r.get('status','')} · {fmt_t(r.get('created_at') or r.get('started_at'))}")


def cmd_search(args):
    resolve_ws(args)
    flags = []
    if getattr(args, "include_closed", False):
        flags.append("--include-closed")
    if getattr(args, "limit", None):
        flags += ["--limit", str(args.limit)]
    d = mc("issue", "search", args.query, *flags)
    hits = as_list(d, "issues")
    result = {"query": args.query, "hits": hits}
    if getattr(args, "then_comments", False):
        result["comment_hits"] = {}
        for h in hits[:10]:
            cs = as_list(mc("issue", "comment", "list", h["id"], "--summary"), "comments")
            m = [c for c in cs if args.query.lower() in (c.get("content") or "").lower()]
            if m:
                result["comment_hits"][h["identifier"]] = len(m)
    if out(result, args):
        return
    print(f"【search「{args.query}」】{len(hits)} 命中")
    for h in hits:
        print(f"  {EMO.get(h.get('status'),'·')} {h.get('identifier')} {h.get('title','')[:44]}")


def cmd_cost(args):
    resolve_ws(args)
    if getattr(args, "id", None):
        u = mc("issue", "usage", args.id)
        if out(u, args):
            return
        print(f"【cost {args.id}】{json.dumps(u, ensure_ascii=False)}")
        return
    rt = mc("runtime", "list")
    ap = mc("autopilot", "list")
    rep = {"runtimes": as_list(rt, "runtimes"), "autopilots": as_list(ap, "autopilots"),
           "note": "单 issue token 用量用 --id;全量聚合需逐 id 循环 issue usage(开销大,先缩范围)"}
    if out(rep, args):
        return
    print(f"【cost】runtime {len(rep['runtimes'])} · autopilot {len(rep['autopilots'])}")
    print("  (逐 issue token 用量: mc_read.py cost --id <ATW-N>)")


def cmd_delta(args):
    resolve_ws(args)
    wf = cache_dir() / "watermark.json"
    prev = json.loads(wf.read_text()).get("watermark") if wf.exists() else None
    skel = do_sweep(args, quiet=True)
    hi = max((r.get("updated_at") or "" for r in skel), default="")
    changed = [r for r in skel if prev and (r.get("updated_at") or "") > prev]
    rep = {"prev_watermark": prev, "new_watermark": hi,
           "changed_since": [{"id": r["identifier"], "status": r["status"], "updated": r["updated_at"]} for r in changed]}
    if getattr(args, "set_watermark", False):
        wf.write_text(json.dumps({"watermark": hi, "at": datetime.now(timezone.utc).isoformat()}))
        rep["watermark_updated"] = True
    if out(rep, args):
        return
    if not prev:
        print(f"【delta】首次:无水位。当前最高 updated_at={fmt_t(hi)}。用 --set-watermark 记下基线。")
    else:
        print(f"【delta】自 {fmt_t(prev)} 起 {len(changed)} 条变更:")
        for r in changed:
            print(f"  {EMO.get(r['status'],'·')} {r['identifier']} {r['title'][:30]} · {fmt_t(r['updated_at'])}")


def cmd_digest(args):
    resolve_ws(args)
    ent = load_entities()
    skel = load_skeleton(args)
    from collections import Counter
    active = [r for r in skel if r["status"] != "cancelled"]
    dist = dict(Counter(r["status"] for r in active))
    roots = [r for r in active if not r.get("parent_issue_id")]
    hot = sorted(active, key=lambda r: r.get("updated_at") or "", reverse=True)[:8]
    todo = [r for r in active if r["status"] in ("todo", "backlog", "in_progress")]
    lines = []
    lines.append(f"# {WS.get('name')} · 记忆蒸馏(onboarding)")
    lines.append(f"> fetched_at `{fmt_t((json.loads((cache_dir()/'sweep_meta.json').read_text()).get('fetched_at')) if (cache_dir()/'sweep_meta.json').exists() else None)}` · provenance: 结构=native · 时间=秒级真锚 · 分布=derived")
    lines.append(f"\n## 全貌\n- 活跃 {len(active)} / 总 {len(skel)} · 状态分布 {dist}")
    lines.append(f"- 顶层(root)节点 {len(roots)} 个: " + ", ".join(f"{r['identifier']}·{r['title'][:16]}" for r in roots[:8]))
    lines.append("\n## 此刻热点(最近更新 Top8)")
    for r in hot:
        lines.append(f"- {EMO.get(r['status'],'·')} {r['identifier']} {r['title'][:34]} · {fmt_t(r.get('updated_at'))}")
    lines.append(f"\n## 待办/在办({len(todo)})")
    for r in sorted(todo, key=lambda r: (r.get("priority") != "high",)):
        lines.append(f"- {EMO.get(r['status'],'·')} {r['identifier']} {r['title'][:34]} [{r.get('priority')}]")
    lines.append("\n## 深挖指针")
    lines.append("- 全项目树: `mc_read.py tree` · 结论/⚠️更正: `mc_read.py distill --id <X>` · 溯源: `mc_read.py timeline --id <X>`")
    md = "\n".join(lines)
    if out({"markdown": md}, args):
        return
    print(md)


# ═══════════════ dispatch ═══════════════
def main():
    global PROFILE
    # 公共 flag 挂到每个子命令上(写在子命令之后),避开 argparse 全局 flag 位置坑
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--profile", default="personal", help="Multica profile(默认 personal)")
    common.add_argument("--workspace", help="workspace name/id/slug(默认当前)")
    common.add_argument("--json", action="store_true", help="输出 JSON(供脚本消费)")
    common.add_argument("--audit", action="store_true", help="末尾打印本次实发命令(只读自证)")

    p = argparse.ArgumentParser(description="multica-read · 只读读取 Multica 持久化记忆")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add(name, fn, setup=None):
        sp = sub.add_parser(name, parents=[common])
        sp.set_defaults(func=fn)
        if setup:
            setup(sp)
        return sp

    add("bootstrap", cmd_bootstrap)
    add("map", cmd_map, lambda s: s.add_argument("--refresh-cache", action="store_true"))

    def sweep_flags(s):
        for k in ("status", "priority", "project", "assignee"):
            s.add_argument(f"--{k}")
        s.add_argument("--metadata", action="append")
        s.add_argument("--page-size", type=int, default=100)
        s.add_argument("--max-pages", type=int, default=200)
    add("sweep", cmd_sweep, sweep_flags)

    def list_flags(s):
        s.add_argument("--label"); s.add_argument("--status"); s.add_argument("--priority")
        s.add_argument("--assignee"); s.add_argument("--sort", choices=["updated", "created"], default="updated")
        s.add_argument("--since"); s.add_argument("--until"); s.add_argument("--top", type=int)
        s.add_argument("--hot", action="store_true"); s.add_argument("--include-archived", action="store_true")
        s.add_argument("--hygiene", action="store_true")
    add("list", cmd_list, list_flags)
    add("tree", cmd_tree, lambda s: s.add_argument("--root"))
    add("stats", cmd_stats)
    add("get", cmd_get, lambda s: (s.add_argument("--id", required=True),
                                   s.add_argument("--comments", default="summary",
                                                  choices=["summary", "roots", "tail", "full", "none"])))
    add("distill", cmd_distill, lambda s: (s.add_argument("--id", required=True),
                                           s.add_argument("--mode", default="roots", choices=["roots", "summary", "full"]),
                                           s.add_argument("--since"), s.add_argument("--corrections-only", action="store_true")))
    add("timeline", cmd_timeline, lambda s: (s.add_argument("--id"), s.add_argument("--window")))
    add("runs", cmd_runs, lambda s: (s.add_argument("--id"), s.add_argument("--task"), s.add_argument("--since-seq", type=int)))
    add("search", cmd_search, lambda s: (s.add_argument("query"), s.add_argument("--include-closed", action="store_true"),
                                         s.add_argument("--limit", type=int), s.add_argument("--then-comments", action="store_true")))
    add("cost", cmd_cost, lambda s: (s.add_argument("--id"),))
    add("delta", cmd_delta, lambda s: (sweep_flags(s), s.add_argument("--set-watermark", action="store_true")))
    add("digest", cmd_digest, lambda s: s.add_argument("--mode", default="onboarding"))

    args = p.parse_args()
    PROFILE = args.profile
    args.func(args)
    if args.audit:
        print("\n─── 本次实发命令(全部只读) ───")
        print("\n".join(AUDIT) or "(未发出命令)")


if __name__ == "__main__":
    main()
