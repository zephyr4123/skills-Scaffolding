# ios-swift-skills

> ## ⚠️ 当前无法安装（2026-07-27 实测）
>
> 上游 `patrickserrano/skills` 的 `.claude-plugin/` 下**只有 `plugin.json`，没有 `marketplace.json`**——4 个候选市场清单路径全部 404，上游 2026-01-17 后未再推送。
>
> **Claude Code 与 Codex 在全新环境下 add 均失败**，报错文案是：
>
> ```
> ✘ Failed to add marketplace: Marketplace file not found at 〈本地缓存路径〉
> ```
>
> ⚠️ 这条报错**指向本地路径，极易被误判成自己环境坏了**，根因其实在上游仓库结构。
> ⚠️ 另注：`claude plugin marketplace add` 失败时**退出码仍是 0**，脚本靠退出码判定不出来。
>
> 若某台机器上它能用，是历史缓存里留了一份 untracked 的 `marketplace.json`，**不代表新用户能装**。
>
> 已从 `install.manifest` 注释掉。上游补上 `marketplace.json` 后，取消该行注释即可恢复。
> 本档案继续保留——它记录的 skill 清单与踩坑仍然有参考价值。

- **来源**：Patrick Serrano — <https://github.com/patrickserrano/skills>
- **安装**：~~`/plugin marketplace add patrickserrano/skills` → `/plugin install ios-swift-skills@patrickserrano-skills`~~（见上方说明，当前失效）
- **本机版本**：1.0.0（2026-07-02 在装，靠历史缓存）
- **一句话**：覆盖 iOS/macOS 开发全流程的 Swift 技能包——从 SwiftUI UI 模式、性能与并发优化，到调试、性能剖析、打包发布与 GitHub issue 修复。

## Skill 清单

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| github-issue-fix-flow | 用 gh CLI 端到端完成 GitHub issue 修复、构建测试、提交并推送 | 需要根据 issue 编号实现修复并自动提交推送时 |
| ios-debugger-agent | 在模拟器上构建、运行并调试 iOS 应用，可操作 UI 和抓取日志 | 需要运行 iOS 应用、操作模拟器或诊断运行时行为时 |
| native-app-profiling | 用 xctrace 命令行对 macOS/iOS 应用做 Time Profiler 性能剖析 | 需要定位 CPU 热点或慢代码路径而不想打开 Instruments 时 |
| release-app-store-changelog | 从 git 历史生成面向用户的 App Store 发布说明 | 需要基于 git tag 生成 What's New 或版本更新日志时 |
| release-macos-spm-packaging | 不用 Xcode 工程，基于 SwiftPM 搭建、构建并打包签名 macOS 应用 | 需要从零搭 SwiftPM macOS 应用、组装 .app 或签名公证时 |
| swift-concurrency-expert | 针对 Swift 6.2+ 并发代码进行审查、合规改进与编译错误修复 | 需要审查 Swift Concurrency 用法或修并发编译错误时 |
| swiftui-liquid-glass | 在 SwiftUI 中采用、重构或审查 iOS 26+ Liquid Glass API | 需要接入或评审 Liquid Glass 界面效果时 |
| swiftui-performance-audit | 审计并优化 SwiftUI 运行时性能，解决卡顿与过度刷新 | 渲染慢、滚动卡顿、CPU/内存偏高等 SwiftUI 性能问题时 |
| swiftui-ui-patterns | 提供构建 SwiftUI 视图与组件的最佳实践和常用模式 | 创建或重构 SwiftUI 界面、设计 Tab 架构或组合页面时 |
| swiftui-view-refactor | 重构 SwiftUI 视图，统一结构、依赖注入与 Observation 用法 | 需要整理视图结构、安全处理 ViewModel 或规范依赖传递时 |
