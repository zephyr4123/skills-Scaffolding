# iconify（MCP）

- **来源**：社区 `iconify-mcp-server`（npm 分发，`npx -y` 即用），数据源为 Iconify 开放图标生态（200+ 图标集、20 万+ 图标）
- **接入**：`mcp/registry.json` 登记，scripts/install.py 注入 Claude Code user scope；stdio 型
- **一句话**：跨图标集的图标检索与取用——按语义搜图标、拿单个图标的 SVG、查某个图标集的全貌与授权。
- **凭据**：无
- **使用建议**：前端写界面需要图标时**先搜再手绘**——别让模型现编 SVG path（歪且不统一）。选定图标集后同一项目尽量只用这一家，风格才齐；图标集各有 LICENSE，商用前看一眼 get_icon_set 里的授权字段。

## Tools 清单

| Tool | 是干啥的 |
|---|---|
| search_icons | 按关键词跨图标集搜索 |
| get_icon | 取单个图标（SVG） |
| get_icon_set | 查某个图标集详情（含授权） |
| get_all_icon_sets | 列出全部图标集 |
