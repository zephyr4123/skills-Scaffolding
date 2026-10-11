---
name: skill-library
description: 个人 skill 库装在哪、⚙️CC 标记的含义、缺了 skill 怎么补
metadata:
  node_type: memory
  type: reference
---

本机装有 skills-scaffolding 个人 skill 库，skill 在机器层全局共用，不进项目目录：

- Claude Code 读 `~/.claude/skills`，Codex 读 `~/.agents/skills`，都是指向脚手架仓库 `skills/` 的符号链接
- 脚手架仓库默认在 `~/coding/personal/skills-scaffolding`；不在就 `readlink ~/.claude/skills/zephyr-scaffold-init` 反查（上溯三级是仓库根）
- 标 **⚙️CC** 的 skill 只能在 Claude Code 上跑（依赖它的专有能力或写死了 `.claude/` 路径），Codex 上别调。权威判据是 skill frontmatter 的 `engines:` 字段
- 插件类 skill（`swiftui-pro`、`ios-swift-skills`）依赖第三方插件已安装
- 缺 skill 或插件：在仓库根跑 `python3 scripts/install.py --check` 看缺口，再跑 `python3 scripts/install.py` 补齐（幂等）
- 全部 skill 的详细说明在仓库 `README.md`

相关：[[skill-routing-frontend]] [[skill-routing-ios]] [[skill-routing-general]] [[mcp-tools]]
