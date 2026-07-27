---
name: ios-verify-loop
description: Use when 在 iOS 项目里改完代码要**自己拿到证据**再交付时——教一套开发-验证闭环:先查工具链(反"我本地验不了")→ 按层取证(编译 / 本地同镜像服务 / 模拟器点击驱动 AXe / 手势探针 / 接口正负边界样本 / 只读 SQL 对账)→ 用双轨审查兜住自验漏网 → 按规格报证据。含 20+ 条实测踩坑(截图反推坐标点不中、simctl defaults 读错域、首启弹窗覆盖装清不掉…)。不适用于非 iOS 项目、或纯文档改动。
---

# ios-verify-loop:iOS 开发-验证闭环(自己取证,别把验证甩给人)

> **心法:UI 上的每一次点击,都要能在数据库里找到那一行。**
> 开发与验证之间没有「等环境 / 等联调 / 等别人」的断点 —— 每一步都在分钟级拿到生产级证据。
>
> **铁律:「我本地验不了」这句话,说出口之前必须先花一条命令查一遍。** 绝大多数「验不了」是没查,不是真没有。

## Step 0 · 先查再说(反「我验不了」)

这是全 skill 的前置,也是最常被跳过的一步。**未经核查就声称能力边界 = 把验证成本转嫁给人**,对方要一趟趟真机出图,而那些缺陷本可以在本地几分钟内暴露。

动手前逐条查,查完确实没有再说没有,并说清缺什么:

| 要验的东西 | 一条命令查它在不在 |
|---|---|
| iOS 能不能编译 | `which xcodebuild && xcodebuild -version` |
| 有没有模拟器 | `xcrun simctl list devices available`(带过滤的版本见下方) |
| 后端/引擎能不能本地跑 | `docker info` + 项目自有运维 CLI 的 `build`/`run` 子命令 |
| API key / 密钥在不在 | `ls <本机密钥目录>/`(项目约定位置,如 `~/.config/<toolchain>/secrets`;也可能在 keychain 或密码管理器 CLI 里)—— **别只在 repo 里 grep `.env`** |
| 密钥怎么注入 | 直接读运维脚本里的注入逻辑(见下方) |
| 能不能查库 | 运维 CLI 的 `db` 子命令(只读) |
| 测试怎么跑 | `ls` 找 `.venv` / `Makefile` / `pytest.ini` / `*Tests.swift` |

带管道的两条单独列在这里 —— **表格单元格里的 `|` 必须转义,转义后照抄就跑不通**(照抄跑空反而会坐实"本地没有"这个错误结论):

```bash
xcrun simctl list devices available | rg -i "iphone|ipad"   # 有没有模拟器
rg -n "API_KEY|secrets" ops                                 # 密钥怎么注入(读运维脚本)
```

**反例(真实,代价由人类同事承担)**:agent 连着几轮声称「本地编译不了 iOS,只能靠你 build」,实际 Xcode 装着、模拟器还开着一台;又声称「本地没有 API key」,实际 key 就在本机约定的密钥目录里、运维脚本里写明了注入路径。三轮布局缺陷因此靠人肉真机出图才暴露,本可以自己编译发现大半。

## Step 1 · 按层取证(从便宜到贵,能在低层暴露的别拖到高层)

### 层 1 · 编译层 —— 最便宜,改完就跑

```bash
xcodebuild -workspace <App>.xcworkspace -scheme <Scheme> \
  -destination 'platform=iOS Simulator,name=iPhone 17 Pro' \
  -configuration Debug build 2>&1 | rg "error:|BUILD SUCCEEDED|BUILD FAILED"
```

**判定**:`BUILD SUCCEEDED` 且 error 行为空。
**边界(重要)**:编译只证明**语法与签名对**,对状态机竞态、转场时序、布局溢出**完全无感** —— 别拿 BUILD SUCCEEDED 当"没问题"。这类缺陷归 Step 2 的审查双轨。

### 层 2 · 本地同镜像服务 —— 依赖服务别去戳远程

