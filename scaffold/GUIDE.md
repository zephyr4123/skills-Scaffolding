# Skill 使用指南（skills-scaffolding 注入）

本项目已装载个人 skill 库，全部链接在 `~/.claude/skills`。遇到下列场景时**主动**调用对应 skill，不要等用户点名。（需要定位 skill 库仓库时：本项目 `.claude/skills-guide.md` 符号链接的目标是仓库 `scaffold/` 目录下的 GUIDE.md，`readlink` 反查后上溯一级即仓库根。）

## 场景路由

### 前端 / 网页 UI

- **设计、评审、打磨界面的默认入口**：`impeccable`（23 个子命令：craft 构建、audit 审计、polish 精修、animate 动效、live 浏览器迭代等，内置反 AI 味硬标准）
- **写落地页/营销站，防 AI 默认审美**：`design-taste-frontend`（v1 仅为兼容保留）；风格化叠加按需选：`minimalist-ui`（极简编辑风）、`industrial-brutalist-ui`（工业粗野）、`high-end-visual-design`（高端质感）、`gpt-taste`（Awwwards 向）、`frontend-design`（通用审美）
- **动画与交互手感**：写的时候用 `emil-design-eng`（Emil Kowalski 设计工程哲学）；审查动效代码用 `review-animations`（十条硬标准，Block/Approve 裁决）
- **高视觉要求的实现流程**：`image-to-code`（先出设计图、再提取设计系统、后写码）
- **自动建整站**：`design-loop`（接力棒循环，一页接一页）
- **只出概念图不写码**：`imagegen-frontend-web` / `imagegen-frontend-mobile`；品牌视觉物料：`brandkit`
- **旧项目视觉翻新**：`redesign-existing-projects`；为 Google Stitch 出设计规范：`stitch-design-taste`

### iOS / SwiftUI

- **写/改 SwiftUI 视图、小组件**：`swiftui-design-principles`（原生设计规范）；代码审查配合 `swiftui-pro` 插件（九份参考清单）
- **iOS 全流程**（需 ios-swift-skills 插件）：模拟器调试 `ios-debugger-agent`、性能 `swiftui-performance-audit` / `native-app-profiling`、并发 `swift-concurrency-expert`、视图重构 `swiftui-view-refactor`、UI 模式 `swiftui-ui-patterns`、Liquid Glass `swiftui-liquid-glass`、发布 `release-app-store-changelog` / `release-macos-spm-packaging`、修 issue `github-issue-fix-flow`

### 写作

- **去 AI 腔、加人味**：`humanizer`（30 种 AI 写作特征检测改写）

### 通用

- **要求完整输出、禁止省略占位**：`full-output-enforcement`
- **Multica 工作区操作**（派 issue 给 agent、看板/轨迹/汇报、onboarding、贴 multica.ai URL）：`multica-collab`
- **开发流程纪律**（superpowers 插件：`brainstorming`、`writing-plans`、`systematic-debugging` 等）：**仅在用户点名要求时使用，绝不自主加载**——它很重、时间-收益杠杆低，日常用轻量 skill 小步快跑 + workflow 对抗性审查替代

## 原则

- 设计类任务：选 `impeccable` 或 `design-taste-frontend` 之一作主导，风格类 skill 做叠加约束，不要同时开多个主导
- 插件类 skill（swiftui-pro、ios-swift-skills、superpowers）依赖插件已安装；缺了就按仓库根的 `install.manifest` 安装（或跑仓库的 `scripts/install.sh`）
- 完整清单与每个 skill 的详情：仓库根的 `README.md`
