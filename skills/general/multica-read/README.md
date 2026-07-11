# multica-read

> 让任意 agent 把 Multica workspace 的持久化记忆读全、读透、且 token 高效——严格只读。

## 问题陈述

Multica 上沉淀的 issue 网络（issue 正文 + 评论里的结论/⚠️更正/commit 链接 + agent 运行轨迹 + 元数据 + 关联代码 + 成本）是一个项目/团队"最长的上下文源"。但别的 agent 想直接读它很困难：

- `multica issue list` **没有 `--label` 过滤、没有时间排序**，也不返回评论。
- issue 里的 `assignee_id / labels / parent_id` 都是**裸 id**，不 join 就是无意义符号；而 issue 用的 assignee_id 是 member 的 `user_id`，和 `member list` 的 `id` 是**两套 id**，天然易踩坑。
- **真正的结论、拍板、commit 链接、⚠️更正**沉在**评论层**，不在正文——直接读正文会拿到被推翻的旧结论。
- Web UI 时间只显示到日，**同一天几十条事件无法排序溯源**。
- 轨迹和全量评论是 token 黑洞，不加纪律会吞爆上下文。

结果：issue 沉淀在 Multica 上，读起来又散又缺维度，"沉淀了等于没沉淀"。

## 解决方案

一个只读 helper（`scripts/mc_read.py`）+ SKILL.md 操作指南，把上述缺口全补齐并塑形成 agent 能一次吞下的**蒸馏记忆**：

- **原生 CLI 能做的**（status/assignee/priority/project/metadata 过滤、全文 search、单条 get、评论线程、runs 轨迹、usage、children）直接调用。
- **CLI 缺的**（按标签过滤、按时间排序/区间、父子树重建、活动时间线、卫生度扫描、蒸馏摘要、聚合、增量）用"一次全量 sweep 落缓存 + 客户端派生"补齐。
- 14 个子命令覆盖 A–J 十维能力：身份/拓扑/实体解析 · 全量清点/冷热分层 · 客户端派生视图 · 单 issue 深读 · 结论蒸馏/⚠️更正 · 取证/时间线/轨迹 · 自动化/成本/编制 · 增量/缓存/新鲜度 · 检索入口 · 输出契约/蒸馏产物。
- **严格只读**用 5 层 fail-closed 保障（见下）。

能力规格由一轮多视角 workflow 头脑风暴 + 完备性批判定稿（6 视角 + 1 综合，补出 8 个第一轮漏掉的维度）。

## 设计决策

| 决策 | 选择 | 原因 | 替代方案 |
|------|------|------|----------|
| 只读怎么保障 | 单一 mc() 网关 + 读动词白名单 fail-closed | 结构上不可能写；默认拒绝而非默认放行 | 靠 SKILL.md 口头约定(不可靠) |
| 标签/时间为何客户端派生 | issue list 无 --label、无 sort | CLI 天花板所限,只能拉 json 自己算 | 等官方加 flag(不可控) |
| 全量怎么取 | 一次 sweep 分页取尽落本地缓存,后续复用 | 用一次 O(全库)换掉后续 N 次精细调用,省 token | 每个视图各自打 CLI(慢且费) |
| 成员 id 怎么 join | 按 `user_id` **和** `id` 双映射 | issue.assignee_id 用的是 user_id,member list 的 id 是另一套 | 只按 id(解析失败,实测踩过) |
| 全局 flag 位置 | 写在子命令之后(共享父 parser) | 避开 argparse 全局 flag 的 default-reset 坑 | 放主 parser(flag 前置,易 reset 失效) |
| 缓存写哪 | `~/.cache/multica-read/<profile>/<ws>/`(仅本地) | 只读原则:副作用不触达 Multica 服务端 | 写进仓库(污染) |

## 已放弃方案

### 方案 A：纯 SKILL.md recipes、不带脚本
- **是什么**：只在 SKILL.md 里写一堆 `multica ...` 命令让 agent 照抄。
- **为什么放弃**：客户端派生（标签过滤/时间排序/树重建/时间线/蒸馏）逻辑复杂、易错，每次让 agent 现搓不可靠；且只读护栏无从强制。用脚本封装才稳。

### 方案 B：分期先写核心子集
- **是什么**：先 bootstrap/map/sweep/list/get/distill 跑通再补其余。
- **为什么放弃**：用户要"最全",一次写满 14 子命令 + 5 层护栏。

## 开源供应链（Build vs Buy）

| 组件 | 来源 | 覆盖度 | 我们的增量 |
|------|------|--------|-----------|
| Multica CLI(`multica`) | 官方(开源) | ~50% 只读原语 | 剩下的编排+客户端派生+只读护栏+输出塑形 |
| Python 标准库 | 内置 | argparse/json/subprocess/datetime | 无额外依赖,零安装 |

结论：薄封装 + 编排层——底层原语买(multica CLI),缺的维度和纪律自建。**零第三方依赖**。

## FAQ

**Q: 会不会不小心改了 Multica 的数据？**
A: 不会。所有 CLI 调用只经 mc() 网关,读动词白名单 fail-closed（`issue create`/`status`/`workspace switch` 等实测全被拒）；subprocess 列表调用无 shell 注入；恒 `--output json`、不传 `--force/--yes`；唯一"写"是本地缓存文件。`--audit` 可打印本次实发命令自证。

**Q: 通用吗？**
A: 通用。`--profile`/`--workspace` 参数化,任何 Multica workspace 都能读。这是**个人 skill**（非 AE/公司）。

**Q: 大库(上千 issue)扛得住吗？**
A: sweep 分页取尽 + 页数护栏 + 骨架只存轻量字段;list/stats/tree 在缓存上算;深读只对命中集;评论/轨迹默认摘要/增量。为大库省 token 设计。

## 生命周期

- **填补的 gap**：Multica CLI 的只读面散、缺派生维度，agent 读持久化记忆困难。
- **什么会让它过时**：Multica 官方出了 `--label`/时间排序/评论检索/一键 digest 等原生能力,或出了官方的记忆读取 MCP/API 时，本 skill 可退化为薄封装或退役。

## 演进历史

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-07-11 | 初版:14 子命令 + 5 层只读护栏;规格经 workflow 多视角头脑风暴定稿;在个人 workspace above-the-wind 实测跑通 |

## 文件清单

| 文件 | 用途 |
|------|------|
| SKILL.md | Agent 操作指南 |
| README.md | 人类设计文档（本文件） |
| scripts/mc_read.py | 只读 helper：14 子命令 + mc() 网关(5 层护栏) |
