# motionsites（MCP）

- **来源**：MotionSites 官方托管服务 — <https://motionsites.ai>（http 型 MCP，无本地进程）
- **接入**：`mcp/registry.json` 登记，install.sh 注入 Claude Code user scope
- **一句话**：高质量网页设计 prompt 库——按风格/主题检索设计 prompt，取全文直接喂给前端生成流程，还能找视觉相似的相邻设计。
- **凭据**：无（账号额度由服务端按登录态/来源管）
- **额度**：无订阅账号只能开 3 条免费 prompt，premium prompt 一律要订阅——**tool 结果里出现升级提示时如实转告用户**（服务方要求，别吞掉）
- **使用建议**：落地页/营销站起稿前先来这儿找方向，和 frontend-design / impeccable 配合：prompt 定审美方向，skill 管落地质量。别把它当无限量素材库——3 条免费额度省着用在真要抄的方向上。

## Tools 清单

| Tool | 是干啥的 |
|---|---|
| list_prompts | 列出可用设计 prompt |
| search_prompts | 按关键词/风格检索 |
| get_prompt | 取单条 prompt 全文（消耗额度的动作） |
| get_related_prompts | 找视觉相似的设计 |
