# Skill 使用指南（skills-scaffolding 注入）

本项目已装载个人 skill 库。遇到下列场景时**主动**调用对应 skill，不要等用户点名。

- skill 根：Claude Code 在 `~/.claude/skills`，Codex 在 `~/.agents/skills`（插件模式下由插件直接注册，无需这两个目录）
- 标 **⚙️CC** 的 skill **只能在 Claude Code 上跑**（依赖该引擎专有能力或写死了 `.claude/` 路径），在 Codex 上别调；其余两个引擎通用
- 每个 skill 的 frontmatter 里 `engines:` 字段是权威判据
- 定位仓库：`readlink` 本项目的 `CLAUDE.local.md`（或 `AGENTS.md`）拿到目标路径——它指向 `<仓库>/scaffold/AGENTS.md`，上溯两级即仓库根

## 场景路由

### 前端 / 网页 UI

- **设计、评审、打磨界面的默认入口**：`impeccable` ⚙️CC（23 个子命令：craft 构建、audit 审计、polish 精修、animate 动效、live 浏览器迭代等，内置反 AI 味硬标准）
- **写落地页/营销站，防 AI 默认审美**：`frontend-design`（通用审美）
- **动画，按手上这件事分工**（四条都只管 Web，原生走 `swiftui-design-principles`）：边写边参考 → `emil-design-eng`；界面太死、想知道哪儿该加 → `find-animation-opportunities`（只读，出 5~7 条清单外加一份「考虑过但否掉了」）；已有动效想整体盘一遍排改进顺序 → `improve-animations`（只读审计，写成带精确数值的计划文件交给别人改）；一个 diff 过闸 → `review-animations`（十条硬标准，Block/Approve；**要用户点名，别指望它自动起来**）。**想直接改出来别用这四条，走 `impeccable animate`**
- **手指驱动的交互**（拖拽、滑动关闭、bottom sheet、中途抓住反向）：`apple-design`（速度交接、动量落点公式、橡皮筋阻尼、半透明材质；组件手感找 Emil，手指物理找它，两个都是叠加层不抢主导）。**说得出效果、叫不出名字**：`animation-vocabulary`（术语反查，只给名字不写码）
- **要用户点名才启动的**（frontmatter 带 `disable-model-invocation`，别指望自动触发；上面的 `review-animations` 同属此类）：`prototype`——同一个组件做 3~5 个方向真不一样的可用版本，翻着比，选中的才写进代码（**它会自删原型目录，别在脏工作区跑**）；`pick-ui-library`——19 条「任务→用哪个库」钦定表，**仅限 React Web**，存量项目以 package.json 和主导 skill 已定的设计系统为准
- **自动建整站**：`design-loop` ⚙️CC（接力棒循环，一页接一页）

### iOS / SwiftUI

- **写/改 SwiftUI 视图、小组件**：`swiftui-design-principles`（原生设计规范）；代码审查配合 `swiftui-pro` 插件（九份参考清单）
- **改完要自己拿到证据再交付**：`zephyr-ios-verify-loop`（开发-验证闭环：先查工具链反「我本地验不了」→ 按层取证「编译 / 本地同镜像服务 / 模拟器点击驱动 AXe / 手势探针 / 接口正负边界样本 / 只读 SQL 对账」→ 审查双轨兜住自验漏网 → 按规格报证据；含 20+ 条实测踩坑）
- **iOS 全流程**（需 ios-swift-skills 插件）：模拟器调试 `ios-debugger-agent`、性能 `swiftui-performance-audit` / `native-app-profiling`、并发 `swift-concurrency-expert`、视图重构 `swiftui-view-refactor`、UI 模式 `swiftui-ui-patterns`、Liquid Glass `swiftui-liquid-glass`、发布 `release-app-store-changelog` / `release-macos-spm-packaging`、修 issue `github-issue-fix-flow`

### 写作

- **去 AI 腔、加人味**：`humanizer` ⚙️CC（30 种 AI 写作特征检测改写）

### 通用

- **写码 / 架构 / 选库 / 配环境 / 交付**：`zephyr-coding-standards`（结构三清晰、实现纪律、选型四看、交付自检）
- **写测试 / 做审查 / 验产出 / 排查问题**：`zephyr-quality-discipline`（测试驱动、CI 门禁、对抗审查、排查三纪律与证据规格）
- **整理 / 审计本机密钥、判断某 token 能不能删、新机器配凭据**：`zephyr-secrets-hygiene`（按「谁能读到」分层归位、登记册要能机器对账、`withkey` 按需加载器；删之前查真正的调用方且不 rm 只隔离；含实测静默陷阱清单。**纯方法论，不带脚本**——给判断方法与参考实现）
- **管「外层协作仓 + 多个独立业务代码仓」的拓扑**（定多仓关联方式、初始化/承接 nested 拓扑项目、给外层仓写跨仓 git 运维 CLI）：`zephyr-nested-git`（外层零业务代码只存指针 manifest，代码仓独立 clone 被 .gitignore 挡住各推各的远端；含单文件参考 CLI，红线在代码里——pull 只 ff-only、push 永不 force、fetch 失败不吞、prod 漂移告警）
- **Multica 工作区操作**（派 issue 给 agent、看板/轨迹/汇报、onboarding、贴 multica.ai URL）：`zephyr-multica-collab`
- **Multica 记忆读取**（把 workspace 的 issue 网络/结论/轨迹/成本读全读透、只读不写、token 高效）：`zephyr-multica-read`
- **多 agent Workflow 编排**（有份量的多步工程活，决定何时上编排、选什么形状与范式；长跑 workflow 卡住 / 大批失败 / 放量前评估也走它）：`zephyr-workflow-orchestration` ⚙️CC
- **让外部长任务跑完来找你**（外部系统上的任务 / CI / 部署 / 远程队列这类不会主动通知你的活；含「静默≠正常」的哨兵纪律）：`zephyr-background-watch` ⚙️CC（依赖 Monitor 与后台任务）
- **开发流程纪律**（superpowers 插件：`brainstorming`、`writing-plans`、`systematic-debugging` 等）：**仅在用户点名要求时使用，绝不自主加载**——它很重、时间-收益杠杆低，日常用轻量 skill 小步快跑 + workflow 对抗性审查替代

## 原则

- 设计类任务：以 `impeccable` 为主导，`frontend-design` 等审美类做叠加约束，不要同时开多个主导
- 插件类 skill（swiftui-pro、ios-swift-skills、superpowers）依赖插件已安装；缺了就按仓库根的 `install.manifest` 安装（或跑仓库的 `scripts/install.sh`）
- **引擎适配**：标 ⚙️CC 的在 Codex 上不可用——不是话题不符，是内容依赖 Claude Code 专有能力或硬编码了 `.claude/` 路径，调了会空转。拿不准就看 skill frontmatter 的 `engines:`
- 完整清单与每个 skill 的详情：仓库根的 `README.md`
