---
name: multica-read
description: Use when agent 需要把某个 Multica workspace 的持久化记忆(issue 网络 + 评论结论/⚠️更正 + agent 轨迹 + 元数据 + 代码关联 + 成本)读全、读透、且 token 高效时 —— 尤其冷启动 onboarding、取证溯源、按标签/时间/全文检索、跨会话增量。严格只读,绝不改动 Multica 任何数据。配套 scripts/mc_read.py 提供 14 个只读子命令(bootstrap/map/sweep/list/tree/stats/get/distill/timeline/runs/search/cost/delta/digest)。
---

# multica-read：让 agent 读全 Multica 的持久化记忆

> **你是 Multica 记忆读取器,职责是把某个 workspace 的持久化记忆读全、读透、token 高效,喂给需要它的 agent 或人。铁律:严格只读——你只 `list/get/search/comment list/runs/...` 读,绝不 `create/update/delete/assign/status/comment add/switch` 任何写操作。所有 CLI 调用只经 `scripts/mc_read.py` 的 mc() 网关(白名单 fail-closed)。**

Multica 上沉淀的 issue 网络是团队/项目的"最长上下文源",但别的 agent 直接 `multica issue list` 读起来又散又缺维度(CLI 无 --label 过滤、无时间排序、评论结论要单独拉、id 是裸的)。本 skill 用一个只读 helper 把这些补齐并塑形成 agent 能一次吞下的蒸馏记忆。

## 怎么用

helper 在本 skill 的 `scripts/mc_read.py`。所有子命令:`python3 <本skill目录>/scripts/mc_read.py <子命令> [flags]`。公共 flag 一律写在**子命令之后**:`--profile <名,默认 personal>`、`--workspace <名/id>`、`--json`(机读)、`--audit`(末尾打印本次实发命令,只读自证)。

### 典型读取流(按场景选)

**A. 冷启动 onboarding(最常用,先建地图再填领土)**
```bash
python3 scripts/mc_read.py bootstrap      # ① 锁定身份/workspace(歧义会列候选)
python3 scripts/mc_read.py map            # ② 拓扑指纹 + 实体解析表 + 标签词典(建坐标系)
python3 scripts/mc_read.py digest         # ③ 一页纸蒸馏:全貌/热点/待办/深挖指针
python3 scripts/mc_read.py tree           # ④ 全项目父子树(看工作怎么组织)
```

**B. 多维检索取 issue**
```bash
python3 scripts/mc_read.py list --label 方法论            # 按标签(CLI 无此维,客户端派生)
python3 scripts/mc_read.py list --sort updated --top 10  # 按时间排序取最近
python3 scripts/mc_read.py list --since 2026-07-11T16:00:00Z   # 时间区间
python3 scripts/mc_read.py list --status backlog --priority high
python3 scripts/mc_read.py list --hygiene                # negative-space:读"缺什么"
python3 scripts/mc_read.py search 观测仪 --include-closed --then-comments  # 全文+两跳评论
python3 scripts/mc_read.py stats                         # 多维分布 + 停滞检测
```

**C. 深读单条 / 读结论 / 溯源**
```bash
python3 scripts/mc_read.py get --id ATW-14               # 单 issue 全档案卡
python3 scripts/mc_read.py distill --id ATW-14           # 评论结论 + ⚠️更正链 + commit 抽取
python3 scripts/mc_read.py timeline --id ATW-14          # 4 源(issue/评论/run/PR)秒级时间线
python3 scripts/mc_read.py runs --id ATW-14              # agent 运行轨迹(有才展开)
```

**D. 跨会话增量 / 成本**
```bash
python3 scripts/mc_read.py delta --set-watermark         # 记基线;下次只看变更
python3 scripts/mc_read.py cost --id ATW-14              # 单 issue token 用量
```

数据流:`sweep` 一次分页拉全量骨架落本地缓存,`list/tree/stats/digest/delta` 全部复用它(缺缓存会自动 sweep),不重复打 CLI。

## 硬性规则

1. **严格只读** — 绝不发任何写命令。helper 的 mc() 网关是白名单 fail-closed;你也绝不绕过 helper 直接跑 `multica` 的写子命令。可疑时用 `--audit` 打印实发命令自证。
2. **先建地图再填领土** — 读任何 issue 内容前先 `bootstrap`+`map`:issue 里的 assignee_id/labels/parent 都是裸符号,靠 map 的实体解析表才有意义。
3. **结论在评论不在正文** — issue.description 是初始意图;真正的拍板、commit 链接、尤其 ⚠️更正 沉在评论层。读结论必用 `distill`,且优先看 ⚠️更正——**别拿被推翻的旧结论当真**。
4. **时间精确到秒** — Multica web UI 只显示到日,`--output json` 的 created_at/updated_at 是秒级 ISO;溯源/排序一律用全精度(helper 已默认)。
5. **token 纪律** — 评论默认 `--summary/--roots-only`、轨迹(`runs`)最贵默认不碰、只对少数关键 issue `get --comments full`;大库先 `search`/分面 `list` 收窄再深读,别无脑全量深读。
6. **身份不混淆** — 个人项目走 `--profile personal`;歧义时 `bootstrap` 会列候选交人确认,**绝不 workspace switch**(那是写操作,已被护栏禁)。

## 反模式

❌ 直接 `multica issue list` 就想读全 → 缺 --label/时间排序/评论结论,且 id 不解析。
→ 用 `mc_read.py`,一次 sweep + 客户端派生补齐所有维度。

❌ 只读 issue 正文就下结论。
→ 正文是意图,结论/⚠️更正在评论;必跑 `distill`,先看有没有被更正。

❌ 把 `workspace member list` 的 `id` 当 issue 的 assignee_id 去 join。
→ 两套 id:issue 用的是 member 的 `user_id`;helper 已两个都映射,别自己手写 join 时踩这个坑。

❌ 一上来就 `runs`/`comment --full` 全量拉,吞爆上下文。
→ 轨迹和全量评论是最大 token 黑洞;默认摘要,只对代表性 issue 展开。

❌ 全局 flag 写在子命令前(`mc_read.py --json list`)。
→ flag 一律写在子命令后(`mc_read.py list --json`)。

## 常见问题

| 症状 | 原因 | 解决方案 |
|------|------|----------|
| 负责人显示成一串 id 不是人名 | 实体缓存旧,或该 member 未在 member list | `mc_read.py map --refresh-cache` 重建实体表 |
| `unrecognized arguments: --json` | 全局 flag 写在子命令前了 | 写在子命令后:`list --json` |
| bootstrap 报"workspace 歧义" | 该 profile 下多个 workspace | 加 `--workspace <名/id>` 指定 |
| distill 显示结论 0 | 该 issue 没评论(如纯索引节点) | 正常;去有评论的落地 issue 上跑 |
| list/tree 数据像是旧的 | 用了缓存 | 先 `mc_read.py sweep` 刷新骨架缓存 |
| 某对象 list 为空(project/autopilot 等) | 该 workspace 确实没有 | 正常,helper 已优雅处理空 |
