# stock-images（MCP）

- **来源**：社区 `stock-images-mcp`（npm 分发，`npx -y` 即用），聚合 Pexels / Unsplash / Pixabay 三个免版权图库
- **接入**：`mcp/registry.json` 登记，scripts/install.py 注入 Claude Code user scope；stdio 型
- **一句话**：免版权配图检索与下载——三源聚合搜索，选中即下载到本地供页面/文档引用。
- **凭据**：需要 `PEXELS_API_KEY` / `UNSPLASH_API_KEY` / `PIXABAY_API_KEY` 三把（各家开发者后台免费申请）。**值不入库**：registry 只登记键名，scripts/install.py 在当前环境能解析出全部三把时才注入（fail-closed），缺则跳过并提示；本机取值方式见 zephyr-secrets-hygiene 的按需加载器。
- **使用建议**：落地页/文章需要真实摄影素材时用它，AI 生成质感的场景别硬凑。三家授权都宽松但不完全相同（Unsplash 要求不得转售原图等），批量商用前过一眼各家条款。

## Tools 清单

| Tool | 是干啥的 |
|---|---|
| search_images | 三源聚合按关键词搜图 |
| download_image | 下载选中图到本地 |