服务端若无 stage、或本地开发不该碰生产,用**同一个 Dockerfile 本地起**:挂载仓内索引/数据短路 S3,从本地密钥文件注入 key,跑在本地端口。

```bash
docker run -d --name <svc>-test -p 8090:8080 \
  -e "API_KEY=$(rg '^API_KEY=' <secrets-dir>/<svc>.env | cut -d= -f2-)" \
  -v "$PWD/<index-dir>:/app/<index-dir>:ro" <image>
# 测完务必 docker rm -f
```

**LLM prompt 类改动尤其必须走这层**:prompt 是纯字符串,单测覆盖不到,**只能打真实请求取证**。见层 4。

### 层 3 · 交互层 —— 模拟器点击驱动(AXe)

手不碰鼠标走完整用户链路。工具 = `axe` CLI + `xcrun simctl`。

**核心口径(三条,全部实测踩出来)**:
- **坐标唯一真相源 = `describe-ui` 取 AX frame 中心点**。⚠️ **别从截图反推坐标** —— 截图像素与 AX point 的换算比随机型 / Display Zoom / 截图来源而变(Simulator.app 窗口截图含标题栏与边框,会整体带一段恒定偏移;`simctl io booted screenshot` 的裸帧没有),写死任何比例或偏移量都会点偏。真要对齐时现场量一次:`xcrun simctl io booted screenshot s.png && sips -g pixelWidth -g pixelHeight s.png`,再跟 `describe-ui` 根节点 AXFrame 比。
- **裁决顺序:截图为状态真相源,AX 树只做坐标源。** AX 树在 `fullScreenCover` 转场后会滞后(cover 已呈现却查无元素、已收却还在)——转场后先截图确认状态,再 `describe-ui` 取坐标。
- **键位走 HID 口径**:退格 = 42。⚠️ macOS 虚拟键码 51 当退格会**打出分号**。

**常用动作**:
- 长按(触发 contextMenu)= `touch --down` + `sleep` + `touch --up`
- 输入后**必须**再 `describe-ui` 验字段值再提交(焦点竞态会提交空/旧值)
- 屏外元素:先 `swipe` 滚到屏内 → `describe-ui` 取**实时** frame → 按坐标 tap
- 异步动画抓帧:每 1~1.5s `xcrun simctl io booted screenshot <帧>.png`(⚠️ 是 `io … screenshot`,没有 `simctl screenshot` 这个子命令)+ `describe-ui` 摘 label 轮询,事后按 AX 内容挑帧命名(实测能抓到 1s 级过渡)
- 首启序列(合规/ATT/引导/评分弹窗)是一次性资源:必须 `uninstall → install → launch`,**`simctl install` 覆盖装不清数据**

**★ SwiftUI TextField 聚焦(这条能省半天)**:默认路径就是 `axe tap`,但**点完必须轮询 `describe-ui` 确认 `UIKeyboardLayoutStar` 出现**(键盘起 = 焦点到手)再 `axe type`,type 完再 `describe-ui` 核 `AXValue` —— **焦点没验证就 type,是这一层最常见的空转来源**。

⚠️ 踩过一例:tap activation point 死活点不出焦点,键盘不起、`AXValue` 恒空、`axe type` 全打空。确认卡在这里再逐级退:① 换 `--tap-style physical` ② `axe touch -x <x> -y <y> --down --up --delay 0.1` ③ 最后才用冷启动自动聚焦:
```
terminate → launch → 轮询 describe-ui 直到出现 UIKeyboardLayoutStar(键盘起 = 聚焦成功)→ 直接 axe type
```
③ 只在**该 app 冷启后输入框自动聚焦**时成立,不是通用解,用前先确认这条前提。(复核过:axe 1.7.1 上 default / physical / simulator 三种 tap-style 都能聚焦 —— 别把 tap 当成 SwiftUI 上的死路,那是个案不是通例。)

**盲点纪律**:每一步动作前用 `describe-ui` 轮询确认目标元素**真的存在**再点,**宁慢勿盲**。踩过:回包未到就按预估坐标点,把「再识别一句」按成了 reset,整条流程被收。

