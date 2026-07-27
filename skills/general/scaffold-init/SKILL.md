---
name: scaffold-init
description: Use when 用户说"安装 scaffold-init 脚手架"、"装上 skill 脚手架"、"注入 skill 使用指南"、"scaffold init"，或在新项目里希望 Claude Code / Codex 知道整套个人 skill 该怎么用时 —— 先预检查环境按需补装，再把 skills-scaffolding 仓库的 GUIDE.md 与 HABITS.md 挂进项目会话上下文（Claude Code 走 CLAUDE.md + @import，Codex 走 AGENTS.md 符号链接），两个引擎共用同一份内容源。
engines: [claude-code, codex]
---

# Scaffold Init：给项目注入 skill 使用指南

把个人 skill 库的使用指南（GUIDE.md）和协作习惯（HABITS.md）注入当前项目，并保证本机环境里 skill 真实可用。适配三种起点：本机新项目（环境已完整）、别人电脑上已有部分 skill、完全干净的新机器。

**两个引擎、两条注入路径、一份内容源**（机制差异是实测结论，勿改）：

| | Claude Code | Codex |
|---|---|---|
| 入口文件 | `CLAUDE.md` | `AGENTS.md` |
| 挂载方式 | 文件里写相对路径 `@import`，指向项目内符号链接 | **`AGENTS.md` 本身就是符号链接** |
| 为什么 | 只内联**项目内相对路径**的 import（`@~/...` 与绝对路径被**静默忽略**），但相对 import **会跟随符号链接** | **没有 loader 级 import**：`@path` 会被当普通文本原样喂给模型（不报错，是静默曲解）；但**被发现的文件本身允许是符号链接、且可指向项目外** |
| 能挂几份 | 两份（GUIDE + HABITS 各一行 import） | 一份（每级目录最多读一个指令文件）→ 指向合并产物 `scaffold/AGENTS.md` |

两个入口可安全并存：**Codex 默认不读 `CLAUDE.md`**，两个文件都在时它只读 `AGENTS.md`，不会重复注入。

## 怎么做

### 第一阶段：环境预检查与按需补齐

0. **插件模式护栏**：跑 `claude plugin list`（有 claude 时）和 `codex plugin list`（有 codex 时）——**任一**引擎已装 `zephyr-skills` 插件，就说明走的是插件市场模式：GUIDE/HABITS 已由插件 hook 每次会话注入，skill 也已随插件注册。告知用户"本机是插件模式，无需 scaffold-init"，**立即停止**（继续做会造成双模式共存、双重注入）。
1. **定位仓库**，按顺序尝试：
   - 默认路径 `~/coding/personal/skills-scaffolding`
   - `readlink ~/.claude/skills/scaffold-init` 或 `readlink ~/.agents/skills/scaffold-init` 反查仓库根（skill 被链接过就能查到）
   - 都没有（全新机器）→ `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`

   注入内容在仓库的 `scaffold/` 目录下：`GUIDE.md`、`HABITS.md`，以及由二者生成的 `AGENTS.md`。
2. **只读预检查**：`bash <仓库>/scripts/preflight.sh`，它按引擎分别报告收编 skill、git 来源 skill、插件三类的就位情况，不做任何改动。
3. **按需补齐**：
   - 预检查退出码 0（环境完整）→ 什么都不装，直接进第二阶段
   - 有缺口 → `bash <仓库>/scripts/install.sh`。它幂等：已就位的链接会刷新、已装的插件会跳过、已克隆的会 pull，**绝不重复下载已有的东西**；且只处理这台机器上真实存在的引擎
4. 把预检查结果（几缺几、补了什么）汇报给用户。

### 第二阶段：注入本项目

先判定本机有哪些引擎（`command -v claude` / `command -v codex`，或看 `~/.claude` / `~/.codex` 在不在），**只给存在的引擎注入**，别给没装的引擎留死链接。

#### Claude Code 侧

| 仓库文件 | 项目内链接 | 作用 |
|---|---|---|
| `scaffold/GUIDE.md` | `.claude/skills-guide.md` | 什么场景用哪个 skill |
| `scaffold/HABITS.md` | `.claude/habits.md` | 主人的协作习惯与经验 |

```bash
mkdir -p .claude
ln -sfn <仓库>/scaffold/GUIDE.md  .claude/skills-guide.md
ln -sfn <仓库>/scaffold/HABITS.md .claude/habits.md
```

项目根没有 `CLAUDE.md` 就创建；`## Skill 脚手架` 小节已存在就只补该小节里缺的行，否则在文件末尾追加整节（原有内容一字不动）：

```markdown

## Skill 脚手架
@.claude/skills-guide.md
@.claude/habits.md
```

#### Codex 侧

先确保合并产物是新的（它由 GUIDE + HABITS 派生，源改了要重新生成）：

```bash
bash <仓库>/scripts/build-agents-md.sh
ln -sfn <仓库>/scaffold/AGENTS.md AGENTS.md
```

⚠️ 项目根**已有真实 `AGENTS.md`**（不是符号链接）时**绝不覆盖**——那是项目自己的内容。改为：告知用户冲突，给两个选项（把脚手架内容并进原文件、或跳过 Codex 侧注入），由用户定。

### 第三阶段：收尾

5. **逐项幂等检查**：每个链接、每行 import 单独判断——已存在且有效的跳过；缺的补上；链接失效（目标不存在，比如仓库文件挪过位置）的重建。老项目可能只注入过 Claude 侧，重跑时只补 Codex 侧，不重复添加已有的。
6. **git 卫生**：若项目用 git，把 `.claude/skills-guide.md`、`.claude/habits.md`、`AGENTS.md` 加进 `.gitignore`（符号链接是本机绝对路径，不该进版本库；`CLAUDE.md` 里的 import 行可以提交，别的机器上链接缺失时会被静默跳过，无副作用）。
7. **告知生效方式**：新会话自动生效；以后仓库里更新 GUIDE.md / HABITS.md，所有已注入项目自动跟进——但 **Codex 侧读的是合并产物，改完源要跑一次 `build-agents-md.sh`**（`install.sh` 末尾也会跑一次）。

## 红线

- 检测到**任一**引擎已安装 `zephyr-skills` 插件时绝不继续注入（那是插件模式的地盘）
- 预检查通过就绝不跑安装——避免重复下载和无谓折腾；预检查不通过也只跑一次 install.sh，靠其幂等性补缺
- 绝不把 GUIDE.md / HABITS.md 的内容复制进项目——必须走符号链接，保持单一来源
- 绝不覆盖项目里已有的真实 `AGENTS.md` / `CLAUDE.md` 内容，只追加或链接；有冲突交用户定
- 只给本机真实存在的引擎注入
- 工作/公司项目不要主动建议注入，用户明确要求才做
