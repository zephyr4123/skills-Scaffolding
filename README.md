<div align="center">

# 🧰 Skills Scaffolding

**个人 Agent Skill 脚手架 —— 收编、分发、恢复、注入，一站式**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-35-blue)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin_marketplace-D97706)
![Codex](https://img.shields.io/badge/Codex-supported-10A37F)

*两条命令订阅全套 skill 与协作习惯 —— Claude Code 与 Codex 通用，或 git clone 完全掌控*

</div>

---

一套可复制的个人 Agent Skill 脚手架。它做四件事：

1. **收编**：把散落各处的 Agent Skill 收进一个有版本管理的仓库，配上"每个是干啥的"总索引
2. **市场分发**：本仓库自身就是一个插件市场，**Claude Code 与 Codex 都能订阅**，各两条命令拿到全套
3. **一键恢复**：git 模式下任何机器一条命令装齐全部 skill 和插件，幂等、只补缺、不重复下载
4. **会话注入**：让每次会话自动知道**什么场景用哪个 skill**（GUIDE.md）和**主人喜欢怎么干活**（HABITS.md）——插件模式由 hook 完成，git 模式说一句"安装 scaffold-init 脚手架"

> 这份 README 同时写给两类读者：**人类**（往下看快速开始）和 **AI 助手**（见[给 AI 助手的操作手册](#给-ai-助手的操作手册)——如果你是一个正在读这份文档的模型，无论跑在 Claude Code 还是 Codex 上，那一节都是为你写的）。

## 目录

- [快速开始](#快速开始)
- [精选第三方插件](#精选第三方插件catalog)
- [引擎适配](#引擎适配)
- [端到端原理](#端到端原理)
- [给 AI 助手的操作手册](#给-ai-助手的操作手册)
- [仓库结构](#仓库结构)
- [Skill 总索引](#收编的-skillskills)
- [install.manifest 格式](#installmanifest-格式)
- [维护手册](#维护手册)
- [Fork 指南与 FAQ](#fork-指南与-faq)

---

## 快速开始

先选模式（二选一，别同时用）：

| 你是谁 | 选哪条 | 成本 |
|---|---|---|
| **使用者**：想直接用这套 skill 和习惯 | 插件市场模式 | 两条命令，自动更新 |
| **维护者 / 魔改者**：想改 skill 内容、收编自己的东西 | git 仓库模式 | clone + 一条命令，改完即生效 |

### 模式一：插件市场（推荐给使用者）

**Claude Code**——在会话里执行两条斜杠命令：

```
/plugin marketplace add zephyr4123/skills-Scaffolding
/plugin install zephyr-skills@skills-scaffolding
```

或在终端里用**等价的 CLI 写法**（headless / CI / 脚本化 / 让 agent 代劳时用这套——`/plugin` 斜杠命令在非交互环境下不可用）：

```bash
claude plugin marketplace add zephyr4123/skills-Scaffolding
claude plugin install zephyr-skills@skills-scaffolding
```

> 首次在一个新目录里起交互式会话时，Claude Code 会先弹一屏 workspace 信任确认（`Is this a project you created or one you trust?`），选信任才进得去。这是它的安全设计，跟本脚手架无关。

**Codex**——终端里执行两条命令：

```bash
codex plugin marketplace add https://github.com/zephyr4123/skills-Scaffolding
codex plugin add zephyr-skills@skills-scaffolding
```

> Codex 原生读 `.claude-plugin/` 格式的市场清单（官方把 `.claude-plugin/marketplace.json` 列为 legacy-compatible 路径）。插件清单这边本仓库放了**两份**——Codex 优先读 `.codex-plugin/plugin.json`（30 个），Claude 读 `.claude-plugin/plugin.json`（35 个），**同一个仓库、同一条命令、同一个版本号，两个引擎各拿各的**，原理见[引擎适配](#引擎适配)。

**装完你得到什么：**

- Claude Code 上全部 **35** 个 skill、Codex 上 **30** 个立即可用（以 `zephyr-skills:xxx` 命名空间注册，模型自动按场景调用）。差额是内容上依赖 Claude Code 专有能力的那几个，见[引擎适配](#引擎适配)
- **每次会话自动注入** GUIDE（skill 路由）与 HABITS（协作习惯）——插件的 SessionStart hook 完成，零脚本、零配置
- **更新省心**：`claude plugin update zephyr-skills` / `codex plugin add zephyr-skills@skills-scaffolding` 拿到最新

> ⚠️ **Codex 用户注意**：插件自带的 hook **默认不被信任**，仅安装插件**不足以**拿到 GUIDE/HABITS 注入。首次启动 Codex 时会**自动弹**信任确认屏（不用手动敲 `/hooks`），选 `Trust all and continue` 之后 hook 才会执行。实测是**两个屏幕**（先项目信任、再 hook review），且第二屏**默认选中的是 `Review hooks` 而不是 `Trust all`**，所以最少要按 `Enter → ↓ → Enter` 三次。这是 Codex 的安全设计，不是装坏了。

**日常管理：**

```bash
claude plugin disable zephyr-skills --scope project   # 本项目关闭（如工作/公司项目），其他项目不受影响
claude plugin enable zephyr-skills --scope project    # 重新打开
claude plugin update zephyr-skills                    # 更新到最新版本
claude plugin uninstall zephyr-skills                 # 整体卸载
```

**边界说明：**

- catalog 里的第三方插件**不会**随本插件自动安装——它们在别人的市场上，各有各的装法与限制，见下方[精选第三方插件](#精选第三方插件catalog)一节
- 插件模式是**只读订阅**：想改 skill 内容，走模式二

### 模式二：git 仓库（推荐给维护者 / 想改 skill 的人）

前提：机器上已装 git，以及 [Claude Code](https://claude.com/claude-code) 与 Codex **至少一个**（`install.sh` 会自动探测装了哪些，只处理存在的）。

```bash
git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding
bash ~/coding/personal/skills-scaffolding/scripts/install.sh
```

`install.sh` **自己探测这台机器上有哪些引擎**，只装存在的那些：

| 探测到 | 做什么 |
|---|---|
| Claude Code | 35 个 skill 链接进 `~/.claude/skills`，`claude plugin` 装三方插件 |
| Codex | 30 个 Codex 适用的 skill 链接进 `~/.agents/skills`，`codex plugin` 装三方插件 |
| 两个都有 | 都做；git 来源的 skill 只 clone 一份，另一边符号链接共用 |

不论探测到哪个引擎，脚本最后都会**无条件**跑一次 `scripts/build-agents-md.sh`，从 `GUIDE.md + HABITS.md` 重新生成 `scaffold/AGENTS.md`（Codex 侧的注入入口）。**这会写你 clone 出来的工作树**——但内容是幂等派生的，源没改时重新生成的结果一字不差，`git status` 保持干净。

**想先试用、不污染现有环境？** 脚本认三个环境变量覆盖点：

```bash
CLAUDE_SKILLS_DIR=/tmp/试用/claude \
CODEX_SKILLS_DIR=/tmp/试用/codex \
bash scripts/install.sh          # 链接全建到临时目录，不碰 ~/.claude 与 ~/.agents
```

（第三个是 `INSTALL_MANIFEST`，可指向你自己的清单。注意这三个只覆盖**本脚本的写入目标**，不隔离引擎自身的配置与 skill 发现——引擎级隔离是 Claude Code / Codex 自己的事。）

另外：`~/.claude/skills` 或 `~/.agents/skills` 下如果已经有**同名的真实目录**（不是符号链接），脚本会明确跳过并提示，**不会接管、不会覆盖**你原有的东西。

脚本幂等，重跑安全：**符号链接会无条件重建**（目标不变，只是 mtime 刷新）、**已存在的真实目录不接管**（会明确跳过并提示）、已装的插件跳过、已克隆的仓库 `git pull`——不会重复下载任何东西。

> 克隆到别的路径也行，脚本会从自身位置定位仓库；但默认路径能让 scaffold-init 的自动发现更顺畅。

### 新项目（仅 git 模式；插件模式已由 hook 全自动注入，**不要**再说这句话，会双重注入）

在项目目录里对 Claude Code 或 Codex 说一句：

> **安装 scaffold-init 脚手架**

> 请带上 skill 名说全——只说"装脚手架"是个通用词，可能给你装成别的框架脚手架（真实踩过的坑）。

它会执行 `scaffold-init` skill：先体检环境（缺 skill 就补、全齐就零动作），再按引擎注入：

| 引擎 | 注入方式 |
|---|---|
| Claude Code | 项目内建符号链接 `.claude/skills-guide.md` / `.claude/habits.md`，`CLAUDE.md` 里写相对路径 `@import` |
| Codex | 项目根的 `AGENTS.md` **本身**做成符号链接，指向 `scaffold/AGENTS.md`（GUIDE+HABITS 的合并产物） |

两种方式都不复制内容——仓库里改一行，所有已注入项目下次会话自动跟进。两个入口可安全并存：**Codex 默认不读 `CLAUDE.md`**，不会重复注入。

> 前提：这台机器跑过一次上面的安装命令（否则模型还不认识 scaffold-init 这个 skill）。

### 日常

- **忘了某个 skill 是干啥的** → 看下面的[总索引](#收编的-skillskills)
- **收了新 skill / 悟了新经验** → 见[维护手册](#维护手册)

---

## 精选第三方插件（catalog/）

这套脚手架的另一半价值：不只收编 skill，还替你**把第三方插件的坑踩完了**——每个都在真实项目里用过、建了档案（来源、装法、每个 skill 是干啥的），试错成本已经付过。

**Claude Code**（会话内斜杠命令，或终端里用等价的 CLI 写法）：

```bash
# 终端 CLI 写法（headless / 脚本化 / agent 操作用这套）
claude plugin marketplace add twostraws/swiftui-agent-skill
claude plugin install swiftui-pro@swiftui-agent-skill
claude plugin install superpowers@claude-plugins-official
```

会话内则是同名的斜杠形式：`/plugin marketplace add …`、`/plugin install …`。

**Codex**：

```bash
codex plugin marketplace add https://github.com/twostraws/swiftui-agent-skill
codex plugin add swiftui-pro@swiftui-agent-skill
```

或者直接跑 `scripts/install.sh`，它按 `install.manifest` 给每个引擎装它装得上的那些。

| 插件 | 为什么值得装 | 引擎 | 档案 |
|---|---|---|---|
| **swiftui-pro** | Paul Hudson（Hacking with Swift 作者）出品，按九份参考清单系统审查 SwiftUI 代码的现代 API、数据流与性能 | 两个都行 | [查看](catalog/swiftui-pro.md) |
| **superpowers** | 软件工程流程纪律全家桶（obra/Jesse Vincent 出品，经 Anthropic 官方市场分发）：脑暴、计划、TDD、系统化调试（14 个 skill）——很重，建议按需点名使用 | 仅 Claude Code | [查看](catalog/superpowers.md) |
| ~~**ios-swift-skills**~~ | iOS 开发一包全覆盖（10 个 skill）。**⚠️ 当前装不上**，见下方说明 | 暂不可用 | [查看](catalog/ios-swift-skills.md) |

> ⚠️ **`superpowers` 有个顺序依赖**：它所在的 Anthropic 官方市场 `claude-plugins-official` 是 Claude Code 内建的，但**只在交互式界面首次启动时才落地**，`-p` / 脚本模式不触发。所以全新机器上要**先在终端起一次 `claude`（进到界面再退出），再跑 install.sh**，否则这条会被跳过。install.sh 检测到这种情况会打印同样的提示。

> ⚠️ **`ios-swift-skills` 当前对所有新用户不可用**（v1.7.x 实测）：上游 `patrickserrano/skills` 的 `.claude-plugin/` 下只有 `plugin.json`，**没有 `marketplace.json`**，两个引擎 add 都会失败。报错文案是「Marketplace file not found at 〈本地缓存路径〉」——**指向本地路径，极易误判成自己环境坏了**，根因其实在上游仓库结构。已从 `install.manifest` 注释掉；上游补上清单后取消注释即可恢复。

插件本体由各自作者维护更新，本仓库只存档案不存副本——所以它们**不会**随 zephyr-skills 自动安装，要用就敲上面的命令；git 模式则由 install.sh 按 `install.manifest` 自动处理。

---

## 引擎适配

这套脚手架同时服务三类用户。**下表每一格都是实测结论**——在真实 Codex（`codex-cli 0.145.0`）的隔离环境里装过、跑过、取过证，不是读文档推出来的。

| | 只用 Claude Code | 只用 Codex | 两个都用 |
|---|---|---|---|
| **插件市场** | ✅ `/plugin marketplace add` + `/plugin install` | ✅ `codex plugin marketplace add` + `codex plugin add`（原生读 `.claude-plugin/` 格式） | ✅ 各装各的，同一个仓库 |
| **可用 skill** | ✅ 35 个 | ✅ 30 个（两条通道都过滤，见下） | ✅ 各取所需 |
| **GUIDE/HABITS 自动注入** | ✅ 装完即生效 | ⚠️ 装完还要**信任一次 hook**（见下） | ✅ 两边独立生效 |
| **git 模式一键装** | ✅ `install.sh` 自动探测 | ✅ 同一条命令 | ✅ 自动两边都装，git 来源 skill 只 clone 一份 |
| **项目级注入** | ✅ `CLAUDE.md` + `@import` 符号链接 | ✅ `AGENTS.md` **本身**是符号链接 | ✅ 两个入口并存，**Codex 默认不读 `CLAUDE.md`**，不会重复注入 |
| **单一来源** | ✅ 仓库改一行，全机器全项目跟进 | ✅ 同左 | ✅ 同左 |

### ⚠️ Codex 的一个必知差异：hook 信任门槛

**仅安装插件不足以拿到 GUIDE/HABITS 注入。** Codex 把插件自带的 hook 视为 non-managed，默认不执行——这是它的安全设计。首次启动会自动弹信任确认屏（不用手动敲 `/hooks`），选 `Trust all and continue` 之后才生效；全新环境会多一个项目信任屏，合计两下。

装完发现没注入，先看是不是卡在这里，别以为坏了。

### 为什么两边都能读同一份清单

Codex 原生认 Claude Code 的插件格式，这不是巧合也不是迁移产物：

- **市场清单**：官方文档把 `$REPO_ROOT/.claude-plugin/marketplace.json` 列为 legacy-compatible 路径
- **插件清单**：其开源实现里有 `DISCOVERABLE_PLUGIN_MANIFEST_PATHS = [".codex-plugin/plugin.json", ".claude-plugin/plugin.json", ".cursor-plugin/plugin.json"]`，按序回落，带单测
- **skill 格式**：两边都是 `SKILL.md` + YAML frontmatter，`name` / `description` 同义
- **环境变量**：Codex 执行 hook 时会**主动注入** `CLAUDE_PLUGIN_ROOT` / `CLAUDE_PLUGIN_DATA` 做兼容

所以本仓这些 skill 的正文**一个字都没为 Codex 改过**，两边共用。

### 两条分发通道各自怎么过滤

| 通道 | 靠什么过滤 | 实测结果 |
|---|---|---|
| **git 模式** | `install.sh` 读每个 skill frontmatter 的 `engines:` | Codex 侧只链 30 个，5 个 Claude-only 一个没链 |
| **插件模式** | **双 manifest**：Codex 读 `.codex-plugin/plugin.json`（30 条），Claude 读 `.claude-plugin/plugin.json`（35 条） | 两边各拿各的，Claude-only 不进 Codex 的可见清单 |

双 manifest 能成立，是因为 Codex 按 `DISCOVERABLE_PLUGIN_MANIFEST_PATHS` 顺序探测清单：

```
.codex-plugin/plugin.json  →  .claude-plugin/plugin.json  →  .cursor-plugin/plugin.json
```

它优先读第一个；而 **Claude Code 只认 `.claude-plugin/plugin.json`**（实测其加载日志形如 `Checking plugin zephyr-skills: skillsPaths=<N> paths`，其中 N 恒等于 `.claude-plugin/plugin.json` 的 skills 条数、与 `.codex-plugin/` 那份的条数无关——多出来的 `.codex-plugin/` 目录对它完全惰性）。同一个仓库、同一条安装命令、同一个版本号——两个引擎各读各的清单。

> `.codex-plugin/plugin.json` 是**派生产物**，由 `scripts/build-codex-manifest.sh` 从 `.claude-plugin/plugin.json` + 各 skill 的 `engines:` 生成，CI 校验其与源同步。手工维护的永远只有那两处。
>
> 为什么不用别的办法（都实测否掉了）：`agents/openai.yaml` 的 `policy.products` 只有正向白名单、`claude-code` 不是合法取值；manifest 的 `interface` 字段被忽略；`config.toml` 的 `[[skills.config]]` 是用户侧配置、不随插件分发；拆成两个 plugin 要维护两套 ID 与版本。**光靠 GUIDE 标注和正文声明也不够——路由阶段只看得到 name/description/path，正文那时还没被读取。**

### 哪 5 个在 Codex 上跑不了，为什么

每个 skill 的 frontmatter 都有 `engines:` 字段（CI 校验），GUIDE 路由里标 **⚙️CC**：

| Skill | 原因 |
|---|---|
| `workflow-orchestration` | 整篇建立在 Claude Code 的 Workflow 工具上（`parallel`/`pipeline`、`effort`、缓存前缀链、journal 字段），换引擎需重写而非改措辞 |
| `background-watch` | 依赖 `Monitor` 与后台任务两个 harness 能力 |
| `impeccable` | 正文 37 处硬编码 `node .claude/skills/impeccable/scripts/…`，装到 Codex 的 `.agents/skills` 下第一步就 ENOENT。**上游本体其实支持 Codex**，靠它自己的安装器改写路径，而本仓只收了裸副本——这是打包缺陷不是方法论缺陷 |
| `design-loop` | 上游作者自己在 frontmatter 声明 `compatibility: claude-code-only`，尊重上游不擅自扩大 |
| `humanizer` | 上游声明支持 Claude Code 与 OpenCode，未提 Codex，同样不替它扩大 |

判定标准是**「内容在另一个引擎上能不能真正执行」**，不是话题相不相关。拿不准一律判窄——标窄了只少推荐一次，标宽了会让人踩空。

## 端到端原理

**内容永远只有仓库里一份**，通过两条通道到达用户。

**插件市场通道**（使用者，全自动）：

```
┌─ GitHub 仓库（.claude-plugin/ 声明市场与插件）────────────────┐
│        │  /plugin marketplace add + /plugin install            │
│        ▼                                                       │
│  本机插件缓存（~/.claude/plugins/cache/…，随市场刷新自动更新）  │
│        ├── skills/ × 35 ──────▶ 注册进 Claude Code（Codex 30 个）│
│        └── SessionStart hook ─▶ 每次会话自动注入 GUIDE + HABITS │
└────────────────────────────────────────────────────────────────┘
```

**git 仓库通道**（维护者，符号链接三层，改完即全局生效）：

```
┌─ 仓库层（单一来源，git 管理）─────────────────────────────┐
│  skills/<领域>/<skill>/   收编的 skill 完整副本              │
│  scaffold/GUIDE.md        场景→skill 路由表（面向模型）      │
│  scaffold/HABITS.md       协作习惯与经验（面向模型）         │
│  install.manifest         插件与 git 来源 skill 清单         │
│  catalog/*.md             三方插件档案（面向人类）           │
└──────────────┬───────────────────────────────────────────┘
               │ scripts/install.sh（幂等）
┌─ 机器层 ──────▼───────────────────────────────────────────┐
│  ~/.claude/skills/<skill> ──符号链接──▶ 仓库/skills/…/<skill> │
│  Claude Code 插件         ──claude plugin install──▶ 市场    │
│  scripts/preflight.sh：只读体检，报告缺口，不动任何东西       │
└──────────────┬───────────────────────────────────────────┘
               │ scaffold-init skill（说"安装 scaffold-init 脚手架"触发）
┌─ 项目层 ──────▼───────────────────────────────────────────┐
│  <项目>/.claude/skills-guide.md ──链接──▶ 仓库/scaffold/GUIDE.md  │
│  <项目>/.claude/habits.md       ──链接──▶ 仓库/scaffold/HABITS.md │
│  <项目>/CLAUDE.md 末尾:  @.claude/skills-guide.md            │
│                          @.claude/habits.md                  │
│  → 每次会话自动把两份内容内联进上下文                        │
└───────────────────────────────────────────────────────────┘
```

三条设计决策，也是踩坑后的实测结论：

1. **全程符号链接，不复制内容。** 仓库里改一行 GUIDE/HABITS/skill 正文，所有机器所有项目下次会话自动生效，不存在过期副本。
2. **项目层必须"先链接进项目、再相对路径 import"。** Claude Code 的 CLAUDE.md `@import` 只内联**项目内相对路径**，指向项目外的路径（`@~/...` 或绝对路径）会被**静默忽略**——但相对路径 import 会跟随符号链接。这是本仓库反复实验得出的行为结论，也是绕开它的最短路径。
3. **一切可重复执行。** preflight.sh 纯只读；install.sh 与 scaffold-init 幂等（已就位的链接刷新、已装的插件跳过、已注入的 import 行不重加）。任何一步中断了重跑即可，不会产生冗余。

---

## 给 AI 助手的操作手册

如果你是一个 Claude Code 或 Codex 会话，用户让你操作这个脚手架，按下表办事。

**第 0 步，先判定模式**：跑 `claude plugin list`（Codex 上跑 `codex plugin list`）——里面有 `zephyr-skills` 就是**插件模式**，skill 与注入已由插件承载，下表标「仅 git 模式」的行**不要执行**（跑 preflight / install.sh / scaffold-init 会造成双模式共存、双重注入），对应意图直接回答"本机是插件模式，无需此操作"。没有该插件才按 git 模式继续。

git 模式下先定位仓库根（下表 `<仓库>` 的取值，按顺序尝试）：① 默认 `~/coding/personal/skills-scaffolding`；② `readlink ~/.claude/skills/scaffold-init` 反查（链接目标的上三级就是仓库根）；③ 都没有则 `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`。

| 用户意图 | 你该做的 |
|---|---|
| "安装 scaffold-init 脚手架" / "注入 skill 指南"（仅 git 模式） | 调用 `scaffold-init` skill；若本机没有该 skill，先按下一行恢复环境，再执行 `<仓库>/skills/general/scaffold-init/SKILL.md` 里的步骤 |
| 恢复/检查环境（仅 git 模式） | 先 `bash <仓库>/scripts/preflight.sh`（只读，退出码 0=完整 1=有缺口）；**仅当有缺口时**才 `bash <仓库>/scripts/install.sh` |
| 收编一个新 skill | 复制 skill 目录进 `skills/<领域>/`（去掉内嵌 `.git`，保留 LICENSE；没有合适领域可新建目录，脚本按 `skills/*/*/` 自动识别），然后：**frontmatter 加 `engines:` 字段**（CI 硬校验；内容依赖某引擎专有能力或硬编码 `.claude/` 路径的只写那一个）、README 索引表加一行**并更新分组标题里的计数**、GUIDE.md 路由加一条（claude-only 的标 ⚙️CC）、`.claude-plugin/plugin.json` 的 `skills` 数组加一条路径、跑 `bash scripts/build-codex-manifest.sh` 重新生成 Codex 侧清单（CI 会校验同步），最后跑一次 install.sh 让链接生效 |
| 新增一个三方插件 | `catalog/` 建档案（来源、安装命令、skill 清单），`install.manifest` 加一行 `plugin`，README 插件表加一行，插件含 skill 则 GUIDE.md 路由加一条，最后跑一次 install.sh 完成安装 |
| 记录新的经验习惯 | 在 HABITS.md 对应小节加一行，无需其他动作（所有已注入项目自动继承） |
| "这个项目别用这套习惯/skill"（插件模式） | `claude plugin disable zephyr-skills --scope project`，只影响当前项目 |
| 更新脚手架到最新 | 插件模式 `claude plugin update zephyr-skills`；git 模式在仓库里 `git pull`，符号链接自动生效 |

硬性规则：

- 本仓库的 commit 信息用中文、**绝不带任何 AI 署名**（HABITS.md「Git」小节的头两条）
- preflight 通过就不要跑安装；不要把 GUIDE/HABITS 的内容复制进任何项目（必须走符号链接 + 相对 import）
- 修改 `scripts/*.sh` 时注意：bash 3.2（macOS 默认）里变量后紧跟中文全角字符会解析错误，必须写 `${var}中文` 而不是 `$var中文`

---

## 仓库结构

```
skills/           收编的 skill 完整副本，按领域分组（design/frontend/ios/writing/general）
                  每个 SKILL.md 的 frontmatter 用 engines: 声明适用引擎，是全仓的过滤真相源
catalog/          第三方插件档案：本体由插件市场管理，这里记来源、装法、用途、当前可用性
scaffold/         注入文件：GUIDE.md（场景→skill 路由表）+ HABITS.md（协作习惯与红线，活文档）
                  AGENTS.md 是二者的合并派生产物，供 Codex 侧注入用（勿手改）
.claude-plugin/   marketplace.json + plugin.json（35 个 skill）：Claude Code 读这份
.codex-plugin/    plugin.json（30 个 skill）：Codex 优先读这份，派生产物（勿手改）
.github/          发版流水线：push 即校验清单，版本号变更自动打 tag + 发 Release
hooks/            插件模式的 SessionStart hook：自动把 scaffold/ 两个文件注入会话
install.manifest  声明式清单：装哪些第三方插件（可标适用引擎）、克隆哪些 git 来源 skill
scripts/
  install.sh              一键恢复：按引擎链接 skill + 装插件 + 克隆 git skill（幂等）
  preflight.sh            只读体检：按引擎报告环境缺口，退出码 0=完整 1=有缺
  build-agents-md.sh      生成 scaffold/AGENTS.md，--check 校验与源同步
  build-codex-manifest.sh 生成 .codex-plugin/plugin.json，--check 校验与源同步
templates/        新写 skill 的起步模板（已含 engines: 字段）
```

同一份内容、两条分发通道：**插件市场模式**（消费者视图——只读订阅、hook 自动注入、自动更新）和 **git 仓库模式**（维护者视图——符号链接可直接改、scaffold-init 按项目注入）。选一条用即可。

---

## 收编的 Skill（skills/）

> 标 **⚙️CC** 的只能在 Claude Code 上跑（原因见[引擎适配](#引擎适配)），其余两个引擎通用。权威判据是每个 skill frontmatter 里的 `engines:` 字段，CI 会校验。

### design — 设计品味（21 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [animation-vocabulary](skills/design/animation-vocabulary/) | 动效术语反查词典：Web 动画术语按 12 类整理，从「看着像什么、感觉像什么」倒查出准确叫法，一次给首选词加 1~2 个近义词并说清差别；词表里没有就直说没有，不许现编（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 效果描述得出来但叫不出名字，需要一个准确的词去跟设计师沟通、写进需求、或喂给 AI 当 prompt 时。⚠️ 词表漏了 scroll snap / FLIP / scrub，它会答「没有」而不是猜 |
| [apple-design](skills/design/apple-design/) | 把 Apple 的流体界面做法翻译成网页实现：手指 1:1 跟随、动画随时能抓住反向、松手把速度交给弹簧、用减速公式算落点再吸附、边界橡皮筋；另含半透明材质分层、随字号变的字距行高、reduced-motion/transparency/contrast 三档降级。给的是能直接抄的公式和数值（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做手势驱动的网页交互——拖拽、滑动关闭、bottom sheet、可打断的转场、弹簧调参时；写原生 SwiftUI 走 swiftui-design-principles。⚠️ 文中「~300ms tap delay」是十年前的知识，现代浏览器早已移除，别去项目里找它 |
| [brandkit](skills/design/brandkit/) | 高端品牌套件图像生成：以品牌策略为先，产出 logo 系统、品牌规范板、identity deck 级演示图 | 需要为产品/品牌生成 logo 概念、品牌视觉板、品牌手册风格图像时 |
| [design-taste-frontend](skills/design/design-taste-frontend/) | 反 AI 味前端设计：先推断设计方向和三档参数，再按大量禁令产出不模板化的页面 | 写落地页、作品集、营销站或改版，要避免紫渐变/居中 hero/Inter 等 AI 默认审美时 |
| [design-taste-frontend-v1](skills/design/design-taste-frontend-v1/) | 上面那个的旧版规则集（v1） | 只在需要与 v1 行为完全兼容时用，新项目默认用 v2 |
| [emil-design-eng](skills/design/emil-design-eng/) | Emil Kowalski 的设计工程哲学：动画决策框架（是否动/缓动/时长）、组件手感细节、性能与可访问性规则（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做 Web UI 动画/交互打磨，想让界面细节有高级手感（spring、手势、popover/toast）时 |
| [find-animation-opportunities](skills/design/find-animation-opportunities/) | 扫代码库找「该动却没动」的地方：四道闸逐条筛（一天会被看见多少次 / 动机能不能被命名 / 300ms 内做不做得完 / 会不会妨碍读数据），键盘触发和高频操作一律否决，最后只留 5~7 条，每条带 file:line 和确切的曲线、时长、属性，还强制列出「考虑过但否掉了」的名单。只读不改代码（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 觉得 Web 界面太死板、想先拿一张有优先级的动效待办清单，或想搞清楚哪些地方其实**不该**加动画时；审已有动效代码走 review-animations，原生 iOS 别用 |
| [frontend-design](skills/design/frontend-design/) | 指导生成有独特审美的前端界面代码，强调字体、配色、动效与布局的大胆方向（来自 [anthropics/skills](https://github.com/anthropics/skills)，Apache-2.0） | 构建网页组件/页面/应用，希望视觉精致独特、不落俗套时 |
| [gpt-taste](skills/design/gpt-taste/) | 强制随机化布局、AIDA 结构、宽幅排版、bento 网格与 GSAP 滚动动效 | 生成落地页等 Web UI，想要 Awwwards 级设计感时 |
| [high-end-visual-design](skills/design/high-end-visual-design/) | 按高端设计公司标准做网页视觉：禁廉价默认，规定字体、双层卡片、大留白、弹簧动效 | 生成或美化网页 UI（React/Tailwind/HTML），要高端质感时 |
| [imagegen-frontend-mobile](skills/design/imagegen-frontend-mobile/) | 生成 app 原生感的移动端 UI 概念图（多屏流程、手机 mockup），只出图不写码 | 为 iOS/Android app 生成 onboarding、首页等多屏视觉概念图时 |
| [imagegen-frontend-web](skills/design/imagegen-frontend-web/) | 生成高端网页设计参考图：每个页面 section 出一张横图，反 AI 俗套艺术指导 | 为落地页/营销站生成设计概念图（供照图实现）时 |
| [impeccable](skills/design/impeccable/) | ⚙️CC 前端界面设计打磨全能 skill：23 个子命令覆盖构建、评审、精修、动效、配色、排版、live 浏览器实时迭代，内置反 AI 味硬标准与 slop 检测（来自 [pbakaus/impeccable](https://github.com/pbakaus/impeccable)，v3.9.1） | 设计、重构、评审或打磨任何前端 UI，尤其要摆脱"一眼 AI 生成"的平庸感、或做 a11y/性能/响应式审计时 |
| [improve-animations](skills/design/improve-animations/) | 整个仓库动效代码的只读审计器：按八类逐条挑问题并回原位复核，排成优先级表让你挑，再把选中的各写成一份计划文件——精确到文件行号、目标 cubic-bezier、时长、验收怎么看，交给别的 agent（哪怕便宜模型）照着改；自己一行源码都不动（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 接手一个 Web 项目觉得「动起来不对劲」、想系统过一遍并排出先改哪个时；或想把判断和改代码拆开。只审一个 diff 用 review-animations。⚠️ 它会在仓库根建 `plans/` 写文件，有推送闸门的项目先决定这目录进不进版本控制 |
| [industrial-brutalist-ui](skills/design/industrial-brutalist-ui/) | 工业粗野主义 UI：瑞士印刷+军用终端美学，硬网格、巨型字体、单一红色点缀、CRT 做旧 | 数据密集仪表盘、作品集、编辑类网页想要机密蓝图/机械终端质感时 |
| [minimalist-ui](skills/design/minimalist-ui/) | 极简编辑风 UI：暖色单色调+衬线大标题+bento 网格+微妙动效，禁渐变重阴影 | 想要 Notion 式高级极简文档风、避免 SaaS 模板感时 |
| [pick-ui-library](skills/design/pick-ui-library/) | 19 条「前端任务 → 用哪个库」的钦定对照表（toast 用 Sonner、拖拽用 dnd kit、长列表用 Virtuoso、状态用 zustand…），只给一个答案不列菜单，另附 6 条「你正在手搓一个已有库解决的问题」自查；仅覆盖 React Web（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 在 React 前端项目里要新引入一个 UI 依赖、懒得自己比选时。需显式点名。⚠️ 表里只给官网不给包名，两处会装错：Base UI 的包是 `@base-ui-components/react`（裸 `base-ui` 是停更的无关包）、Virtuoso 是 `react-virtuoso` |
| [prototype](skills/design/prototype/) | 把你描述的一个 UI 组件做成 3~5 个方向真不一样的可用版本（换配色换文案不算，必须是布局、密度、性格或交互模型上的不同答案，且每个都能真的点、真的动），全挂在同一个底部切换条上按数字键实时翻看对比；候选全程待在隔离目录碰不到生产代码，选中哪个才写进去（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 手上是一个具体的小东西（toast、价格卡、某个按钮）拿不准该做成什么样，想先并排看几个真不一样的方案再拍板时；只能显式点名，仅限 Web。⚠️ 定稿后它会自删整个原型目录 |
| [redesign-existing-projects](skills/design/redesign-existing-projects/) | 对现有网站/应用做设计审计并升级到高端质感，不破坏功能 | 给已有前端项目做视觉翻新、去 AI 味时 |
| [review-animations](skills/design/review-animations/) | 动画代码严审：十条不可妥协标准（缓动、时长 300ms 内、GPU 属性、可中断性、reduced-motion 等）挑刺式审查，输出 Before/After 表和 Block/Approve 裁决（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 对 CSS transition/keyframes/Framer Motion 等动效代码做高标准 craft review 时。需显式点名（frontmatter 带 `disable-model-invocation`） |
| [stitch-design-taste](skills/design/stitch-design-taste/) | 为 Google Stitch 生成 DESIGN.md 设计规范，强制高级反俗套 UI 风格 | 用 Google Stitch 生成界面前，需要统一设计品味约束时 |

### frontend — 前端工程（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [design-loop](skills/frontend/design-loop/) | ⚙️CC "接力棒"文件驱动的自治循环建站：每轮读任务、生成一页 HTML/Tailwind、集成导航、视觉校验，再写入下一任务直到全站完成（来自 [jezweb/claude-skills](https://github.com/jezweb/claude-skills)） | 需要自动连续生成多页完整网站（"把整站建完"、"design loop"）时 |
| [image-to-code](skills/frontend/image-to-code/) | 图生代码工作流：先自生成分节设计图、深度提取设计系统，再忠实实现前端 | 视觉品质要求高的落地页/官网开发或改版，强制"先出图、再分析、后写码"时 |

### ios — iOS 开发（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [ios-verify-loop](skills/ios/ios-verify-loop/) | iOS 开发-验证闭环：先查工具链反「我本地验不了」→ 按层取证（编译 / 本地同镜像服务 / 模拟器点击驱动 AXe / 手势探针 / 接口正负边界样本 / 只读 SQL 对账）→ 双轨审查兜住自验漏网 → 按规格报证据，含 20+ 条实测踩坑（自写） | 改完 iOS 代码要自己拿到证据再交付、做全 App 逐屏 UI 审计、不想把验证甩给人时 |
| [swiftui-design-principles](skills/ios/swiftui-design-principles/) | SwiftUI/WidgetKit 原生设计规范：间距网格、字体层级、语义色、原生组件（作者 arjitj2，MIT） | 写或改 SwiftUI 视图、iOS 小组件等原生 Apple UI 时 |

### writing — 写作（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [humanizer](skills/writing/humanizer/) | ⚙️CC 基于 Wikipedia「AI 写作特征」指南，检测并改写文本中 30 种 AI 腔模式（clone 自 [blader/humanizer](https://github.com/blader/humanizer)） | 编辑 AI 生成/疑似 AI 腔的文稿，去 AI 味、加人味时 |

### general — 通用（9 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [background-watch](skills/general/background-watch/) | ⚙️CC 让外部长任务跑完主动来找你：谁会自动叫醒你谁不会、按通知次数选形状（一次性用后台 Bash / 每次发生用 Monitor）、**静默≠正常**的中间态哨兵纪律、轮询脚本工程规范（**Claude Code 专属**，自写） | 起了外部系统上的任务、CI、部署、远程队列这类不会主动通知你的长活时 |
| [coding-standards](skills/general/coding-standards/) | 编码与工程标准：不为写而写 / 融入现有代码、结构三清晰（目录/结构/模块）、设计与实现纪律（可读性、错误处理、日志、性能）、留痕文档、依赖选型四看、环境隔离与可回滚，含交付前自检清单（自写） | 写代码、改代码、做架构设计、选第三方库、配环境或准备交付时 |
| [quality-discipline](skills/general/quality-discipline/) | 质量与求真纪律：测试驱动（先写测试看它失败）、机器能查的进 CI 门禁、质量不由写的人自证、对抗审查以收敛为准不设轮数；排查三纪律与「什么算验过了」的证据规格（自写） | 写测试、做代码审查、验证自己的产出、或排查一个问题时 |
| [secrets-hygiene](skills/general/secrets-hygiene/) | 本机凭据治理：按「谁能读到」分层归位（第 0 层根本不存 → keychain → 600+按需加载 → 系统标准位 → 永不全局 export）、登记册要能机器对账、`withkey` 按需加载器；退役前查真正的调用方且不 rm 只隔离；含实测静默陷阱清单（`ssh-keygen -p` 非 TTY 下静默设空口令还照报成功等）。**不带脚本**：给扫描位置表、「只吐键名不吐值」的命令写法与加载器参考实现，让用户写进自己的环境（自写） | 整理/审计本机密钥、判断某 token 还能不能删、给新机器配凭据、或新增一份凭据要决定放哪时 |
| [full-output-enforcement](skills/general/full-output-enforcement/) | 强制输出完整无删节内容：禁止占位符/省略模式，超长时分段续写 | 要求生成完整代码文件、不能出现 `// ...` 等省略时 |
| [multica-collab](skills/general/multica-collab/) | 让任意 coding agent 成为 Multica（AI 原生工作区）的操作台：从零 onboarding、发 issue 派活、观测轨迹、验收打回、死锁救活、团队协作范式，全程 CLI；含把 issue 建成带全属性的工作管理对象（project / 排期 / 正交标签 / stage / PR 关联）与建专职 agent 的配置边界（自写） | 提到 multica、想把任务托管给 agent 做看板化管理、或贴出 multica 实例 URL 时 |
| [multica-read](skills/general/multica-read/) | Multica 持久化记忆的只读读取器：issue 网络、评论结论、agent 轨迹、成本全景，14 个只读子命令（白名单网关 fail-closed），token 高效（自写） | 冷启动 onboarding、取证溯源、按标签/时间/全文检索 workspace 记忆、跨会话增量同步时 |
| [workflow-orchestration](skills/general/workflow-orchestration/) | ⚙️CC 多 agent Workflow 编排打法：何时上（杠杆闸）、选形状（barrier/pipeline/offload）、五种范式（大规模调研/判官团/对抗审查/上下文卸载/大切片流水线）、承重纪律，以及长跑可靠性工程（输出爆量=头号杀手、文件落盘量产、null 兜底、指标由代码算、缓存续跑、放量前资源三件套 gate）（自写） | 面对有份量的多步工程活（设计/大改/调研/审查/迁移/排障），要决定怎么编排多 agent 时；或长跑 workflow 卡住 / 大批失败 / 放量前评估时 |
| [scaffold-init](skills/general/scaffold-init/) | 本脚手架的注入器：预检查环境按需补装，再把 GUIDE.md 与 HABITS.md 挂进当前项目的 CLAUDE.md（自写） | 启动新项目时说"安装 scaffold-init 脚手架"，一次注入永久生效 |

---

## install.manifest 格式

一行一条，空格分隔，`#` 开头是注释：

```
# 插件：plugin <marketplace 来源（github repo 或 URL；官方市场填 -）> <插件@市场>
plugin patrickserrano/skills ios-swift-skills@patrickserrano-skills
plugin twostraws/swiftui-agent-skill swiftui-pro@swiftui-agent-skill
plugin - superpowers@claude-plugins-official

# git 来源 skill（跟踪上游更新、不收编进仓库）：clone <git 地址> <目录名>
# clone https://github.com/someone/some-skill some-skill
```

注意：`@` 后面的**市场名**不等于 marketplace 来源的 repo 名，以该市场 `.claude-plugin/marketplace.json` 里的 `name` 字段为准；不确定就先 `claude plugin marketplace add <来源>` 一次，看输出里的市场名再照抄。

`skills/` 下收编的副本**不需要**写进 manifest——install.sh 自动全部链接。

---

## 维护手册

| 事件 | 动作 |
|---|---|
| 收一个散装 skill | 副本放进 `skills/<领域>/` → README 索引加一行 → GUIDE.md 路由加一条 → plugin.json `skills` 数组加一条 → README 徽章与分组计数同步 → 跑 install.sh → 按下行发版 |
| 装一个新插件 | `catalog/` 建档案 → `install.manifest` 加 `plugin` 行 → README 插件表加一行 →（含 skill 则 GUIDE.md 加路由）→ 跑 install.sh 完成安装 |
| 跟踪上游的 git skill | `install.manifest` 加 `clone` 行（install.sh 负责 clone 和后续 pull） |
| 悟出新的经验习惯 | HABITS.md 加一行并按下行发版（git 侧即刻生效，插件订阅者更新后生效） |
| 自己写新 skill | 从 `templates/skill-template/` 复制起步，写完按"收散装 skill"流程走 |
| 改了 GUIDE/HABITS/skill 正文（发版） | bump `.claude-plugin/` 两个 json 里的 version → commit + push，**其余全自动**：GitHub Actions 会校验清单一致性，并对新版本自动打 `v<版本>` 与 `zephyr-skills--v<版本>` 双 tag、生成 Release。git 用户 pull 即生效；插件订阅者 `claude plugin update` 后生效 |

> 嫌手动登记麻烦？把这些动作丢给项目里的 AI 助手做——它会按[操作手册](#给-ai-助手的操作手册)执行。

---

## Fork 指南与 FAQ

**插件市场模式和 git 模式怎么选？**
只用不改 → 插件市场（两条命令、自动更新、hook 全自动注入）；要改内容、收编自己的 skill → git 模式（符号链接直接改，改完 push 就是发布）。同一台机器**只走一条**。

**不小心两种模式都装了会怎样？**
不会坏，但全都是双份：GUIDE/HABITS 注入两遍（hook 一遍 + CLAUDE.md import 一遍），全部 skill 也双份注册（`zephyr-skills:xxx` 与 `~/.claude/skills/xxx` 各一份），白费上下文还可能造成路由歧义。解法：卸掉一边——插件侧 `claude plugin uninstall zephyr-skills`；git 侧删掉项目 CLAUDE.md 里的 `## Skill 脚手架` 小节、`.claude/` 里的两个链接，以及 `~/.claude/skills` 下指向本仓库的符号链接。

**插件模式怎么拿到更新？**
`claude plugin update zephyr-skills` 一条命令更新到最新（市场清单会定期自动刷新，但插件本体更新以这条命令为准）。git 模式则 `git pull` 即全局生效。

**我想拿去自用，要改哪些地方？**

1. 全局搜索替换四个标识符（比逐处枚举更不容易漏）：`zephyr4123`（GitHub 用户名）、`skills-Scaffolding`（仓库名）、`zephyr-skills`（插件名）、`skills-scaffolding`（市场名）——覆盖 README、`.claude-plugin/` 两个 json、`skills/general/scaffold-init/SKILL.md`
2. `HABITS.md` 全文换成你自己的习惯（这是"主人的偏好"，不是通用最佳实践）
3. `GUIDE.md` 和 `skills/` 按你的库存增删

**为什么全程符号链接而不是复制？**
单一来源。复制意味着每台机器每个项目一份副本，改一处漏 N 处；链接让"仓库即真相"，`git pull` 就是全局更新。

**为什么项目注入要先建 `.claude/` 内的链接，而不是 CLAUDE.md 直接 `@~/...` 引仓库？**
实测 Claude Code 只内联项目内相对路径的 `@import`，项目外路径静默忽略；而相对 import 会跟随符号链接——所以"链接进项目 + 相对引用"是唯一既生效又保住单一来源的写法。

**项目 CLAUDE.md 里的 import 行提交到 git 会影响协作者吗？**
不会。协作者机器上若没有对应链接，import 会被静默跳过，零副作用；若协作者也装了本脚手架，说一句"安装 scaffold-init 脚手架"就补上链接了。`.claude/skills-guide.md`、`.claude/habits.md` 两个链接本身建议 gitignore（是本机绝对路径）。

**这个仓库本身什么许可？**
自有内容（脚本、GUIDE/HABITS、scaffold-init、文档）为 MIT，见根目录 [LICENSE](LICENSE)；`skills/` 下收编的第三方 skill 沿用各自目录内的 LICENSE，与根许可无关。

**收编的第三方 skill 的版权？**
能溯源的都保留了原 LICENSE 并在索引表标注出处（emilkowalski/skills、pbakaus/impeccable、jezweb/claude-skills、blader/humanizer、anthropics/skills、arjitj2）；其余多为社区流传的散装 skill，收集时来源已不可考。若你是某个 skill 的作者：愿意署名请提 issue 补出处，不希望被收录提 issue 即删。

**install.sh 会覆盖我机器上已有的同名 skill 吗？**
不会。已存在的**真实目录**一律跳过（只提示）；只有符号链接会被刷新指向仓库。
