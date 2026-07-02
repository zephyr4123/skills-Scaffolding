# superpowers

- **来源**：社区作者 Jesse Vincent（obra）出品，经 Anthropic 官方插件市场分发 — <https://github.com/anthropics/claude-plugins-official>（上游 <https://github.com/obra/superpowers>）
- **安装**：`/plugin install superpowers@claude-plugins-official`（官方市场默认可用）
- **本机版本**：6.1.0（持续自动更新）
- **一句话**：面向 Claude Code 的软件工程流程纪律插件，覆盖需求脑暴、计划编写与执行、TDD、系统化调试、代码评审、并行子代理、worktree 隔离与完工验证。
- **使用建议**：很重，慎用——除非点名要求，日常以"轻量 skill 小步快跑 + workflow 对抗性审查"替代（见 scaffold/HABITS.md），插件保留安装即可。

## Skill 清单

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| brainstorming | 创造性工作前，通过对话式提问澄清意图，形成设计并获批后才动手 | 新增功能、构建组件或修改行为之前 |
| dispatching-parallel-agents | 对多个相互独立的任务，各派一个上下文隔离的子代理并行处理 | 有 2 个以上无共享状态、无先后依赖的独立任务时 |
| executing-plans | 加载书面实现计划，批判性审阅后按任务逐步执行并在检查点汇报 | 已有实现计划、需在单独会话中执行时 |
| finishing-a-development-branch | 开发完成后先验证测试，再提供 merge/PR/清理等收尾选项 | 实现完成、测试全过，要决定如何整合分支时 |
| receiving-code-review | 收到评审意见先技术验证再实施，拒绝表演式附和或盲目照改 | 收到代码评审反馈、尤其含糊或存疑时 |
| requesting-code-review | 派出上下文精准构造的评审子代理，尽早尽频繁审查成果 | 完成任务或重大功能后、合并主分支前 |
| subagent-driven-development | 每个计划任务派新实现子代理，任务后做规格+质量评审 | 在当前会话执行含独立任务的实现计划时 |
| systematic-debugging | 铁律：先系统化调查找到根因，禁止未查根因就打补丁 | 遇到任何 bug、测试失败或异常行为时 |
| test-driven-development | 先写测试并亲眼看它失败，再写最小实现让其通过（红-绿-重构） | 实现新功能或修 bug、写实现代码之前 |
| using-git-worktrees | 为功能开发建立隔离工作区，优先平台原生工具，退回 git worktree | 开始需要与当前工作区隔离的开发之前 |
| using-superpowers | 会话入口规则：只要有技能可能适用，必须先调用该技能 | 每次对话开始时 |
| verification-before-completion | 声称完成/修好前必须运行验证命令拿到新鲜证据 | 宣称工作完成、提交或建 PR 之前 |
| writing-plans | 为多步任务写零上下文假设的详细实现计划 | 已有规格的多步任务、动代码之前 |
| writing-skills | 用 TDD 方法写技能文档：先看子代理无技能时失败，再写技能让其合规 | 创建、编辑技能或部署前验证技能时 |
