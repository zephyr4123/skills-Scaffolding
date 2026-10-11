---
name: skill-routing-frontend
description: 网页 UI、动效、手势交互任务该用哪个 skill（impeccable 主导，动效四件套各有分工）
metadata:
  node_type: memory
  type: reference
---

遇到下列场景**主动**调用对应 skill，不等用户点名。四条动效 skill 都只管 Web，原生走 `swiftui-design-principles`。

- **设计、评审、打磨界面的默认入口**：`impeccable` ⚙️CC（23 个子命令：craft 构建、audit 审计、polish 精修、animate 动效、live 浏览器迭代等，内置反 AI 味硬标准）
- **写落地页 / 营销站，防 AI 默认审美**：`frontend-design`
- **动效按手上的事分工**：
  - 边写边参考 → `emil-design-eng`
  - 界面太死、想知道哪儿该加 → `find-animation-opportunities`（只读，出 5~7 条清单外加"考虑过但否掉了"）
  - 已有动效想整体盘一遍排改进顺序 → `improve-animations`（只读审计，写成带精确数值的计划文件交给别人改）
  - 一个 diff 过闸 → `review-animations`（十条硬标准，Block/Approve；**要用户点名才启动**）
  - 想直接改出来 → 别用这四条，走 `impeccable animate`
- **手指驱动的交互**（拖拽、滑动关闭、bottom sheet、中途抓住反向）：`apple-design`（速度交接、动量落点、橡皮筋阻尼；组件手感找 Emil，手指物理找它，两个都是叠加层不抢主导）
- **说得出效果、叫不出名字**：`animation-vocabulary`（术语反查，只给名字不写码）
- **要用户点名才启动的**（frontmatter 带 `disable-model-invocation`）：
  - `prototype` —— 同一个组件做 3~5 个方向真不一样的可用版本翻着比，选中的才写进代码（**它会自删原型目录，别在脏工作区跑**）
  - `pick-ui-library` —— 19 条"任务→用哪个库"钦定表，**仅限 React Web**，存量项目以 package.json 和已定的设计系统为准
- **自动建整站**：`design-loop` ⚙️CC（接力棒循环，一页接一页）

**原则**：设计类任务以 `impeccable` 为主导，`frontend-design` 等审美类做叠加约束，不要同时开多个主导。

相关：[[skill-library]] [[mcp-tools]]
