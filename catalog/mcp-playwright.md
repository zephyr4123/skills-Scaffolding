# playwright（MCP）

- **来源**：Microsoft 官方 `@playwright/mcp` — <https://github.com/microsoft/playwright-mcp>（npm 分发，`npx` 即用）
- **接入**：`mcp/registry.json` 登记，scripts/install.py 注入 Claude Code user scope；stdio 型
- **一句话**：浏览器自动化全家桶——导航、点击、表单、截图、可访问性快照、执行 JS、网络请求观测，起自己的浏览器实例干活。
- **本机配置要点**：指定 `--browser chrome` + 独立 profile（`~/.config/playwright-profile`，与日常浏览器隔离）+ 动作超时 15s
- **凭据**：无
- **使用建议**：前端/UI 活的**闭环校验锚点**——zephyr-workflow-orchestration 与 impeccable live 迭代都靠它拿真实渲染证据。与 claude-in-chrome 的分工：claude-in-chrome 借用户真实 Chrome 会话（带登录态，要装扩展），playwright 起独立实例（干净、可并行、无登录态）；要登录态用前者，要干净环境用后者。

## Tools 清单（常用）

| Tool | 是干啥的 |
|---|---|
| browser_navigate / navigate_back | 打开 URL / 后退 |
| browser_click / type / press_key / hover / drag | 页面交互 |
| browser_fill_form / select_option / file_upload | 表单操作 |
| browser_snapshot | 可访问性快照（优先用它读页面，比截图省 token） |
| browser_take_screenshot | 像素截图（视觉校验用） |
| browser_evaluate / run_code_unsafe | 页内执行 JS |
| browser_network_requests / console_messages | 网络与控制台观测 |
| browser_tabs / resize / handle_dialog / wait_for | 窗口与流程控制 |
