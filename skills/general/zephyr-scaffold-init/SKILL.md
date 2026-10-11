---
name: zephyr-scaffold-init
description: Use when 用户说"安装 zephyr-scaffold-init 脚手架"、"安装 scaffold-init 脚手架"（旧称，仍认）、"装上 skill 脚手架"、"给这个项目装上红线和记忆"、"同步脚手架"、"scaffold init"，或想让一个项目带上主人的红线、工作习惯与共享记忆时 —— 先体检本机（缺什么补什么），再给项目装上 AGENTS.md 红线区块和 .memory/ 共享记忆，Claude Code 侧把自带的自动记忆目录指向 .memory。重跑即同步脚手架的新版内容，项目改过的部分不覆盖。
engines: [claude-code, codex]
---

# Scaffold Init：给项目装上红线与共享记忆

一句话：**红线和记忆跟着项目走（进 git），skill 留在机器上（全局共用）。**

| 装什么 | 放哪 | 谁怎么读 |
|---|---|---|
| 红线与工作习惯 | 项目 `AGENTS.md` 里的标记区块 | Codex 直接读；Claude 通过 `CLAUDE.md` 里那行 `@AGENTS.md` 读到同一份 |
| 共享记忆（skill 路由等种子 + 项目自己积累的） | 项目 `.memory/` | Claude 当作自己的自动记忆读写；Codex 由全局 SessionStart hook 注入索引 |
| Claude 自动记忆目录 | `.claude/settings.local.json` 的 `autoMemoryDirectory` | 只接受绝对路径，所以每台机器各写一次，不进 git |

Codex 在项目里不需要装任何东西：它的 hook 和记忆读写规则在机器层，由 `install.py` 装。

## 怎么做

1. **定位脚手架仓库**，按顺序试：
   - 默认 `~/coding/personal/skills-scaffolding`
   - `readlink ~/.claude/skills/zephyr-scaffold-init` 或 `readlink ~/.agents/skills/zephyr-scaffold-init`，上溯三级是仓库根
   - 都没有（全新机器）→ `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`
2. **体检本机**：`python3 <仓库>/scripts/install.py --check`。
   - 退出码 0 → 本机完整，什么都不装
   - 有缺口 → `python3 <仓库>/scripts/install.py`（幂等，只补缺）。输出里提示 hook 定义有变化时，告诉用户：打开 codex 输入 `/hooks`，信任 `project_memory.py` 一次
3. **给项目装**：先 `python3 <仓库>/scripts/init_project.py <项目目录> --check`，把它列出的改动讲给用户；用户确认后去掉 `--check` 再跑。它会：
   - 清掉老版本留下的注入（指向脚手架的 `CLAUDE.local.md` / `AGENTS.md` 符号链接、`.gitignore` 里的 `AGENTS.md`）
   - 把这个项目原先存在 `~/.claude/projects/` 下的 Claude 自动记忆搬进 `.memory/`
   - 在 `.memory/` 放入种子记忆，在 `AGENTS.md` 写入红线区块
   - Claude 侧：`CLAUDE.md` 加一行 `@AGENTS.md`，`settings.local.json` 写自动记忆目录，`.gitignore` 挡住 `settings.local.json`
4. **验证真的生效**（不可跳过，见红线）。起新会话让它背内容，**必须禁用文件工具**——否则模型自己去读文件也答得出来，证明不了内容在上下文里：
   ```bash
   echo '不要使用任何工具。原样引用你上下文中「协作红线与工作习惯」的红线第 1 条，再说出你的记忆索引里第一条记忆的标题；没有就回答 NO。' \
     | claude -p --disallowed-tools "Read,Bash,Glob,Grep"
   codex exec --ephemeral \
     '不要执行命令也不要读文件。原样引用你上下文中「协作红线与工作习惯」的红线第 1 条，再说出「# 项目记忆」索引的第一条标题；没有就回答 NO。'
   ```
   ⚠️ `--disallowed-tools` 的工具名必须合成一个参数、提示词走 stdin：写成 `--disallowed-tools Read Bash '提示词'` 时提示词会被当成工具名吞掉，命令直接报错。
5. **收尾**：告诉用户 `AGENTS.md`、`CLAUDE.md`、`.memory/`、`.gitignore` 的改动应该提交进 git（这样才跟着项目走），`settings.local.json` 不提交。按红线，提交和推送前先问用户。

## 同步规则

重跑 `init_project.py` 就是同步。脚手架写进项目的种子记忆和红线区块都记了内容指纹：

- 项目没改过的 → 跟着脚手架更新到新版
- 项目改过的（人改的或 Claude 自己改的）→ 跳过，在输出里列出，由用户决定要不要手动合并
- 脚手架撤掉的种子 → 项目没改过就一并撤掉，改过就保留
- Claude 只改了 metadata（如 `modified` 时间戳）不算改过

## 红线

- 项目里已有的 `AGENTS.md` / `CLAUDE.md` 内容绝不覆盖：脚本只追加或替换自己的标记区块，以及一行 `@AGENTS.md`
- 指向别处的 `AGENTS.md` / `CLAUDE.md` 符号链接不碰，交用户定
- **注入完必须验证**（第 4 步）。文件在、链接对，都证明不了内容进了上下文——老版本的 `@import` 写法在 9 个项目里静默空转了一个多月，期间每次注入都"看起来成功"
- 不往家目录装（脚本会拒绝）
- 提交、推送前先问用户
