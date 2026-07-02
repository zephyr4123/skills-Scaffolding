---
name: scaffold-init
description: Use when 用户想给当前项目"装上 skill 脚手架"、"注入 skill 使用指南"、"scaffold init"，或在新项目里希望 Claude 知道整套个人 skill 该怎么用时 —— 把 skills-scaffolding 仓库的 GUIDE.md 通过项目内符号链接 + @import 挂进项目 CLAUDE.md。
---

# Scaffold Init：给项目注入 skill 使用指南

把个人 skill 库的使用指南（GUIDE.md）注入当前项目的 CLAUDE.md，让本项目的每次会话都自带"什么场景用哪个 skill"的路由知识。

机制（实测结论，勿改）：Claude Code 只内联**项目内相对路径**的 `@import`，指向项目外的路径（含 `@~/...` 和绝对路径）会被静默忽略；但相对路径 import 会跟随符号链接。所以用"项目内符号链接 → 仓库 GUIDE.md"保持单一来源。

## 怎么做

1. **定位指南**：确认 `~/coding/personal/skills-scaffolding/GUIDE.md` 存在；若不存在（换机器或仓库挪位），用 `readlink ~/.claude/skills/scaffold-init` 反查仓库根目录，GUIDE.md 在仓库根。
2. **幂等检查**：项目根 CLAUDE.md 若已包含 `.claude/skills-guide.md` 字样，确认符号链接还有效后告知"已注入过"并停止。
3. **建符号链接**：
   ```bash
   mkdir -p .claude
   ln -sfn <GUIDE.md 的绝对路径> .claude/skills-guide.md
   ```
4. **注入 import**：项目根没有 CLAUDE.md 就创建，有就在末尾追加（原有内容一字不动）：

   ```markdown

   ## Skill 脚手架
   @.claude/skills-guide.md
   ```

5. **git 卫生**：若项目用 git，把 `.claude/skills-guide.md` 加进 .gitignore（符号链接是本机绝对路径，不该进版本库；CLAUDE.md 里的 import 行可以提交，别的机器上链接缺失时会被静默跳过，无副作用）。
6. **收尾**：告知注入完成，新会话自动生效；以后仓库里更新 GUIDE.md，所有已注入项目自动跟进。

## 红线

- 绝不把 GUIDE.md 的内容复制进项目——必须走符号链接 + 相对 import，保持单一来源
- 绝不修改或删除项目 CLAUDE.md 里已有的任何内容，只追加
- 公司项目（含 ae-* skill 语境）不要主动建议注入，用户明确要求才做