**循环脚本必须带哨兵**:`axe tap --label` 对**带 emoji 的 label** 精确匹配会失败(如「👉 Get Started」用 `--label "Get Started"` 匹配不上),循环会卡死在同一页重复截图。解法:label 匹配失败即**回退坐标 tap**,并加「**页面指纹不变即判卡死**」的哨兵。

**系统弹窗会随机挡路**:SKStoreReview 评分弹窗首启后会自动冒出盖住输入框。解法:每步前 `describe-ui` 校验目标元素真在,弹窗元素出现就先处理掉。(顺带:它反而是 UI 审计清单里"系统评分弹窗态"的免费截图。)

### 层 3' · 手势探针 —— 截图看不出的那类缺陷

**场景**:视觉一模一样、但交互死了。这类缺陷**截图完全看不出来**,只能用手势层实测。

**做法**:用 `axe` 的 swipe 在页面各区域发探针,看手势是否被响应。

**实战战绩**:验出「内容列限宽套在 ScrollView **外面**」导致两侧成手势死区 —— 截图上与正确实现一模一样,是自验漏网、由手势探针抓回来的。
**推论纪律**:**截图相同 ≠ 通过。交互面必须用手势探针实测。**

### 层 4 · 接口层 —— 正 / 负 / 边界三批样本

任何 LLM prompt、过滤规则、校验逻辑,都要打真实请求,**三批一起测**:

| 批次 | 验什么 | 判据 |
|---|---|---|
| **负样本** | 该拦的拦住了 | 全部命中预期(如全返空) |
| **正样本** | 不该拦的没误伤 | 全部正常返回 |
| **边界样本** | 最容易被误伤的那几个具体 case | 逐个点名验,**不能只测"典型"** |

**边界样本是这层的灵魂** —— 它是防「过度过滤 / 过度收紧」的唯一保险。举例:做内容安全围栏时,专门验「Frankly, my dear, I don't give a damn.」这类**带敏感词的合法内容**是否被误杀。测到它才叫测过。

### 层 5 · 数据层 —— UI 动作 → 只读 SQL 铁证

每步 UI 操作后立刻对账,做到心法那句「点击能在库里找到那一行」。例:
- sheet 提交 → 查对应请求行是否落库
- 选择/收敛动作 → 断言 `status=resolved AND citations IS NULL`
- 删除动作 → **三表计数一次断言**

**护栏(照抄进任何 db 工具)**:只读前缀白名单 / 拒多语句 / 凭据从 CI 变量 API 内存取**不落盘不回显** / prod 需独立 `--confirm-prod`。

### 层 6 · CI / 部署 gate

- **CI 没绿连 dry-run 都不碰。**
- 每步显式加旗、**无常开授权**;prod 归项目负责人在自己终端亲手跑。
- ⚠️ **按 job 级状态判,别按 pipeline 级** —— 顶层 `status=manual`(残留手动 job)但目标 job 已 success 是常态形态。
- ⚠️ CI 输出解析**必须先去 ANSI 色码**(踩过:盯板空转半小时)。
- ⚠️ 平台 API 抖动是常态,单次 read timeout 不是流水线挂了,守望脚本要容错。
- ⚠️ **背景长任务一律用绝对路径** —— 背景任务里的 `cd` 会污染后续 cwd(踩过 exit 127)。

## Step 2 · 审查双轨(兜住自验的漏网)

自验只能证明「我想到的都对」,证明不了「我没想到的」。两轨互补,**各管一层,找茬的和写码的不是同一个脑子**:

| 轨 | 管什么 | 怎么跑 | 收敛判据 |
|---|---|---|---|
| **workflow 对抗审查** | 跨层契约 / 状态机 / 转场竞态 / DB 竞态 | 多维 lens 并行找茬 → **逐条对抗验证杀误报** | **审到连续一轮零新发现** |
| **清单直审(swiftui-pro)** | view 层 | 按九清单直审,不起 workflow | 清单走完 |

