---
name: zephyr-scaffold-init
description: Use when 用户说"安装 zephyr-scaffold-init 脚手架"、"安装 scaffold-init 脚手架"（旧称，仍认）、"装上 skill 脚手架"、"注入 skill 使用指南"、"scaffold init"，或在新项目里希望 Claude Code / Codex 知道整套个人 skill 该怎么用时 —— 先预检查环境按需补装，再把 skills-scaffolding 仓库的 GUIDE.md 与 HABITS.md 挂进项目会话上下文。两个引擎同一套机制：入口文件本身做成符号链接（Claude Code 用 CLAUDE.local.md，Codex 用 AGENTS.md），共用同一份内容源。
engines: [claude-code, codex]
---

# Scaffold Init：给项目注入 skill 使用指南

把个人 skill 库的使用指南（GUIDE.md）和协作习惯（HABITS.md）注入当前项目，并保证本机环境里 skill 真实可用。适配三种起点：本机新项目（环境已完整）、别人电脑上已有部分 skill、完全干净的新机器。

**两个引擎、同一套机制、一份内容源**（机制是实测结论，勿改）：

| | Claude Code | Codex |
|---|---|---|
| 入口文件 | `CLAUDE.local.md`（Claude Code 约定的本机私有 memory 文件） | `AGENTS.md` |
| 挂载方式 | **文件本身就是符号链接** | **文件本身就是符号链接** |
| 指向 | `scaffold/AGENTS.md`（GUIDE + HABITS 的合并产物） | 同一个文件 |
| 与项目自有文件的关系 | 与项目 `CLAUDE.md` **同时加载**，互不冲突，项目的 `CLAUDE.md` 不用动 | 每级目录最多读一个指令文件，项目已有真实 `AGENTS.md` 时是冲突，交用户定 |

⚠️ **绝不要改回 `CLAUDE.md` + `@import`。** Claude Code 展开 `@path` 时有一道**外部引用闸**：路径解析出的真实位置必须落在项目根**之内**，否则**静默丢弃**——不报错、不提示、`/memory` 里也看不出来。符号链接确实会被跟随，但跟过去仍在项目外，照样被拦；`.claude/rules/` 目录同样受这道闸管。唯一不受限的是**入口文件本身**——`CLAUDE.md` / `CLAUDE.local.md` 是被直接读取的 memory 文件，不是 include，符号链接指向哪儿都读得到。（2026-08-20 用 9 组对照实验 + 独立复验测定；老写法在本机 9 个项目里静默空转了一个多月才被发现，教训见红线最后一条。）

两个入口可安全并存：**Codex 默认不读 `CLAUDE.md` / `CLAUDE.local.md`**，不会重复注入。

## 怎么做

### 第一阶段：环境预检查与按需补齐

0. **插件模式护栏**：跑 `claude plugin list`（有 claude 时）和 `codex plugin list`（有 codex 时）——**任一**引擎已装 `zephyr-skills` 插件，就说明走的是插件市场模式：GUIDE/HABITS 已由插件 hook 每次会话注入，skill 也已随插件注册。告知用户"本机是插件模式，无需 zephyr-scaffold-init"，**立即停止**（继续做会造成双模式共存、双重注入）。
1. **定位仓库**，按顺序尝试：
   - 默认路径 `~/coding/personal/skills-scaffolding`
   - `readlink ~/.claude/skills/zephyr-scaffold-init` 或 `readlink ~/.agents/skills/zephyr-scaffold-init` 反查仓库根（skill 被链接过就能查到）
   - 都没有（全新机器）→ `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`

   注入内容在仓库的 `scaffold/` 目录下：`GUIDE.md`、`HABITS.md`，以及由二者生成的 `AGENTS.md`。
2. **只读预检查**：`bash <仓库>/scripts/preflight.sh`，它按引擎分别报告收编 skill、git 来源 skill、插件三类的就位情况，不做任何改动。
3. **按需补齐**：
   - 预检查退出码 0（环境完整）→ 什么都不装，直接进第二阶段
   - 有缺口 → `bash <仓库>/scripts/install.sh`。它幂等：已就位的链接会刷新、已装的插件会跳过、已克隆的会 pull，**绝不重复下载已有的东西**；且只处理这台机器上真实存在的引擎
4. 把预检查结果（几缺几、补了什么）汇报给用户。

### 第二阶段：注入本项目

