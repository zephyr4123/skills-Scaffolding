# workflow-orchestration

> 把「以 Workflow(多 agent 编排)为工程核心锚点」这套打法,从一个真实项目里蒸馏成可跨项目复用的操作 playbook。

## 问题陈述

Claude Code 的 Workflow 工具很强,但「什么时候上、上多大、什么形状、怎么收敛」没有约束时,容易两头翻车:

- 一头:琐碎活也 5-agent 轰,又慢又费(没过杠杆闸)。
- 另一头:把 sub-agent 的产出当结论——**fan-out 不配 verify,就是把不可信放大 N 倍**。

真正让 fan-out 有价值的那几条纪律(主控 verify、结构化产出契约、收敛判据、独立性校验)是**隐性的**,散落在经验里,换个会话 / 换个项目就重新踩。

## 解决方案

一套**决策式 playbook**:Step0 要不要上(杠杆闸)→ Step1 选形状(barrier / pipeline / offload)→ Step2 选范式(五种)→ Step3 收敛(主控 verify,唯一不可 fan-out)。配一套「让编排可信」的承重规则 + 反模式 + 排障表。

## 核心立论

单 agent 单次 = 一个误差未知的**点估计**;N 个独立 agent = **集成(ensemble)**,独立性让不相关误差相互抵消——Workflow 改的是每份产出的**认识论地位**,不只是速度。它**作用在其它工程习惯之上**(放大取证调试、可溯源、skill 蒸馏……),这层「元方法」属性,是它值得当核心锚点、而不只是又一件并行工具的原因。

## 设计决策

| 决策 | 选择 | 原因 | 替代方案 |
|---|---|---|---|
| skill 形态 | 纯 playbook(**无 script**) | 这是判断 / 决策知识,不是工具链;"验证前置"体现在每条范式都有真实项目 grounding | 带脚本——不适用,没有可自动化的链路 |
| 深浅分层 | SKILL.md 只放可执行决策层,深参考指向 Multica | 避免与 Multica 深文档重复;**skill 薄、reference 厚**,agent 才记得住 | 把 7 个 issue 深内容全塞进 SKILL(胖、难记) |
| 承重脊 | `agents propose, orchestrator disposes` 立为铁律 | fan-out 不配 verify 就是放大不可信,这是最容易被忽略、却最承重的一条 | 只讲"并行快"——把编排讲浅了 |
| 配合锚 | Playwright / run-app 闭环校验单列 | 它是单 agent 感知回路、不是多 agent 编排,但和 workflow 在流水线里组合,不能漏 | 塞进 workflow 范式里——分类不纯 |

## 与 Multica 深参考的关系

本 skill = **可执行层**(怎么做的决策流 + 纪律)。深层第一性原理、六条承重原则、每种范式的完整 grounding = **参考层**,住在 Multica `above-the-wind` 方法论簇:hub **ATW-26(#8)** + 5 支 **ATW-28~32** + 配合锚 **ATW-27(#9)**。skill 记不下的深度去那里查——这正呼应 [multica-read](../multica-read/) 的主张:让沉淀**可读**,方法论才算闭环。

## 已放弃方案

### A:把 Multica 7 个 issue 原样搬进 SKILL.md
- **是什么**:把 hub + 5 支 + 配合锚的完整正文拷进 SKILL.md。
- **为什么放弃**:太长、agent 记不住;playbook 要的是「决策 + 纪律」的可执行浓缩,不是论文。深内容留在 Multica 分层引用。

## 开源供应链(Build vs Buy)

| 组件 | 来源 | 覆盖 | 增量 |
|---|---|---|---|
| Workflow 工具本体 | Claude Code 内建 | 编排原语(parallel / pipeline / agent) | 本 skill 补的是"何时/多大/什么形状/怎么收敛"的判断纪律,工具本身不教 |

零第三方依赖(纯知识 playbook)。

## FAQ

**Q:和 superpowers 那套重流程 skill 什么关系?**
A:替代关系。本人路线是「轻量 skill 小步快跑 + workflow 对抗审查」替掉 brainstorming / writing-plans 那套重流程——本 skill 就是那套轻打法的编排纪律。

**Q:通用吗?**
A:通用。范式与纪律与语言 / 技术栈无关,任何项目都能用。**个人 skill**(非 AE)。

## 生命周期

- **填补的 gap**:Workflow 工具强,但用法纪律隐性、跨项目重踩。
- **什么会让它过时**:多 agent 编排范式成为 harness 内建默认纪律,或本人打法演进后需重蒸馏。

## 演进历史

| 版本 | 日期 | 变更 |
|---|---|---|
| v1.0 | 2026-07-12 | 初版:从 `above-the-wind` 项目 dogfood 蒸馏;5 范式 + 6 承重原则 + Playwright 配合锚;结构经 3 路对抗审查 workflow(完备性 / 组织MECE / 框架深度)定稿 |

## 文件清单

| 文件 | 用途 |
|---|---|
| SKILL.md | Agent 操作 playbook |
| README.md | 人类设计文档(本文件) |

---
distill 自 above-the-wind 项目(用户点名);是个人方法论 **#7**(项目需求 → 可复用 skill 回流脚手架)的**第二个实例**(第一个 = multica-read)。本 skill 是个人的,非 AE。
