# Skills Scaffolding

个人 Agent Skill 收集仓库：把散落在本机的 skill 收编归档、给第三方插件建档案，目标是——**任何时候打开这个 README，就能一眼看到我有哪些 skill、每个是干啥的、什么时候用**。

## 仓库结构

```
skills/           收编的完整副本（散装、没有版本管理的 skill 的正式的家），按领域分组
catalog/          第三方插件档案（本体由插件市场管理，这里只记来源、装法、用途）
GUIDE.md          面向模型的场景路由指南，供 scaffold-init 注入各项目的 CLAUDE.md
templates/        新写 skill 的起步模板
install.manifest  一键安装清单：声明要装的插件和 git 来源 skill
scripts/          install.sh：一条命令恢复全部（链接收编 skill + 装插件 + 克隆 git skill）
                  preflight.sh：只读预检查，报告环境缺口，全绿则啥也不用装
```

收录规则：自己写的、散装下载的 → 存完整副本进 `skills/`；插件市场管理的 → 只在 `catalog/` 建档。

---

## 收编的 Skill（skills/）

### design — 设计品味（15 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [brandkit](skills/design/brandkit/) | 高端品牌套件图像生成：以品牌策略为先，产出 logo 系统、品牌规范板、identity deck 级演示图 | 需要为产品/品牌生成 logo 概念、品牌视觉板、品牌手册风格图像时 |
| [design-taste-frontend](skills/design/design-taste-frontend/) | 反 AI 味前端设计：先推断设计方向和三档参数，再按大量禁令产出不模板化的页面 | 写落地页、作品集、营销站或改版，要避免紫渐变/居中 hero/Inter 等 AI 默认审美时 |
| [design-taste-frontend-v1](skills/design/design-taste-frontend-v1/) | 上面那个的旧版规则集（v1） | 只在需要与 v1 行为完全兼容时用，新项目默认用 v2 |
| [emil-design-eng](skills/design/emil-design-eng/) | Emil Kowalski 的设计工程哲学：动画决策框架（是否动/缓动/时长）、组件手感细节、性能与可访问性规则（来自 [emilkowalski/skills](https://github.com/emilkowalski/skills)） | 做 Web UI 动画/交互打磨，想让界面细节有高级手感（spring、手势、popover/toast）时 |
| [frontend-design](skills/design/frontend-design/) | 指导生成有独特审美的前端界面代码，强调字体、配色、动效与布局的大胆方向 | 构建网页组件/页面/应用，希望视觉精致独特、不落俗套时 |
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
| [swiftui-design-principles](skills/ios/swiftui-design-principles/) | SwiftUI/WidgetKit 原生设计规范：间距网格、字体层级、语义色、原生组件 | 写或改 SwiftUI 视图、iOS 小组件等原生 Apple UI 时 |

### writing — 写作（1 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [humanizer](skills/writing/humanizer/) | 基于 Wikipedia「AI 写作特征」指南，检测并改写文本中 30 种 AI 腔模式（clone 自 [blader/humanizer](https://github.com/blader/humanizer)） | 编辑 AI 生成/疑似 AI 腔的文稿，去 AI 味、加人味时 |

### general — 通用（2 个）

| Skill | 是干啥的 | 什么时候用 |
|---|---|---|
| [full-output-enforcement](skills/general/full-output-enforcement/) | 强制输出完整无删节内容：禁止占位符/省略模式，超长时分段续写 | 要求生成完整代码文件、不能出现 `// ...` 等省略时 |
| [scaffold-init](skills/general/scaffold-init/) | 把本仓库 GUIDE.md 以 @import 挂进当前项目的 CLAUDE.md，让项目每次会话自带 skill 路由知识（自写） | 启动新项目时说"装脚手架"/"scaffold init"，一次注入永久生效 |

---

## 第三方插件档案（catalog/）

| 插件 | 一句话 | 档案 |
|---|---|---|
| ios-swift-skills | iOS/macOS 开发全流程技能包：UI 模式、并发、调试、性能剖析、打包发布（10 个 skill） | [catalog/ios-swift-skills.md](catalog/ios-swift-skills.md) |
| swiftui-pro | Paul Hudson 出品的 SwiftUI 专业代码审查（九份参考清单） | [catalog/swiftui-pro.md](catalog/swiftui-pro.md) |
| superpowers | Anthropic 官方的软件工程流程纪律插件：脑暴、计划、TDD、调试、评审（14 个 skill） | [catalog/superpowers.md](catalog/superpowers.md) |

---

## 日常用法

- **忘了某个 skill 是干啥的** → 看上面的表
- **启动新项目** → 在项目里对 Claude 说"装脚手架"（scaffold-init 先跑 preflight.sh 预检查：本机环境完整就零安装直接注入；缺啥补啥、绝不重复下载；全新机器会先自动 clone 本仓库。然后把 [GUIDE.md](GUIDE.md) 以 `@import` 注入项目 CLAUDE.md，此后每次会话自动知道什么场景用哪个 skill；GUIDE 更新全项目自动跟进）
- **换新机器 / 重装** → clone 本仓库后跑 `bash scripts/install.sh`，一条命令全部就位：收编 skill 链接进 `~/.claude/skills`、插件自动 `marketplace add` + `install`、git 来源 skill 自动 clone（重复执行安全，已就位的自动跳过）
- **新收一个散装 skill** → 复制进 `skills/<领域>/`，README 表里加一行，`GUIDE.md` 路由里加一条
- **新装一个插件** → `catalog/` 建一个档案，README 表里加一行，`install.manifest` 加一行 `plugin`
- **想跟踪上游更新的 git skill** → 不收编，`install.manifest` 加一行 `clone`，install.sh 会负责 clone 和后续 pull
- **自己写新 skill** → 从 `templates/skill-template/` 复制起步