先判定本机有哪些引擎（`command -v claude` / `command -v codex`，或看 `~/.claude` / `~/.codex` 在不在），**只给存在的引擎注入**，别给没装的引擎留死链接。

两侧共用同一份合并产物，先确保它是新的（由 GUIDE + HABITS 派生，源改了要重新生成）：

```bash
bash <仓库>/scripts/build-agents-md.sh
```

#### Claude Code 侧

```bash
ln -sfn <仓库>/scaffold/AGENTS.md CLAUDE.local.md
```

就这一条。`CLAUDE.local.md` 与项目自己的 `CLAUDE.md` 同时加载，所以**不碰项目的 `CLAUDE.md`**，也不需要在 `.claude/` 下建任何链接。

⚠️ 项目根**已有真实 `CLAUDE.local.md`**（不是符号链接）时**绝不覆盖**——告知用户冲突，给两个选项（把脚手架内容并进原文件、或跳过 Claude 侧注入），由用户定。

#### Codex 侧

```bash
ln -sfn <仓库>/scaffold/AGENTS.md AGENTS.md
```

⚠️ 项目根**已有真实 `AGENTS.md`**（不是符号链接）时**绝不覆盖**——那是项目自己的内容。改为：告知用户冲突，给两个选项（把脚手架内容并进原文件、或跳过 Codex 侧注入），由用户定。

### 第三阶段：收尾

5. **老项目迁移**：2026-08-20 之前注入过的项目用的是老写法——`CLAUDE.md` 里两行 `@.claude/skills-guide.md` / `@.claude/habits.md`，外加 `.claude/` 下两个符号链接。**那套从来没生效过**（原因见开头的机制说明）。碰到就清干净：
   - 删掉 `CLAUDE.md` 里的 `## Skill 脚手架` 小节——**只删这一节**，其余内容一字不动；删完若整个文件只剩空白，连文件一并删
   - 删掉 `.claude/skills-guide.md`、`.claude/habits.md` 这两个符号链接（**只删符号链接**，`.claude/` 下别的东西一概不碰）
   - 按第二阶段建好 `CLAUDE.local.md`
6. **逐项幂等检查**：每个链接单独判断——已存在且指向正确的跳过；缺的补上；失效的（目标不存在，比如仓库挪过位置）重建。老项目可能只注入过一侧，重跑时只补缺的那侧。
7. **验证注入真的生效**（不可跳过，见红线）。起一个新会话让它背内容，答不出就是没生效：
   ```bash
   claude -p --disallowed-tools Read Bash Glob Grep \
     '不要使用任何工具。你的上下文里是否包含标题「协作习惯与经验（skills-scaffolding 注入）」？包含就原样引用其中红线第 1 条，不包含只回答 NO_HABITS。'
   ```
   Codex 侧同理跑 `codex exec`。**必须禁用文件工具**——否则模型会自己去 `cat` 那个文件，答得出来但证明不了它在上下文里。
8. **git 卫生**：若项目用 git，把 `CLAUDE.local.md`、`AGENTS.md` 加进 `.gitignore`——它们是本机绝对路径的符号链接，在别人机器和 CI 上必然失效，不该进版本库。
9. **告知生效方式**：新会话自动生效；以后仓库里更新 GUIDE.md / HABITS.md，所有已注入项目自动跟进——但**两侧读的都是合并产物，改完源要跑一次 `build-agents-md.sh`**（`install.sh` 末尾也会跑一次）。

## 红线

- 检测到**任一**引擎已安装 `zephyr-skills` 插件时绝不继续注入（那是插件模式的地盘）
- 预检查通过就绝不跑安装——避免重复下载和无谓折腾；预检查不通过也只跑一次 install.sh，靠其幂等性补缺
- 绝不把 GUIDE.md / HABITS.md 的内容复制进项目——必须走符号链接，保持单一来源
- 绝不覆盖项目里已有的真实 `CLAUDE.local.md` / `AGENTS.md` / `CLAUDE.md` 内容；有冲突交用户定
- 只给本机真实存在的引擎注入
- 工作/公司项目不要主动建议注入，用户明确要求才做
- **注入完必须验证，不许只看链接就报"已完成"**——链接建好、`cat` 读得出、`ls -la` 一切正常，都**证明不了内容进了上下文**。这套机制的失效是完全静默的：老写法在本机 9 个项目里空转了一个多月，期间每次注入都"看起来成功"。只有让一个新会话背出 HABITS 的原文才算数（第三阶段第 7 步）
