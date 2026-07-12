---
name: workflow-orchestration
description: Use when 面对一件有份量的多步工程活(设计一个功能/大改动/大规模调研/代码审查/迁移/排障)、要决定"怎么用多 agent Workflow 编排"时——教一套以 Workflow 为核心锚点的编排打法:何时该上(杠杆闸)、选什么形状(barrier / pipeline / offload)、哪五种范式(大规模调研+交叉验证 / 判官团发散 / 对抗审查收敛 / 并行+上下文卸载 / 大切片流水线)、以及让编排可信的承重纪律(agents propose orchestrator disposes、结构化产出契约、收敛判据、独立性校验)。配合锚:Playwright / run-app 闭环校验。不适用于纯对话或琐碎机械改动。
---

# workflow-orchestration:以 Workflow 为核心锚点的工程编排

> **你是多 agent 编排的操盘手。核心信念:单 agent 单次输出 = 一个误差未知的点估计;N 个独立 agent = 集成(ensemble),独立性让不相关误差相互抵消——Workflow 改的是每份产出的「认识论地位」,不只是速度。铁律:fan-out 的是劳动,fan-in 的判断永远留在你手里——`agents propose, orchestrator disposes`,唯一不可外包的是最终裁决。**

深层第一性原理与每种范式的完整 grounding 见 Multica `above-the-wind` 方法论簇(hub ATW-26 · 5 支 ATW-28~32 · 配合锚 ATW-27)——**可选、个人 workspace、非复用必需**:本 skill 的决策流不查它也能照跑,深参考只是加分。

## 怎么用(决策流)

### Step 0 · 要不要上 workflow(杠杆闸)
- 单事实 / 单文件的琐碎活 → 单步搜索或直接干,**别开编排**。
- 值得上的信号:方案空间宽、要多视角证伪、规模大要并行、重活压主上下文。**值才上。**
- ultracode / 大任务可默认常开;但"默认开" ≠ 无脑 5-agent 轰一切——**按杠杆定规模**(边际视角≈免费但有拐点)。

### Step 1 · 选形状(按依赖结构,别一刀切)
- 子任务**相互独立** → **barrier fan-out**(`parallel`,一轮收齐)。
- 阶段间**有依赖** → **pipeline**(每站输出 = 下站输入 schema,可断点续跑)。
- **单个重活** → 只 **offload**(丢后台返 digest,保主上下文,压根不必并行)。

### Step 2 · 选范式(五选一或组合)
| 范式 | 什么时候 | 收敛机制 |
|---|---|---|
| **大规模调研 + 交叉验证** | 要吃透外部事实 / 许可 / 竞品 | 对外部事实交叉印证到「无冲突」→ **落成可复现脚本 + 数据**,不出散文 |
| **判官团(发散)** | 方案空间宽、要创造性方向 | N 路**不同框架** → 合成 + **嫁接各家最优**(暴露 dissent,不抹平) |
| **对抗审查(收敛)** | 已有产物要挑错、降返修 | N 个独立 lens(**含"完备性"一路**)→ 结构化 findings(带严重度+verdict) |
| **并行 + 上下文卸载** | 一批独立子任务 / 重活压上下文 | 提吞吐 + 护主判断力;**但并行 ≠ 真独立** |
| **大切片流水线** | 完整功能从 0 到合并 | 调研→判官团→build→闭环校验→对抗审查→蒸馏,阶段间走交接契约 |

发散(判官团)与收敛(对抗审查)矢量相反,**分开跑,别捆一坨**。两种「收敛」也别混:调研的收敛 = 对**外部事实**交叉印证到无冲突;对抗审查的收敛 = 对**自己产物**证伪。流水线里 **skill × workflow 互补**:确定性的品味 / 流程 skill(如 impeccable)嵌进某工位定「好的样子」,workflow 供多路独立视角逼近它——不是二选一。

