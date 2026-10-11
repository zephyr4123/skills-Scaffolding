---
name: mcp-tools
description: 浏览器自动化、图标、免版权配图、网页设计 prompt 该用哪个 MCP（仅 Claude Code 侧有）
metadata:
  node_type: memory
  type: reference
---

这些 MCP 只注入了 Claude Code 的 user scope，Codex 会话里不存在。工具不在时，在脚手架仓库跑 `python3 scripts/install.py --check` 对账。

- **浏览器自动化 / UI 闭环取证**：`playwright`（导航 / 点击 / 快照 / 截图 / 网络观测）——要用户真实 Chrome 登录态时才用 claude-in-chrome
- **找图标**：`iconify`（跨图标集语义搜索 + 取 SVG）——别让模型手绘 SVG 图标，同一项目尽量只用一个图标集
- **找免版权配图**：`stock-images`（Pexels / Unsplash / Pixabay 三源）——要真实摄影素材时用；工具不在说明凭据未就位
- **找网页设计 prompt**：`motionsites`——落地页起稿先找方向；免费额度仅 3 条，省着用，结果里的升级提示如实转告用户

相关：[[skill-routing-frontend]]
