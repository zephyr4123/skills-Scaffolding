---
name: skill-routing-ios
description: SwiftUI 视图、iOS 验证闭环、iOS 全流程任务该用哪个 skill
metadata:
  node_type: memory
  type: reference
---

遇到下列场景**主动**调用对应 skill，不等用户点名。

- **写 / 改 SwiftUI 视图、小组件**：`swiftui-design-principles`（原生设计规范）；代码审查配合 `swiftui-pro` 插件（九份参考清单）
- **改完要自己拿到证据再交付**：`zephyr-ios-verify-loop`（先查工具链反"我本地验不了"→ 按层取证：编译 / 本地同镜像服务 / 模拟器点击驱动 AXe / 手势探针 / 接口正负边界样本 / 只读 SQL 对账 → 双轨审查兜住自验漏网 → 按规格报证据；含 20+ 条实测踩坑）
- **iOS 全流程**（需 `ios-swift-skills` 插件，上游目前装不上）：模拟器调试 `ios-debugger-agent`、性能 `swiftui-performance-audit` / `native-app-profiling`、并发 `swift-concurrency-expert`、视图重构 `swiftui-view-refactor`、UI 模式 `swiftui-ui-patterns`、Liquid Glass `swiftui-liquid-glass`、发布 `release-app-store-changelog` / `release-macos-spm-packaging`、修 issue `github-issue-fix-flow`

相关：[[skill-library]]
