---
name: scaffold-init
description: Use when 用户想给当前项目"装上 skill 脚手架"、"注入 skill 使用指南"、"scaffold init"，或在新项目里希望 Claude 知道整套个人 skill 该怎么用时 —— 先预检查环境按需补装，再把 skills-scaffolding 仓库的 GUIDE.md 与 HABITS.md 通过项目内符号链接 + @import 挂进项目 CLAUDE.md。
---

# Scaffold Init：给项目注入 skill 使用指南

把个人 skill 库的使用指南（GUIDE.md）注入当前项目的 CLAUDE.md，并保证本机环境里 skill 真实可用。适配三种起点：本机新项目（环境已完整）、别人电脑上已有部分 skill、完全干净的新机器。

机制（实测结论，勿改）：Claude Code 只内联**项目内相对路径**的 `@import`，指向项目外的路径（含 `@~/...` 和绝对路径）会被静默忽略；但相对路径 import 会跟随符号链接。所以用"项目内符号链接 → 仓库 GUIDE.md"保持单一来源。

## 怎么做

### 第一阶段：环境预检查与按需补齐

1. **定位仓库**，按顺序尝试：
   - 默认路径 `~/coding/personal/skills-scaffolding`
   - `readlink ~/.claude/skills/scaffold-init` 反查仓库根（skill 被链接过就能查到）
   - 都没有（全新机器）→ `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`

   注入文件在仓库的 `scaffold/` 目录下：`scaffold/GUIDE.md` 与 `scaffold/HABITS.md`。
2. **只读预检查**：`bash <仓库>/scripts/preflight.sh`，它会报告收编 skill、git 来源 skill、插件三类的就位情况，不做任何改动。
3. **按需补齐**：
   - 预检查退出码 0（环境完整）→ 什么都不装，直接进第二阶段
   - 有缺口 → `bash <仓库>/scripts/install.sh`。它是幂等的：已就位的链接会刷新、已装的插件会跳过、已克隆的会 pull，**绝不重复下载已有的东西**
4. 把预检查结果（几缺几、补了什么）汇报给用户。

### 第二阶段：注入本项目

要注入的文件有两个，处理方式相同（都在仓库根）：

| 仓库文件 | 项目内链接 | 作用 |
|---|---|---|
| scaffold/GUIDE.md | `.claude/skills-guide.md` | 什么场景用哪个 skill |
| scaffold/HABITS.md | `.claude/habits.md` | 主人的协作习惯与经验 |

5. **逐文件幂等检查**：对每个文件单独判断——项目根 CLAUDE.md 已包含对应 import 行且符号链接目标有效的跳过；缺 import 行的补行；import 行在但链接失效（目标不存在，比如仓库文件挪过位置）的重建链接（老项目可能只注入过 GUIDE，重跑时只补 HABITS，不重复添加已有的）。
6. **建符号链接**：
   ```bash
   mkdir -p .claude
   ln -sfn <仓库>/scaffold/GUIDE.md .claude/skills-guide.md
   ln -sfn <仓库>/scaffold/HABITS.md .claude/habits.md
   ```
7. **注入 import**：项目根没有 CLAUDE.md 就创建；`## Skill 脚手架` 小节已存在就只在该小节里补缺的行，否则在文件末尾追加整节（原有内容一字不动）：

   ```markdown

   ## Skill 脚手架
   @.claude/skills-guide.md
   @.claude/habits.md
   ```

8. **git 卫生**：若项目用 git，把 `.claude/skills-guide.md` 和 `.claude/habits.md` 加进 .gitignore（符号链接是本机绝对路径，不该进版本库；CLAUDE.md 里的 import 行可以提交，别的机器上链接缺失时会被静默跳过，无副作用）。
9. **收尾**：告知注入完成，新会话自动生效；以后仓库里更新 GUIDE.md，所有已注入项目自动跟进。

## 红线

- 预检查通过就绝不跑安装——避免重复下载和无谓折腾；预检查不通过也只跑一次 install.sh，靠其幂等性补缺
- 绝不把 GUIDE.md 的内容复制进项目——必须走符号链接 + 相对 import，保持单一来源
- 绝不修改或删除项目 CLAUDE.md 里已有的任何内容，只追加
- 工作/公司项目不要主动建议注入，用户明确要求才做