### Step 3 · 收敛(劳动可 fan-out,fan-in 的最终裁决不可外包)
- 收敛阶段本身照样 fan-out N 个 lens / skeptic;**唯一不可外包的是 fan-in 那一下——最终裁决留在主控**。
- sub-agent 产出**必经主控逐条 verify 才算数**——结构化 findings 才好逐条消费。潜伏 bug 常是 verify 抓的、不是 lens 抓的。
- 收敛判据:**不设固定轮数,审到连续一轮无实质新发现即停**。
- 落到真实环境取证:前端走 **Playwright 闭环校验**(截图→读图→判断→改→再截,桌面/平板/移动/高视口多档 + 交互),后端走 **run-app + read-logs**。截图不读回来 = 没验证。

**结构化产出契约长这样**(让主控能逐条 verify 的最小形状,别收散文):
```json
{ "findings": [ { "severity": "blocker|major|minor|nit", "location": "file:line 或选择器",
                  "issue": "可复现的失败场景", "fix": "具体修法", "verdict": "CONFIRMED|PLAUSIBLE" } ],
  "overall": "一句话总评" }
```
主控按 severity 排序 → 逐条 verify(CONFIRMED 才认)→ fix;判官团则回各方案的多维评分 + 暴露 dissent。

## 硬性规则

1. **agents propose, orchestrator disposes** — sub-agent 产出必经主控 verify;最终裁决永不外包。fan-out 不配 verify,就是把不可信产出放大 N 倍。
2. **结构化产出契约** — 让 sub-agent 回结构化(findings 带严重度/verdict、评分、schema),主控才能确定性逐条消费,也才可回流 issue、可审计;**不收散文**。
3. **独立性是承重假设、会被破坏** — 共享 repo / 文件 state 泄漏会制造相关失败;并行拿到 0 error 后**主控串行复审仍强制**。跨 lens / 跨引擎的独立 > 同质多开。
4. **过量供给视角、但有拐点** — 边际 reviewer ≈ 免费故审查量应往上调;但 token / 时间有限,收益递减处刹车。
5. **上下文卫生** — 重活丢后台,护 orchestrator 的上下文(它是唯一稀缺资源、= 判断质量)。
6. **收敛判据成文** — 审到连续一轮无实质新发现即停;不设固定轮数、也不草草一轮。

## 反模式

❌ 琐碎活也开 5-agent → 按杠杆定规模,值才上。
❌ 拿 sub-agent 产出直接当结论 → 必经主控逐条 verify(agents propose, orchestrator disposes)。
❌ lens 自己收口就算审完 → fan-in 的判断留主控;lens 只提怀疑,主控取证裁决。
❌ N 路同质多开当"独立视角" → 给每路不同框架 / lens 逼真发散,独立性才承重。
❌ sub-agent 回散文 → 要结构化(findings / 评分 / schema)才能确定性消费。
❌ 并行 0 error 就以为可信 → 共享 state 会泄漏,主控串行复审强制。
❌ 前端改完只看代码 / 类型检查 → 上 Playwright 真实环境截图取证。
❌ 把发散(判官团)和收敛(对抗审查)糊成"一种评审" → 矢量相反,分两枝跑。

## 常见问题

| 症状 | 原因 | 解决 |
|---|---|---|
| workflow 产出看着对、一集成就错 | 没主控 verify,或 sub-agent 共享 state 泄漏 | 逐条 verify;排查跨 agent 的 state 依赖 |
| 多路 agent 给的方案都差不多 | 没给不同框架,同质多开 | 每路指定不同出发框架 / lens |
| 审查没完没了 / 草草一轮 | 没定收敛判据 | 连续一轮无实质新发现即停 |
| 主上下文被 sub-agent 输出撑爆 | 没走结构化 / 没卸载 | 结构化 schema 回收 + 重活丢后台返 digest |
| 前端"应该没问题"但真跑有 bug | 只静态看没跑真实环境 | Playwright 多档视口截图 + 交互实测 |
| 小任务也开一堆 agent、又慢又费 | 没过杠杆闸 | Step 0 先判值不值得,琐碎活单步干 |