**实测数据(说明这一步不可省)**:
- 三段收敛曲线:`18→8→0`、`8→4→0`、`9+2+1→0`
- 单日 3 段 × 3 轮:确认缺陷 **30+ 全修**,**误报被对抗验证杀 ~18(误报率约 37%)**
- 一次 54 agent 审查**抓到作者已「验证通过」的回归**

**★ 编译通过 ≠ 没问题的活教材**:一次 IA 重构里,`BUILD SUCCEEDED` 且作者自读三遍,对抗审查仍逮出 2 个 blocker —— 其一是「关 sheet 与开 fullScreenCover 落在同一个 SwiftUI 事务,被 UIKit 丢弃」,会让整个功能在进程内彻底不可用。**编译器对事务竞态完全无感。**

**agent 的 finding 不是事实**:审查产出必须逐条 verify 才算数,别直接转述。踩过两次:转述 agent「数据不可恢复」的结论,一查 89 条里 69 条完好;agent 言之凿凿报「key 碰撞」还附了具体值,一验为假。

## Step 3 · 报证据(什么算合格)

**标准引用格式 = `文件:行号` + `commit hash`。** 「应该没问题」「已验证」不是证据。

合格证据的形态:
- **编译**:`BUILD SUCCEEDED` + error 行为空
- **DB 铁证**:只读 SQL 结果 + 明确断言
- **计数型硬数字**:`单测 55 → 63 全绿(新增 35)`、`30 屏 / 49 页 / 156 态`、`4/4 零失败 16.8 分钟`
- **样本矩阵**:正 / 负 / 边界各多少条、各什么结果(列表格)
- **截图**:作为状态真相源,按 AX label 内容命名帧
- **commit / CI 号**:`ios d3299fe`、`CI #3888/#3889`

**否定式证据也要报**:难确定性触发的态(引擎多候选 / 断网 / 非 Pro 账号 / AB 变体)**不硬凑**,在报告里点名「**未触发 + 原因**」。诚实覆盖比虚假全绿有用。

**结论被推翻要留痕**:以「⚠️ 更正:撤回……」开头,写清「错在哪 / 反证 / 判据修正」三段,**保留旧结论不删**。

## 附:全 App 逐屏截图审计(穷举驱动)

要做整体 UI 审计时,别「想到哪截到哪」:

1. **穷举防漏**:先用 workflow 并行读代码穷举「页面 × 状态 × 到达路径」(实测 8 模块 → 49 页 156 态),再上 **completeness critic 补漏**(逮到系统评分弹窗态、键盘弹起态等 6 项),然后按清单驱动截图 —— **比想到哪截到哪靠谱一个量级**。
2. **交付形态**:截图不裸堆,按用户链路组织成带流程箭头 / 状态徽章 / 逐屏注解的 HTML,顶部放「系统级发现」清单 —— **给人看的是「链路故事」,不是图堆**。
3. **诚实覆盖**:未触发的态点名说明,不硬凑。

## 硬性规则

1. **说「验不了」前必须先查** — 走 Step 0 清单,查完确实没有再说没有,并说清缺什么。未经核查的能力边界声明 = 把成本转嫁给人。
2. **编译通过不等于验过** — `BUILD SUCCEEDED` 对状态机 / 转场时序 / 布局溢出无感,必须叠 Step 2 审查双轨。
3. **截图相同不等于通过** — 交互面用手势探针实测(手势死区截图看不出)。
4. **坐标只信 AX,状态只信截图** — 坐标一律取 `describe-ui` 的 AX frame,别从截图换算(换算比随机型 / 缩放 / 截图来源而变);AX 树转场后滞后。
5. **接口/prompt 改动必打正负边界三批样本** — 尤其边界样本(最易被误伤的具体 case),这是防过度收紧的唯一保险。
6. **每步动作前先确认目标元素存在** — 宁慢勿盲;循环脚本带「页面指纹不变即判卡死」哨兵。
7. **UI 动作要能在库里对上账** — 关键路径配只读 SQL 断言;db 工具必须只读白名单 + 拒多语句 + 凭据不落盘。
8. **CI 没绿连 dry-run 都不碰** — 按 job 级判状态;prod 归项目负责人亲手跑,无常开授权。
9. **agent 的 finding 是待验证输出,不是事实** — 逐条 verify 才算数,别直接转述(实测误报率约 37%)。
10. **证据带 `文件:行号` + commit;未触发的态点名报** — 不硬凑覆盖,不用「应该没问题」结案。

