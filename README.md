<div align="center">

# 🧰 Skills Scaffolding

**个人 Agent Skill 脚手架 —— 收编、分发、恢复、注入，一站式**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-21-blue)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin_marketplace-D97706)

*两条命令订阅全套 skill 与协作习惯 —— 或 git clone 完全掌控*

</div>

---

一套可复制的个人 Agent Skill 脚手架。它做四件事：

1. **收编**：把散落各处的 Claude Code skill 收进一个有版本管理的仓库，配上"每个是干啥的"总索引
2. **市场分发**：本仓库自身就是一个 Claude Code 插件市场，`/plugin` 两条命令即可订阅全套（含自动更新）
3. **一键恢复**：git 模式下任何机器一条命令装齐全部 skill 和插件，幂等、只补缺、不重复下载
4. **会话注入**：让每次会话自动知道**什么场景用哪个 skill**（GUIDE.md）和**主人喜欢怎么干活**（HABITS.md）——插件模式由 hook 全自动完成，git 模式对 Claude 说一句"装脚手架"

> 这份 README 同时写给两类读者：**人类**（往下看快速开始）和 **Claude Code**（见[给 Claude Code 的操作手册](#给-claude-code-的操作手册)——如果你是一个正在读这份文档的模型，那一节就是为你写的）。

## 目录

- [快速开始](#快速开始)
- [端到端原理](#端到端原理)
- [给 Claude Code 的操作手册](#给-claude-code-的操作手册)
- [仓库结构](#仓库结构)
- [Skill 总索引](#收编的-skillskills)
- [第三方插件档案](#第三方插件档案catalog)
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

在 Claude Code 里执行两条命令：

```
/plugin marketplace add zephyr4123/skills-Scaffolding
/plugin install zephyr-skills@skills-scaffolding
```

**装完你得到什么：**

- 全部 21 个 skill 立即可用（以 `zephyr-skills:xxx` 命名空间注册，Claude 自动按场景调用）
- **每次会话自动注入** GUIDE（skill 路由）与 HABITS（协作习惯）——插件的 SessionStart hook 完成，零脚本、零配置，连"装脚手架"都不用说
- **更新省心**：仓库发新版后 `claude plugin update zephyr-skills` 一条命令拿到最新（市场清单也会定期自动刷新）

**日常管理：**

```bash
claude plugin disable zephyr-skills --scope project   # 本项目关闭（如工作/公司项目），其他项目不受影响
claude plugin enable zephyr-skills --scope project    # 重新打开
claude plugin update zephyr-skills                    # 更新到最新版本
claude plugin uninstall zephyr-skills                 # 整体卸载
```

**边界说明：**

- catalog 里的三个第三方插件（ios-swift-skills、swiftui-pro、superpowers）**不会**随本插件自动安装——它们在别人的市场上，按各自[档案](#第三方插件档案catalog)里的命令装（共五条命令）
- 插件模式是**只读订阅**：想改 skill 内容，走模式二

### 模式二：git 仓库（推荐给维护者 / 想改 skill 的人）

前提：机器上已装 git 和 [Claude Code](https://claude.com/claude-code)（`claude` 命令可用）。

```bash
git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding
bash ~/coding/personal/skills-scaffolding/scripts/install.sh
```

装完即拥有全套：收编 skill 链接进 `~/.claude/skills`，三方插件自动安装。机器上已有部分 skill 也没关系——脚本幂等，已就位的跳过，只补缺的。若暂时没装 Claude Code，skill 链接部分照常完成，插件部分会提示失败，装好后重跑同一命令即可补齐。

> 克隆到别的路径也行，脚本会从自身位置定位仓库；但默认路径能让 scaffold-init 的自动发现更顺畅。

### 新项目（仅 git 模式；插件模式已由 hook 全自动注入，**不要**再说这句话，会双重注入）

在项目目录里对 Claude Code 说一句：

> **装脚手架**

Claude 会执行 `scaffold-init` skill：先体检环境（缺 skill 就补、全齐就零动作），然后把 GUIDE.md 和 HABITS.md 注入本项目的 CLAUDE.md。从此这个项目的每次会话都自带 skill 路由知识和协作习惯，一次注入永久生效。

> 前提：这台机器跑过一次上面的安装命令（否则 Claude 还不认识"装脚手架"这句话）。

### 日常

- **忘了某个 skill 是干啥的** → 看下面的[总索引](#收编的-skillskills)
- **收了新 skill / 悟了新经验** → 见[维护手册](#维护手册)

---

## 端到端原理

**内容永远只有仓库里一份**，通过两条通道到达用户。

**插件市场通道**（使用者，全自动）：

```
┌─ GitHub 仓库（.claude-plugin/ 声明市场与插件）────────────────┐
│        │  /plugin marketplace add + /plugin install            │
│        ▼                                                       │
│  本机插件缓存（~/.claude/plugins/cache/…，随市场刷新自动更新）  │
│        ├── skills/ × 21 ──────▶ 直接注册进 Claude Code         │
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
               │ scaffold-init skill（说"装脚手架"触发）
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

## 给 Claude Code 的操作手册

如果你是一个 Claude Code 会话，用户让你操作这个脚手架，按下表办事。

**第 0 步，先判定模式**：跑 `claude plugin list`——里面有 `zephyr-skills` 就是**插件模式**，skill 与注入已由插件承载，下表标「仅 git 模式」的行**不要执行**（跑 preflight / install.sh / scaffold-init 会造成双模式共存、双重注入），对应意图直接回答"本机是插件模式，无需此操作"。没有该插件才按 git 模式继续。

git 模式下先定位仓库根（下表 `<仓库>` 的取值，按顺序尝试）：① 默认 `~/coding/personal/skills-scaffolding`；② `readlink ~/.claude/skills/scaffold-init` 反查（链接目标的上三级就是仓库根）；③ 都没有则 `git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding`。

| 用户意图 | 你该做的 |
|---|---|
| "装脚手架" / "注入 skill 指南"（仅 git 模式） | 调用 `scaffold-init` skill；若本机没有该 skill，先按下一行恢复环境，再执行 `<仓库>/skills/general/scaffold-init/SKILL.md` 里的步骤 |
| 恢复/检查环境（仅 git 模式） | 先 `bash <仓库>/scripts/preflight.sh`（只读，退出码 0=完整 1=有缺口）；**仅当有缺口时**才 `bash <仓库>/scripts/install.sh` |
| 收编一个新 skill | 复制 skill 目录进 `skills/<领域>/`（去掉内嵌 `.git`，保留 LICENSE；没有合适领域可新建目录，脚本按 `skills/*/*/` 自动识别），然后：README 索引表加一行**并更新分组标题里的计数**、GUIDE.md 路由加一条、`.claude-plugin/plugin.json` 的 `skills` 数组加一条路径，最后跑一次 install.sh 让链接生效 |
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
catalog/          第三方插件档案：本体由插件市场管理，这里记来源、装法、用途
scaffold/         注入文件：GUIDE.md（场景→skill 路由表）+ HABITS.md（协作习惯与经验，活文档）
.claude-plugin/   marketplace.json + plugin.json：本仓库同时是一个可订阅的插件市场
hooks/            插件模式的 SessionStart hook：自动把 scaffold/ 两个文件注入会话
install.manifest  声明式清单：要装哪些插件、克隆哪些 git 来源 skill
scripts/
  install.sh      一键恢复：链接收编 skill + 装插件 + 克隆 git skill（幂等）
  preflight.sh    只读体检：报告环境缺口，退出码 0=完整 1=有缺
templates/        新写 skill 的起步模板
```

同一份内容、两条分发通道：**插件市场模式**（消费者视图——只读订阅、hook 自动注入、自动更新）和 **git 仓库模式**（维护者视图——符号链接可直接改、scaffold-init 按项目注入）。选一条用即可。

---

## 收编的 Skill（skills/）

### design — 设计品味（15 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [brandkit](skills/design/brandkit/) | 高端品牌套件图像生成：以品牌策略为先，产出 logo 系统、品牌规范板、identity deck 级演示图 | 需要为产品/品牌生成 logo 概念、品牌视觉板、品牌手册风格图像时 |
| [design-taste-frontend](skills/design/design-taste-frontend/) | 反 AI 味前端设计：先推断设计方向和三档参数，再按大量禁令产出不模板化的页面 | 写落地页、作品集、营销站或改版，要避免紫渐变/居中 hero/Inter 等 AI 默认审美时 |
| [design-taste-frontend-v1](skills/design/design-taste-frontend-v1/) | 上面那个的旧版规则集（v1） | 只在需要与 v1 行为完全兼容时用，新项目默认用 v2 |
| [emil-design-eng](skills/design/emil-design-eng/) | Emil Kowalski 的设计工程哲学：动画决策框架（是否动/缓动/时长）、组件手感细节、性能与可访问性规则（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做 Web UI 动画/交互打磨，想让界面细节有高级手感（spring、手势、popover/toast）时 |
| [frontend-design](skills/design/frontend-design/) | 指导生成有独特审美的前端界面代码，强调字体、配色、动效与布局的大胆方向（来自 [anthropics/skills](https://github.com/anthropics/skills)，Apache-2.0） | 构建网页组件/页面/应用，希望视觉精致独特、不落俗套时 |
| [gpt-taste](skills/design/gpt-taste/) | 强制随机化布局、AIDA 结构、宽幅排版、bento 网格与 GSAP 滚动动效 | 生成落地页等 Web UI，想要 Awwwards 级设计感时 |
| [high-end-visual-design](skills/design/high-end-visual-design/) | 按高端设计公司标准做网页视觉：禁廉价默认，规定字体、双层卡片、大留白、弹簧动效 | 生成或美化网页 UI（React/Tailwind/HTML），要高端质感时 |
| [imagegen-frontend-mobile](skills/design/imagegen-frontend-mobile/) | 生成 app 原生感的移动端 UI 概念图（多屏流程、手机 mockup），只出图不写码 | 为 iOS/Android app 生成 onboarding、首页等多屏视觉概念图时 |
| [imagegen-frontend-web](skills/design/imagegen-frontend-web/) | 生成高端网页设计参考图：每个页面 section 出一张横图，反 AI 俗套艺术指导 | 为落地页/营销站生成设计概念图（供照图实现）时 |
| [impeccable](skills/design/impeccable/) | 前端界面设计打磨全能 skill：23 个子命令覆盖构建、评审、精修、动效、配色、排版、live 浏览器实时迭代，内置反 AI 味硬标准与 slop 检测（来自 [pbakaus/impeccable](https://github.com/pbakaus/impeccable)，v3.9.1） | 设计、重构、评审或打磨任何前端 UI，尤其要摆脱"一眼 AI 生成"的平庸感、或做 a11y/性能/响应式审计时 |
| [industrial-brutalist-ui](skills/design/industrial-brutalist-ui/) | 工业粗野主义 UI：瑞士印刷+军用终端美学，硬网格、巨型字体、单一红色点缀、CRT 做旧 | 数据密集仪表盘、作品集、编辑类网页想要机密蓝图/机械终端质感时 |
| [minimalist-ui](skills/design/minimalist-ui/) | 极简编辑风 UI：暖色单色调+衬线大标题+bento 网格+微妙动效，禁渐变重阴影 | 想要 Notion 式高级极简文档风、避免 SaaS 模板感时 |
| [redesign-existing-projects](skills/design/redesign-existing-projects/) | 对现有网站/应用做设计审计并升级到高端质感，不破坏功能 | 给已有前端项目做视觉翻新、去 AI 味时 |
| [review-animations](skills/design/review-animations/) | 动画代码严审：十条不可妥协标准（缓动、时长 300ms 内、GPU 属性、可中断性、reduced-motion 等）挑刺式审查，输出 Before/After 表和 Block/Approve 裁决（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 对 CSS transition/keyframes/Framer Motion 等动效代码做高标准 craft review 时 |
| [stitch-design-taste](skills/design/stitch-design-taste/) | 为 Google Stitch 生成 DESIGN.md 设计规范，强制高级反俗套 UI 风格 | 用 Google Stitch 生成界面前，需要统一设计品味约束时 |

### frontend — 前端工程（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [design-loop](skills/frontend/design-loop/) | "接力棒"文件驱动的自治循环建站：每轮读任务、生成一页 HTML/Tailwind、集成导航、视觉校验，再写入下一任务直到全站完成（来自 [jezweb/claude-skills](https://github.com/jezweb/claude-skills)） | 需要自动连续生成多页完整网站（"把整站建完"、"design loop"）时 |
| [image-to-code](skills/frontend/image-to-code/) | 图生代码工作流：先自生成分节设计图、深度提取设计系统，再忠实实现前端 | 视觉品质要求高的落地页/官网开发或改版，强制"先出图、再分析、后写码"时 |

### ios — iOS 开发（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [swiftui-design-principles](skills/ios/swiftui-design-principles/) | SwiftUI/WidgetKit 原生设计规范：间距网格、字体层级、语义色、原生组件（作者 arjitj2，MIT） | 写或改 SwiftUI 视图、iOS 小组件等原生 Apple UI 时 |

### writing — 写作（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [humanizer](skills/writing/humanizer/) | 基于 Wikipedia「AI 写作特征」指南，检测并改写文本中 30 种 AI 腔模式（clone 自 [blader/humanizer](https://github.com/blader/humanizer)） | 编辑 AI 生成/疑似 AI 腔的文稿，去 AI 味、加人味时 |

### general — 通用（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [full-output-enforcement](skills/general/full-output-enforcement/) | 强制输出完整无删节内容：禁止占位符/省略模式，超长时分段续写 | 要求生成完整代码文件、不能出现 `// ...` 等省略时 |
| [scaffold-init](skills/general/scaffold-init/) | 本脚手架的注入器：预检查环境按需补装，再把 GUIDE.md 与 HABITS.md 挂进当前项目的 CLAUDE.md（自写） | 启动新项目时说"装脚手架"，一次注入永久生效 |

---

## 第三方插件档案（catalog/）

这些插件的本体由 Claude Code 插件市场管理（作者持续更新，仓库不存副本）。git 模式由 `install.sh` 按 `install.manifest` 自动安装；插件模式**不会**自动带装，按下表档案里的命令手动装（共五条命令）：

| 插件 | 一句话 | 档案 |
|---|---|---|
| ios-swift-skills | iOS/macOS 开发全流程技能包：UI 模式、并发、调试、性能剖析、打包发布（10 个 skill） | [catalog/ios-swift-skills.md](catalog/ios-swift-skills.md) |
| swiftui-pro | Paul Hudson 出品的 SwiftUI 专业代码审查（九份参考清单） | [catalog/swiftui-pro.md](catalog/swiftui-pro.md) |
| superpowers | 软件工程流程纪律插件（作者 obra/Jesse Vincent，经 Anthropic 官方市场分发）：脑暴、计划、TDD、调试、评审（14 个 skill） | [catalog/superpowers.md](catalog/superpowers.md) |

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
| 改了 GUIDE/HABITS/skill 正文（发版） | bump `.claude-plugin/` 两个 json 里的 version → commit + push。git 用户 pull 即生效（符号链接）；插件订阅者 `claude plugin update` 后生效 |

> 嫌手动登记麻烦？把这些动作丢给项目里的 Claude 做——它会按[操作手册](#给-claude-code-的操作手册)执行。

---

## Fork 指南与 FAQ

**插件市场模式和 git 模式怎么选？**
只用不改 → 插件市场（两条命令、自动更新、hook 全自动注入）；要改内容、收编自己的 skill → git 模式（符号链接直接改，改完 push 就是发布）。同一台机器**只走一条**。

**不小心两种模式都装了会怎样？**
不会坏，但全都是双份：GUIDE/HABITS 注入两遍（hook 一遍 + CLAUDE.md import 一遍），21 个 skill 也双份注册（`zephyr-skills:xxx` 与 `~/.claude/skills/xxx` 各一份），白费上下文还可能造成路由歧义。解法：卸掉一边——插件侧 `claude plugin uninstall zephyr-skills`；git 侧删掉项目 CLAUDE.md 里的 `## Skill 脚手架` 小节、`.claude/` 里的两个链接，以及 `~/.claude/skills` 下指向本仓库的符号链接。

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
不会。协作者机器上若没有对应链接，import 会被静默跳过，零副作用；若协作者也装了本脚手架，说一句"装脚手架"就补上链接了。`.claude/skills-guide.md`、`.claude/habits.md` 两个链接本身建议 gitignore（是本机绝对路径）。

**这个仓库本身什么许可？**
自有内容（脚本、GUIDE/HABITS、scaffold-init、文档）为 MIT，见根目录 [LICENSE](LICENSE)；`skills/` 下收编的第三方 skill 沿用各自目录内的 LICENSE，与根许可无关。

**收编的第三方 skill 的版权？**
能溯源的都保留了原 LICENSE 并在索引表标注出处（emilkowalski/skills、pbakaus/impeccable、jezweb/claude-skills、blader/humanizer、anthropics/skills、arjitj2）；其余多为社区流传的散装 skill，收集时来源已不可考。若你是某个 skill 的作者：愿意署名请提 issue 补出处，不希望被收录提 issue 即删。

**install.sh 会覆盖我机器上已有的同名 skill 吗？**
不会。已存在的**真实目录**一律跳过（只提示）；只有符号链接会被刷新指向仓库。
