<div align="center">

# 🧰 Skills Scaffolding

**个人 Agent 脚手架 —— skill 装在机器上，红线和记忆跟着项目走**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
![Skills](https://img.shields.io/badge/skills-22-blue)
![Claude Code](https://img.shields.io/badge/Claude_Code-supported-D97706)
![Codex](https://img.shields.io/badge/Codex-supported-10A37F)

*Claude Code 与 Codex 双引擎：读同一份红线、写同一个 `.memory/`，各用自己最擅长的方式*

</div>

---

它做三件事：

1. **收编 skill**：散落的 skill 收进一个有版本管理的仓库，链进两个引擎的全局 skill 目录。每台机器装一次，所有项目共用
2. **给项目装红线**：主人的红线、写代码与验证标准、工作习惯，写进项目的 `AGENTS.md`。两个引擎每次会话都整份加载，不可能看漏
3. **给项目装共享记忆**：`.memory/` 随 git 走。Claude Code 把它当作自己的自动记忆读写，Codex 由 hook 注入索引——谁写的另一边都能用

> 这份 README 写给两类读者：**人类**看[快速开始](#快速开始)；**AI 助手**看[给 AI 助手的操作手册](#给-ai-助手的操作手册)。

## 目录

- [快速开始](#快速开始)
- [架构](#架构)
- [同步规则](#同步规则)
- [引擎适配](#引擎适配)
- [给 AI 助手的操作手册](#给-ai-助手的操作手册)
- [仓库结构与测试](#仓库结构与测试)
- [Skill 总索引](#收编的-skillskills)
- [精选第三方插件](#精选第三方插件catalog)
- [MCP 总索引](#收编的-mcpmcp)
- [从 2.x 升级](#从-2x-升级)
- [Fork 指南与 FAQ](#fork-指南与-faq)

---

## 快速开始

前提：git、python3（3.10+，只用标准库），Claude Code 与 Codex 至少装了一个。

### 1. 每台机器一次：装机器层

```bash
git clone https://github.com/zephyr4123/skills-Scaffolding.git ~/coding/personal/skills-scaffolding
python3 ~/coding/personal/skills-scaffolding/scripts/install.py
```

脚本自己探测这台机器装了哪个引擎，只处理存在的：

| 引擎 | 做什么 |
|---|---|
| Claude Code | 适用的 skill 链进 `~/.claude/skills`；装第三方插件；注入 MCP（user scope）。**自带的自动记忆保持开启，不动** |
| Codex | 适用的 skill 链进 `~/.agents/skills`；装第三方插件；`config.toml` 写 `model_context_window = 1000000`、关原生 `memories`；装项目记忆 SessionStart hook；全局 `~/.codex/AGENTS.md` 写入记忆读写规则 |

> ⚠️ **Codex 装完要做一次**：打开 `codex` 输入 `/hooks`，信任 `project_memory.py`。没信任的 hook 不会执行，记忆就注入不了。以后只有 hook 定义变了才需要重新信任。

```bash
python3 scripts/install.py --check       # 只读体检，有缺口退出码 1
python3 scripts/install.py --uninstall   # 撤掉 skill 链接与 Codex 记忆组件（插件、MCP、config 值不动）
```

已存在的同名**真实目录**一律跳过，不接管；仓库里删掉的 skill，留在 skill 根里的失效链接会被清掉。

### 2. 每个项目一次：装项目层

在项目里对 Claude Code 或 Codex 说一句：

> **安装 zephyr-scaffold-init 脚手架**

它会体检本机、预览改动、征得同意后安装，再起新会话验证真的生效。也可以直接跑：

```bash
python3 ~/coding/personal/skills-scaffolding/scripts/init_project.py <项目目录> --check   # 先看会改什么
python3 ~/coding/personal/skills-scaffolding/scripts/init_project.py <项目目录>
```

装完把 `AGENTS.md`、`CLAUDE.md`、`.memory/`、`.gitignore` 的改动提交进 git——这样红线和记忆才跟着项目走。

### 3. 脚手架更新之后

仓库里 `git pull`，重跑 `install.py`（机器层）；然后在各项目里重跑 `init_project.py`（或说"同步脚手架"），规则见[同步规则](#同步规则)。

---

## 架构

| | 机器层（每台机器一次） | 项目层（每个项目一次，跟 git 走） |
|---|---|---|
| **两个引擎共享** | `skills/` 链进各自的 skill 根 | `AGENTS.md` 红线区块、`.memory/` 共享记忆 |
| **Claude Code** | 什么都不加，自带自动记忆照常工作 | `CLAUDE.md` 里一行 `@AGENTS.md`；`.claude/settings.local.json` 的 `autoMemoryDirectory` 指向 `.memory` |
| **Codex** | hook、记忆读写规则、上下文 100 万、关原生 memories | 不用装，hook 自己找到 `.memory/` |

项目层的内容来自 `seed/`：

- `seed/redlines.md` → 项目 `AGENTS.md` 的红线区块：🔴 9 条红线 + 写代码标准 + 验证与排查纪律 + 工作方式（Git、Issue、搜索、决策、立规矩、汇报）
- `seed/memory/` → 项目 `.memory/`：skill 库总览、前端 / iOS / 通用 skill 路由、MCP 工具

### 为什么这样分

- **skill 是工具，留在机器上**：项目里不建 skill 目录，所有项目共用全局那一份。记忆和红线是知识，才跟项目走
- **红线进入口文件，不进记忆**：记忆加载时只露出索引里的一行摘要，正文要模型自己去读——红线藏在记忆里，哪次忘了翻就等于失效。入口文件每次整份加载，看不见是不可能的
- **红线只有一份**：写在 `AGENTS.md`，Claude 侧由 `CLAUDE.md` 里的 `@AGENTS.md` 引入（项目同时有这两个文件时，Claude 默认只读 `CLAUDE.md`）。路径在项目内，过得了 Claude Code 的外部引用闸。不写两份，免得改一边忘一边
- **记忆共享，管法不同**：Claude Code 本身很会写记忆，不给它加规则，只把自动记忆目录指向 `.memory/`。Codex 原生记忆不分项目、整份注入，所以关掉，改由 hook 注入本项目索引，再用全局 `AGENTS.md` 里的读写规则教它怎么写。记忆格式统一以 Claude Code 为准
- **Codex 的读写规则放机器层**：它是对 Codex 的适配，不是项目知识；放进项目 `AGENTS.md` 的话，Claude 读到也会被它框住
- **`autoMemoryDirectory` 写进 `settings.local.json`**：这个设置只接受绝对路径，进 git 就会在别的机器上指错地方，所以每台机器各写一次，并由 `.gitignore` 挡住

## 同步规则

脚手架写进项目的东西都记了内容指纹：记忆记在 frontmatter 的 `metadata.scaffold_sha`，红线记在区块开头的注释里。重跑 `init_project.py` 时：

| 情况 | 处理 |
|---|---|
| 项目没改过 | 跟着脚手架更新到新版 |
| 项目改过（人改的或 Claude 自己改的） | 跳过，在输出里列出，由你决定要不要手动合并 |
| 脚手架撤掉了某条种子记忆 | 项目没改过就一并撤掉，改过就保留 |
| Claude 只改了 metadata（如 `modified` 时间戳） | 不算改过 |

所以项目特有的调整可以直接改项目里的红线区块或记忆，之后同步会自动跳过它们。

---

## 引擎适配

### 哪 5 个 skill 在 Codex 上跑不了

每个 skill 的 frontmatter 都有 `engines:` 字段（CI 校验），索引和路由记忆里标 **⚙️CC**：

| Skill | 原因 |
|---|---|
| `zephyr-workflow-orchestration` | 整篇建立在 Claude Code 的 Workflow 工具上（`parallel`/`pipeline`、`effort`、缓存前缀链、journal 字段），换引擎需重写而非改措辞 |
| `zephyr-background-watch` | 依赖 `Monitor` 与后台任务两个 harness 能力 |
| `impeccable` | 正文 37 处硬编码 `node .claude/skills/impeccable/scripts/…`，装到 Codex 的 `.agents/skills` 下第一步就 ENOENT。**上游本体其实支持 Codex**，靠它自己的安装器改写路径，而本仓只收了裸副本——这是打包缺陷不是方法论缺陷 |
| `design-loop` | 上游作者自己在 frontmatter 声明 `compatibility: claude-code-only`，尊重上游不擅自扩大 |
| `humanizer` | 上游声明支持 Claude Code 与 OpenCode，未提 Codex，同样不替它扩大 |

判定标准是**「内容在另一个引擎上能不能真正执行」**，不是话题相不相关。拿不准一律判窄——标窄了只少推荐一次，标宽了会让人踩空。


### Codex 的几个必知差异（codex-cli 0.162.1 实测）

- **原生 memories 为什么关**：`~/.codex/memories/memory_summary.md` 整份注入每个会话，不分项目（公司项目、私人数据、别的仓库混在一起）；内容是「任务组 → 会话摘要」的流水账，到处是绝对路径；由后台两阶段批处理生成，官方原话 "Treat these files as generated state"，人和 agent 都不能当场写
- **hook 要信任一次**：见[快速开始](#1-每台机器一次装机器层)。没信任时 hook 静默不执行
- **`.agents/` 在沙盒里只读**：workspace-write 沙盒把 `.git`、`.agents`、`.codex` 设为只读，实测 `mkdir .agents` 返回 `Operation not permitted`——所以记忆目录叫 `.memory/` 而不是 `.agents/memory/`
- **AGENTS.md 不支持引入其他文件**：`@path` 语法不存在，`project_doc_fallback_filenames` 只接受文件名不接受路径。SessionStart hook 的 `additionalContext` 是唯一能把文件内容确定性放进上下文的官方通道
- **上下文窗口**：配置写 100 万，实际生效 = min(配置, 模型上限) × 95%。gpt-6-astra 的上限是 87.2 万，实测会话里生效的是 828,400

---

## 给 AI 助手的操作手册

如果你是一个 Claude Code 或 Codex 会话，用户让你操作这个脚手架，按下表办事。仓库默认在 `~/coding/personal/skills-scaffolding`，不在就 `readlink ~/.claude/skills/zephyr-scaffold-init`（或 `~/.agents/skills/…`）上溯三级。

| 用户意图 | 你该做的 |
|---|---|
| "安装 zephyr-scaffold-init 脚手架" / "同步脚手架" | 调用 `zephyr-scaffold-init` skill；本机没有这个 skill 就先跑下一行恢复环境 |
| 恢复 / 检查本机环境 | `python3 <仓库>/scripts/install.py --check`（只读）；**有缺口时**才跑 `python3 <仓库>/scripts/install.py` |
| 收编一个新 skill | 复制进 `skills/<领域>/`（去掉内嵌 `.git`，保留 LICENSE）→ frontmatter 加 `engines:`（依赖某引擎专有能力或写死 `.claude/` 路径的只写那一个，CI 校验）→ README 索引加一行并更新分组计数与徽章 → `seed/memory/` 里对应的路由记忆加一条（仅 Claude 可用的标 ⚙️CC）→ 跑 `install.py` |
| 新增一个第三方插件 | `catalog/` 建档案 → `install.manifest` 加 `plugin` 行 → README 插件表加一行 → 插件含 skill 则路由记忆加一条 → 跑 `install.py` |
| 收编一个新 MCP | `mcp/registry.json` 加条目（家目录写 `${HOME}`，凭据只记 `env_required` 键名）→ `catalog/mcp-<name>.md` 档案 → README MCP 表 + `seed/memory/mcp-tools.md` 各加一条 → 跑 `install.py` |
| 改红线或工作习惯 | 改 `seed/redlines.md` → 发版 → 各项目重跑 `init_project.py` 同步 |
| 改 Codex 的记忆读写规则 | 改 `engines/codex/memory-rules.md` → 重跑 `install.py` |
| 更新脚手架 | 仓库 `git pull` → 重跑 `install.py` → 各项目重跑 `init_project.py` |

硬性规则：

- 本仓库的 commit 信息用中文、**绝不带任何 AI 署名**（红线第 1 条）
- 要改全局的红线就改 `seed/redlines.md` 再同步，不要逐个项目手改；某个项目特有的调整才直接改那个项目的区块
- 装完必须验证：起新会话、禁用文件工具，让它背出红线和记忆索引（命令见 `zephyr-scaffold-init` 第 4 步）。文件在、链接对，都证明不了内容进了上下文

---

## 仓库结构与测试

```
skills/             收编的 skill，按领域分组；frontmatter 的 engines: 决定链进哪个引擎
seed/               项目层种子：redlines.md（红线区块）+ memory/（种子记忆，Claude 记忆格式）
engines/codex/      Codex 适配：project_memory.py（SessionStart hook）+ memory-rules.md（读写规则）
scripts/
  install.py        机器层：安装 / 体检（--check）/ 卸载（--uninstall）
  init_project.py   项目层：安装与同步（--check 只预览）
  common.py         两者共用：frontmatter、内容指纹、受管区块
tests/              单测 + 仓库门禁（CI 跑）；e2e/ 是用真实 claude / codex 跑的端到端验证
catalog/            第三方插件与 MCP 档案：本体由上游管理，这里记来源、装法、用途、坑
mcp/registry.json   MCP 登记册（单一来源，凭据只记键名）
install.manifest    第三方插件清单
templates/          新写 skill 的起步模板（已含 engines: 字段）
VERSION             版本号；main 上出现新值即自动打 tag 发 Release
```

```bash
python3 -m unittest discover -s tests          # 单测 + 仓库门禁，CI 同款
python3 tests/e2e/run_e2e.py --engine codex    # 真实 codex：注入、读、写、隔离
python3 tests/e2e/run_e2e.py --engine claude   # 真实 claude：红线可见、记忆写进 .memory
```

仓库门禁（`tests/test_repo.py`）会检查：每个 skill 有合法的 `engines:`、种子记忆格式合规且与索引一一对应、红线不超过 200 行、全仓不再出现已退役的文件名。

---

## 收编的 Skill（skills/）

> 标 **⚙️CC** 的只能在 Claude Code 上跑（原因见[引擎适配](#引擎适配)），其余两个引擎通用。**命名约定：`zephyr-` 前缀 = 自写，无前缀 = 外部收编（保留上游原名）。**权威判据是每个 skill frontmatter 里的 `engines:` 字段，CI 会校验。

### design — 设计品味（10 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [animation-vocabulary](skills/design/animation-vocabulary/) | 动效术语反查词典：Web 动画术语按 12 类整理，从「看着像什么、感觉像什么」倒查出准确叫法，一次给首选词加 1~2 个近义词并说清差别；词表里没有就直说没有，不许现编（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 效果描述得出来但叫不出名字，需要一个准确的词去跟设计师沟通、写进需求、或喂给 AI 当 prompt 时。⚠️ 词表漏了 scroll snap / FLIP / scrub，它会答「没有」而不是猜 |
| [apple-design](skills/design/apple-design/) | 把 Apple 的流体界面做法翻译成网页实现：手指 1:1 跟随、动画随时能抓住反向、松手把速度交给弹簧、用减速公式算落点再吸附、边界橡皮筋；另含半透明材质分层、随字号变的字距行高、reduced-motion/transparency/contrast 三档降级。给的是能直接抄的公式和数值（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做手势驱动的网页交互——拖拽、滑动关闭、bottom sheet、可打断的转场、弹簧调参时；写原生 SwiftUI 走 swiftui-design-principles。⚠️ 文中「~300ms tap delay」是十年前的知识，现代浏览器早已移除，别去项目里找它 |
| [emil-design-eng](skills/design/emil-design-eng/) | Emil Kowalski 的设计工程哲学：动画决策框架（是否动/缓动/时长）、组件手感细节、性能与可访问性规则（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做 Web UI 动画/交互打磨，想让界面细节有高级手感（spring、手势、popover/toast）时 |
| [find-animation-opportunities](skills/design/find-animation-opportunities/) | 扫代码库找「该动却没动」的地方：四道闸逐条筛（一天会被看见多少次 / 动机能不能被命名 / 300ms 内做不做得完 / 会不会妨碍读数据），键盘触发和高频操作一律否决，最后只留 5~7 条，每条带 file:line 和确切的曲线、时长、属性，还强制列出「考虑过但否掉了」的名单。只读不改代码（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 觉得 Web 界面太死板、想先拿一张有优先级的动效待办清单，或想搞清楚哪些地方其实**不该**加动画时；审已有动效代码走 review-animations，原生 iOS 别用 |
| [frontend-design](skills/design/frontend-design/) | 指导生成有独特审美的前端界面：先弄清题材再设计，两遍工作法（先写设计计划、对照 brief 复核、像通用默认就重来），列出 AI 生成设计的五种典型脸让你避开，文案也当设计写（来自 [anthropics/skills](https://github.com/anthropics/skills) 2026-09-03 版，Apache-2.0） | 构建网页组件/页面/应用，希望视觉精致独特、不落俗套时 |
| [impeccable](skills/design/impeccable/) | ⚙️CC 前端界面设计打磨全能 skill：23 个子命令覆盖构建、评审、精修、动效、配色、排版、live 浏览器实时迭代，内置反 AI 味硬标准与 slop 检测（来自 [pbakaus/impeccable](https://github.com/pbakaus/impeccable)，v3.9.1） | 设计、重构、评审或打磨任何前端 UI，尤其要摆脱"一眼 AI 生成"的平庸感、或做 a11y/性能/响应式审计时 |
| [improve-animations](skills/design/improve-animations/) | 整个仓库动效代码的只读审计器：按八类逐条挑问题并回原位复核，排成优先级表让你挑，再把选中的各写成一份计划文件——精确到文件行号、目标 cubic-bezier、时长、验收怎么看，交给别的 agent（哪怕便宜模型）照着改；自己一行源码都不动（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 接手一个 Web 项目觉得「动起来不对劲」、想系统过一遍并排出先改哪个时；或想把判断和改代码拆开。只审一个 diff 用 review-animations。⚠️ 它会在仓库根建 `plans/` 写文件，有推送闸门的项目先决定这目录进不进版本控制 |
| [pick-ui-library](skills/design/pick-ui-library/) | 19 条「前端任务 → 用哪个库」的钦定对照表（toast 用 Sonner、拖拽用 dnd kit、长列表用 Virtuoso、状态用 zustand…），只给一个答案不列菜单，另附 6 条「你正在手搓一个已有库解决的问题」自查；仅覆盖 React Web（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 在 React 前端项目里要新引入一个 UI 依赖、懒得自己比选时。需显式点名。⚠️ 表里只给官网不给包名，两处会装错：Base UI 的包是 `@base-ui-components/react`（裸 `base-ui` 是停更的无关包）、Virtuoso 是 `react-virtuoso` |
| [prototype](skills/design/prototype/) | 把你描述的一个 UI 组件做成 3~5 个方向真不一样的可用版本（换配色换文案不算，必须是布局、密度、性格或交互模型上的不同答案，且每个都能真的点、真的动），全挂在同一个底部切换条上按数字键实时翻看对比；候选全程待在隔离目录碰不到生产代码，选中哪个才写进去（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 手上是一个具体的小东西（toast、价格卡、某个按钮）拿不准该做成什么样，想先并排看几个真不一样的方案再拍板时；只能显式点名，仅限 Web。⚠️ 定稿后它会自删整个原型目录 |
| [review-animations](skills/design/review-animations/) | 动画代码严审：十条不可妥协标准（缓动、时长 300ms 内、GPU 属性、可中断性、reduced-motion 等）挑刺式审查，输出 Before/After 表和 Block/Approve 裁决（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 对 CSS transition/keyframes/Framer Motion 等动效代码做高标准 craft review 时。需显式点名（frontmatter 带 `disable-model-invocation`） |

### frontend — 前端工程（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [design-loop](skills/frontend/design-loop/) | ⚙️CC "接力棒"文件驱动的自治循环建站：每轮读任务、生成一页 HTML/Tailwind、集成导航、视觉校验，再写入下一任务直到全站完成（来自 [jezweb/claude-skills](https://github.com/jezweb/claude-skills)） | 需要自动连续生成多页完整网站（"把整站建完"、"design loop"）时 |

### ios — iOS 开发（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [zephyr-ios-verify-loop](skills/ios/zephyr-ios-verify-loop/) | iOS 开发-验证闭环：先查工具链反「我本地验不了」→ 按层取证（编译 / 本地同镜像服务 / 模拟器点击驱动 AXe / 手势探针 / 接口正负边界样本 / 只读 SQL 对账）→ 双轨审查兜住自验漏网 → 按规格报证据，含 20+ 条实测踩坑（自写） | 改完 iOS 代码要自己拿到证据再交付、做全 App 逐屏 UI 审计、不想把验证甩给人时 |
| [swiftui-design-principles](skills/ios/swiftui-design-principles/) | SwiftUI/WidgetKit 原生设计规范：间距网格、字体层级、语义色、原生组件（作者 arjitj2，MIT） | 写或改 SwiftUI 视图、iOS 小组件等原生 Apple UI 时 |

### writing — 写作（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [humanizer](skills/writing/humanizer/) | ⚙️CC 基于 Wikipedia「AI 写作特征」指南，检测并改写文本中 30 种 AI 腔模式（clone 自 [blader/humanizer](https://github.com/blader/humanizer)） | 编辑 AI 生成/疑似 AI 腔的文稿，去 AI 味、加人味时 |

### general — 通用（8 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [zephyr-background-watch](skills/general/zephyr-background-watch/) | ⚙️CC 让外部长任务跑完主动来找你：谁会自动叫醒你谁不会、按通知次数选形状（一次性用后台 Bash / 每次发生用 Monitor）、**静默≠正常**的中间态哨兵纪律、轮询脚本工程规范（**Claude Code 专属**，自写） | 起了外部系统上的任务、CI、部署、远程队列这类不会主动通知你的长活时 |
| [zephyr-secrets-hygiene](skills/general/zephyr-secrets-hygiene/) | 本机凭据治理：按「谁能读到」分层归位（第 0 层根本不存 → keychain → 600+按需加载 → 系统标准位 → 永不全局 export）、登记册要能机器对账、`withkey` 按需加载器；退役前查真正的调用方且不 rm 只隔离；含实测静默陷阱清单（`ssh-keygen -p` 非 TTY 下静默设空口令还照报成功等）。**不带脚本**：给扫描位置表、「只吐键名不吐值」的命令写法与加载器参考实现，让用户写进自己的环境（自写） | 整理/审计本机密钥、判断某 token 还能不能删、给新机器配凭据、或新增一份凭据要决定放哪时 |
| [zephyr-nested-git](skills/general/zephyr-nested-git/) | 「外层协作仓 + 多个独立业务代码仓」的 nested-git 指针拓扑：外层零业务代码，只存指针 manifest（url/path/prod_branch）与协作产物，代码仓独立 clone 嵌在外层被 .gitignore 挡住、各推各的远端；指针是仓库级不是提交级，用版本关联精度换两层平台/凭据/CI 的彻底解耦。含单文件参考 CLI（红线在代码里：pull 只 ff-only、push 永不 force、fetch 失败不吞、prod_branch 漂移告警）+ 空壳 MR 四道校验 + 运维台通用纪律（dry-run 默认、写操作拒绝 all、凭据不进 argv）（自写） | 新项目要定多仓关联方式（submodule/subtree/合仓/nested 选哪个）、初始化或承接 nested 拓扑项目、给外层仓写跨仓 git 运维 CLI 时 |
| [zephyr-cloud-cli-ops](skills/general/zephyr-cloud-cli-ops/) | CLI-first 云运维分工协议：控制台是人的界面、API 才是 agent 的界面——人只做付钱 / 开通 / 发密钥三类控制台专属动作，其余（建桶/传件/证书/加速域名/DNS/防盗链/预热/验证）全由 agent 用 CLI+SDK 完成。含开工四步协议（凭据归位→只读验活→摸底→动手）、COS+CDN 静态资产十步全链蓝图（每步带完成判据，附 faststart / 防盗链白名单 / 证书续期台账等配套纪律）、实测陷阱清单（边缘证书铺设窗口期、`--resolve` 指定节点是错误测法、本机 VPN 隧道废掉测速）。方法论跨云，worked example 腾讯云。**不带脚本**（自写） | 要配对象存储 / CDN / 证书 / DNS、静态资产迁上云分发、新云账号想让 agent 接管运维、或线上 CDN 慢 / 握手失败 / 测速反复要排查时 |
| [zephyr-multica-collab](skills/general/zephyr-multica-collab/) | 让任意 coding agent 成为 Multica（AI 原生工作区）的操作台：从零 onboarding、发 issue 派活、观测轨迹、验收打回、死锁救活、团队协作范式，全程 CLI；含把 issue 建成带全属性的工作管理对象（project / 排期 / 正交标签 / stage / PR 关联）与建专职 agent 的配置边界（自写） | 提到 multica、想把任务托管给 agent 做看板化管理、或贴出 multica 实例 URL 时 |
| [zephyr-multica-read](skills/general/zephyr-multica-read/) | Multica 持久化记忆的只读读取器：issue 网络、评论结论、agent 轨迹、成本全景，14 个只读子命令（白名单网关 fail-closed），token 高效（自写） | 冷启动 onboarding、取证溯源、按标签/时间/全文检索 workspace 记忆、跨会话增量同步时 |
| [zephyr-workflow-orchestration](skills/general/zephyr-workflow-orchestration/) | ⚙️CC 多 agent Workflow 编排打法：何时上（杠杆闸）、选形状（barrier/pipeline/offload）、五种范式（大规模调研/判官团/对抗审查/上下文卸载/大切片流水线）、承重纪律，以及长跑可靠性工程（输出爆量=头号杀手、文件落盘量产、null 兜底、指标由代码算、缓存续跑、放量前资源三件套 gate）（自写） | 面对有份量的多步工程活（设计/大改/调研/审查/迁移/排障），要决定怎么编排多 agent 时；或长跑 workflow 卡住 / 大批失败 / 放量前评估时 |
| [zephyr-scaffold-init](skills/general/zephyr-scaffold-init/) | 本脚手架的项目层安装器：体检本机按需补装，再给项目装上 `AGENTS.md` 红线区块与 `.memory/` 共享记忆，Claude 侧把自动记忆目录指向 `.memory`；重跑即同步脚手架新版（自写） | 新项目启动、或脚手架更新后同步时说"安装 zephyr-scaffold-init 脚手架" |

---

## 精选第三方插件（catalog/）

这套脚手架的另一半价值：不只收编 skill，还替你**把第三方插件的坑踩完了**——每个都在真实项目里用过、建了档案（来源、装法、每个 skill 是干啥的），试错成本已经付过。

**Claude Code**（会话内斜杠命令，或终端里用等价的 CLI 写法）：

```bash
# 终端 CLI 写法（headless / 脚本化 / agent 操作用这套）
claude plugin marketplace add twostraws/swiftui-agent-skill
claude plugin install swiftui-pro@swiftui-agent-skill
```

会话内则是同名的斜杠形式：`/plugin marketplace add …`、`/plugin install …`。

**Codex**：

```bash
codex plugin marketplace add https://github.com/twostraws/swiftui-agent-skill
codex plugin add swiftui-pro@swiftui-agent-skill
```

或者直接跑 `python3 scripts/install.py`，它按 `install.manifest` 给每个引擎装它装得上的那些。

| 插件 | 为什么值得装 | 引擎 | 档案 |
|---|---|---|---|
| **swiftui-pro** | Paul Hudson（Hacking with Swift 作者）出品，按九份参考清单系统审查 SwiftUI 代码的现代 API、数据流与性能 | 两个都行 | [查看](catalog/swiftui-pro.md) |
| ~~**ios-swift-skills**~~ | iOS 开发一包全覆盖（10 个 skill）。**⚠️ 当前装不上**，见下方说明 | 暂不可用 | [查看](catalog/ios-swift-skills.md) |

> ⚠️ **`ios-swift-skills` 当前对所有新用户不可用**（v1.7.x 实测）：上游 `patrickserrano/skills` 的 `.claude-plugin/` 下只有 `plugin.json`，**没有 `marketplace.json`**，两个引擎 add 都会失败。报错文案是「Marketplace file not found at 〈本地缓存路径〉」——**指向本地路径，极易误判成自己环境坏了**，根因其实在上游仓库结构。已从 `install.manifest` 注释掉；上游补上清单后取消注释即可恢复。

插件本体由各自作者维护更新，本仓库只存档案不存副本；`install.py` 按 `install.manifest` 自动安装，也可以敲上面的命令手动装。

---

## 收编的 MCP（mcp/）

> **裁决（2026-08-25）：MCP 暂只做 Claude Code 侧**（注入 user scope），Codex 侧暂不管——这是范围裁决不是能力结论，registry 的 `engines` 字段已为将来扩 Codex 留位。

机制与 skill 收编同构，但收编单位不同——**MCP 收编的是「配置 + 档案」，不是内容副本**（server 本体活在 npm / 上游服务里）：

- **单一来源**：手改的只有 `mcp/registry.json`（配置模板 + `env_required` 凭据键名）；`scripts/install.py` 据此 `claude mcp add-json --scope user` 幂等注入（已配置的跳过、不覆盖），`install.py --check` 只读对账
- **凭据红线**：registry 只登记键名，**值永不入库**；`install.py` 仅在当前环境能解析出全部键时才注入（fail-closed），缺则跳过并提示——取值方式见 zephyr-secrets-hygiene
- **少而精纪律**：MCP 的 tool 定义常驻吃上下文，user 档只放高频通用的；重的 / 项目特定的以后走 project 档

| MCP | 是干啥的 | 凭据 | 档案 |
|---|---|---|---|
| **playwright** | 浏览器自动化（微软官方）：导航/点击/快照/截图/网络观测，UI 闭环校验锚点 | 无 | [查看](catalog/mcp-playwright.md) |
| **iconify** | 跨图标集语义搜索 + 取 SVG（200+ 图标集），别让模型手绘图标 | 无 | [查看](catalog/mcp-iconify.md) |
| **stock-images** | 免版权配图三源聚合（Pexels/Unsplash/Pixabay）检索下载 | 3 把 API key（只记键名） | [查看](catalog/mcp-stock-images.md) |
| **motionsites** | 网页设计 prompt 库（http 型）：免费额度 3 条，premium 需订阅 | 无（额度服务端管） | [查看](catalog/mcp-motionsites.md) |

---

## install.manifest 格式

一行一条，空格分隔，`#` 开头是注释：

```
# plugin <市场来源（github repo 或 URL；引擎内建的市场填 -）> <插件@市场> [适用引擎，逗号分隔，省略=两个都装]
plugin twostraws/swiftui-agent-skill swiftui-pro@swiftui-agent-skill claude-code,codex
```

`@` 后面的**市场名**不等于来源 repo 名，以该市场 `marketplace.json` 里的 `name` 字段为准。`skills/` 下收编的副本**不需要**写进 manifest，`install.py` 自动全部链接。

---

## 从 2.x 升级

3.0.0 是一次彻底重构：

- **插件市场模式已移除，只保留 git 模式。** 订阅过插件的先卸掉（`claude plugin uninstall zephyr-skills`，Codex 侧同理），再按[快速开始](#快速开始)装
- **GUIDE / HABITS 注入改成了红线区块 + 共享记忆。** 老项目里那两个指向脚手架的符号链接（`CLAUDE.local.md`、`AGENTS.md`）会在重跑 `init_project.py` 时自动清掉，换成新结构；`.gitignore` 里的 `AGENTS.md` 一行也会去掉，因为红线现在要提交进 git
- **写代码标准与质量纪律两个 skill 已并入红线**，不再作为 skill 存在；`install.py` 会清掉指向它们的失效链接
- **安装脚本换成 Python**（`install.py` / `init_project.py`），体检用 `install.py --check`

---

## Fork 指南与 FAQ

**我想拿去自用，要改哪些地方？**

1. 全局搜索替换 `zephyr4123`（GitHub 用户名）和 `skills-Scaffolding`（仓库名）
2. `seed/redlines.md` 全文换成你自己的红线和习惯——这是"主人的偏好"，不是通用最佳实践
3. `skills/` 和 `seed/memory/` 里的路由记忆按你的库存增删

**为什么全程符号链接而不是复制 skill？**
单一来源。skill 是工具，`git pull` 就是全机器更新。红线和记忆则相反：它们要跟着项目走、允许按项目定制，所以是复制进项目，再靠[同步规则](#同步规则)跟上游保持一致。

**公司项目也装吗？`.memory/` 会进公司仓库吗？**
会。红线和记忆跟项目走，个人项目、公司项目一视同仁；只有 `settings.local.json`（本机绝对路径）不进 git。

**这个仓库本身什么许可？**
自有内容（脚本、红线与种子记忆、zephyr- 前缀的 skill、文档）为 MIT，见 [LICENSE](LICENSE)；`skills/` 下收编的第三方 skill 沿用各自目录内的 LICENSE。

**收编的第三方 skill 的版权？**
都保留了原 LICENSE 并在索引表标注出处（emilkowalski/skills、pbakaus/impeccable、jezweb/claude-skills、blader/humanizer、anthropics/skills、arjitj2）。若你是某个 skill 的作者：愿意署名请提 issue 补出处，不希望被收录提 issue 即删。