## 反模式

❌ 「我本地编译不了 / 没有 key,你 build 一下试试」→ 先跑 Step 0 清单;绝大多数是没查。
❌ 改完只看代码 + 类型检查就交 → 至少过编译层,交互改动过模拟器层。
❌ 拿 `BUILD SUCCEEDED` 当验证完成 → 它对事务竞态无感,叠审查双轨。
❌ 截图看着一样就判通过 → 手势死区类缺陷只有探针能抓。
❌ 用截图目测像素换算坐标去 tap → 换算比不固定(窗口截图还含边框偏移),点不中;一律走 `describe-ui`。
❌ tap 完不验证焦点就直接 `axe type` → 先轮询 `UIKeyboardLayoutStar` 确认键盘起;仍不起再按 physical → touch → 冷启动 逐级退。
❌ `simctl spawn defaults read <bundle-id>` 读 app 台账 → 那是模拟器全局 prefs 域,不是 app 容器域(踩过:台账明明在记,外部读恒 0,险些误判功能坏了)。正路直读容器 plist:`data/Containers/Data/Application/<hash>/Library/Preferences/<bundle-id>.plist` 配 `plutil -p`。
❌ 靠 `simctl pbsync` 取分享面板导出的图 → 不带图像剪贴板,别在这条路上耗时;走「保存到文件」→ 直捞 `Containers/Shared/AppGroup/<id>/File Provider Storage/`。
❌ prompt 只改不测、指望部署后人肉试 → 本地同镜像起服务打真实请求。
❌ 只测典型正样本 → 边界样本(带敏感词的合法内容等)才是防误伤的保险。
❌ 直接转述 agent 的 finding 当结论 → 逐条 verify;误报率约 37%。
❌ 报「已验证/应该没问题」 → 给 `文件:行号` + commit + 数字。

## 常见问题

| 症状 | 原因 | 解决 |
|---|---|---|
| 声称"本地验不了"结果人家一查工具都在 | 跳过 Step 0 | 先跑工具链体检清单再表态 |
| 编译过了真机还是崩 / 功能不可用 | 只做了编译层 | 叠审查双轨,尤其状态机 / 转场竞态维度 |
| `axe tap` 点不中控件 | 用截图换算了坐标 | `describe-ui` 取 AX frame 中心点 |
| `axe type` 全打空 / 键盘不起 | 焦点没到手就 type 了 | 先轮询 `UIKeyboardLayoutStar` 确认;仍不起按 physical → touch → 冷启动 逐级退 |
| 退格打出分号 | 用了 macOS 虚拟键码 51 | HID 口径退格 = 42 |
| 转场后 AX 查无元素 / 已收还在 | AX 树滞后 | 先截图定状态,再 describe-ui 取坐标 |
| 循环脚本卡死在同一页重复截图 | emoji label 匹配失败 | 回退坐标 tap + 页面指纹哨兵 |
| 外部读 UserDefaults 恒 0,以为功能坏了 | 读的是全局 prefs 域 | 直读容器 plist + `plutil -p` |
| 首启弹窗序列复现不出来 | `simctl install` 覆盖装不清数据 | `uninstall → install → launch` |
| CI 盯板空转 | 输出带 ANSI 色码没去 | 解析前先去色码;按 job 级判状态 |
| 背景任务报 `no such file` (127) | 前面任务 `cd` 污染了 cwd | 背景长任务一律绝对路径 |
| 审查没完没了 / 草草一轮 | 没定收敛判据 | 连续一轮零新发现即停 |
