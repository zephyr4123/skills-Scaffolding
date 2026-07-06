---
name: multica-collab
description: Use when 用户提到 multica——想把任务派给 multica agent、看任务/看板/运行轨迹、做 onboarding 接入、出工作汇报，或贴出 multica 实例的 issue/run URL 时。让任意 coding agent（Claude Code / Codex / 任何带 CLI 的引擎）成为用户与 Multica 之间的操作界面：发 issue、观测 run、验收产物、救活死锁，全程 CLI，用户零点击。
---

# Multica Collab：用对话驾驭 AI 原生工作区

Multica（开源：<https://github.com/multica-ai/multica>，官方云：<https://multica.ai>）是一个 AI 原生团队工作区：**AI agent 是一等队友**——在看板上被分派 issue、发评论、改状态、跑代码，和人类成员完全一样。

你（正在读这份 skill 的 coding agent）的角色：**用户与 Multica 之间的翻译层**。用户说人话，你翻译成 `multica` CLI；用户永远不需要打开网页（唯一例外：首次 OAuth 登录）。

这套工作范式的核心价值，向用户解释时用这个框架：

| Multica 对象 | 工作管理语义 |
|---|---|
| issue | 待办/看板卡片，description 就是给 agent 的任务书 |
| run 轨迹 | 全流程审计日志——排查、审计、复盘、统计汇报的原始数据 |
| comment / outputs | 过程与产物的文档沉淀，上下文永不丢失 |
| agent + runtime | 干活的队友和它跑在哪台机器上 |

## 铁律（先读）

1. **CLI 是唯一清单**：能力边界 = `multica --help` 的输出。不确定的命令先 `multica <cmd> --help` 自查，**绝不编造命令或参数**。概念疑问查官方文档 <https://multica.ai/docs>（没有网页抓取工具就用 `curl` 拉），不凭记忆复述。
2. **URL 一律转 CLI**：用户贴任何 multica 实例（官方云或自托管域名）的 `/issues/<id>`、`/runs/<id>`、`/agents/<id>` 类 URL 时，从 path 提取 ID 用 CLI 拉数据。**禁止**用浏览器工具打开（SPA + 登录墙，无登录态必跳 login，纯浪费）。例外：首次 OAuth、用户明确说"帮我打开网页看看"、拉官方文档。
3. **ID 规则**：CLI 接 identifier（如 `TES-3`）或完整 36 位 UUID，**不接纯数字**，也不接 web UI 显示的 8 位截断 ID。截断 ID → 先 `issue runs <identifier> --output json` 拿完整 UUID。
4. **多身份先对表**：`--profile <name>` 隔离不同 server/账号；同账号多 workspace 用 `multica workspace --help` 自查列出/切换命令。**任何写操作前确认 profile 与 workspace 指向**——把个人任务发进公司空间（或反之）是事故，拿不准就问用户。
5. **破坏性操作先确认**：删除 issue/agent、修改他人负责的条目、批量改状态，先向用户复述再执行。
6. 结构化数据一律 `--output json`，给用户看时翻译成人话。
7. **issue 合法状态**（以 `multica issue status --help` 为准）：`backlog / todo / in_progress / in_review / done / blocked / cancelled`。别发明状态名。

## Phase 0：从零上车（用户什么都没有时）

按顺序检测，缺哪步按对应小节补；全通过则直接跳到 Phase 1。

```bash
multica --version                      # ① CLI 装了吗          → 缺则走 0.1
multica [--profile X] auth status      # ② 登录态有效吗        → 缺则走 0.2
multica [--profile X] runtime list     # ③ 有在线算力吗        → ②通过③不通过：multica daemon start（失败看故障表）
multica [--profile X] agent list       # ④ 有能干活的 agent 吗 → 缺则走 0.3
```

### 0.1 装 CLI

```bash
# macOS
brew install multica-ai/tap/multica
# 其他平台 / brew 不可用：按官方文档安装页操作（https://multica.ai/docs）
```

### 0.2 选 server 并登录（唯一需要用户碰浏览器的一步）

| 场景 | 命令 |
|---|---|
| 个人 / 小团队（推荐，零运维） | `multica setup cloud` → 官方云 multica.ai |
| 公司 / 自托管 server | `multica setup self-host --server-url <URL> --app-url <URL>` |
| 已有多身份，需要隔离 | 所有命令前加 `--profile <名字>`（config/daemon/workspace 全隔离） |

执行后浏览器自动弹出 OAuth 页——**提示用户**：用邮箱登录，没账号就在页面上邮箱+验证码注册，完成后回终端看 `Setup complete`。

setup 成功后自动发生两件事，逐一确认：

1. **workspace 绑定**：登录后 CLI 自动发现并绑定你的 workspace（终端会打印 `Found N workspace(s)`，新注册账号会自带一个初始 workspace）。多 workspace 时用 `multica workspace --help` 自查列出/切换命令确认当前指向。
2. **daemon 自动启动**：这台机器随即成为 runtime（算力提供方），机器上装的 coding 引擎（claude/codex/gemini…）各自注册为一个 runtime。验证：

```bash
multica auth status     # 应显示 Server / User / Token
multica runtime list    # 应有本机 runtime，STATUS=online；没有 → multica daemon start
```

> headless 环境（SSH/CI）免浏览器方案：先在任一有浏览器的设备完成注册、并在 web 端个人设置里生成 PAT，再回 headless 机器 `multica login --token`。

### 0.3 建第一个 agent

新 workspace 没有 agent 就没人干活。三步：

**第一步**，把 agent 的 instructions 写进本地文件（这是给 agent 的系统提示）。最小可用模板：

```bash
cat > /tmp/helper-instructions.md <<'EOF'
你是本 workspace 的通用助手 agent。
工具箱：multica CLI（已在 PATH、已认证）。能力边界 = `multica --help`，
先 --help 自查再执行，绝不编造命令。
职责：答疑、盘点 workspace、按任务书执行操作。
语气：与用户同语言，简洁直接。
边界：删除类操作先在 comment 里说明并等确认。
EOF
```

> 新 workspace 通常自带引导 issue（含官方 Helper 配方，比模板更全）：`multica issue list --output json` 找到它，`multica issue get <identifier>` 读 description 照抄。

**第二步**，选 runtime 并创建：

```bash
multica agent create \
  --name "Helper" \
  --description "workspace 通用助手：答疑、建任务、盘点状态" \
  --instructions "$(cat /tmp/helper-instructions.md)" \
  --runtime-id <从 runtime list 选一个 UUID> \
  --visibility workspace --output json
```

（`--visibility workspace` 是 legacy 参数但当前可用，等价于新参数 `--permission-mode public_to --public-to-workspace`。）

**第三步**，`multica agent list` 确认在列。

### 0.4 冒烟测试（验证闭环）

```bash
cat <<'EOF' | multica issue create --title "冒烟测试" --assignee "Helper" \
  --description-stdin --output json
目标: 盘点本 workspace 的 runtime / agent / issue，各列一行
验收: 本 issue 有一条盘点结果 comment
约束: 只读操作，不改任何东西
EOF
# ↑ 返回 JSON 里的 identifier 字段（形如 ABC-3）就是后续命令用的 ID

# 秒级认领后观测：
multica issue runs <identifier> --output json   # 拿 task-id（第一条的 id 字段）和 run 状态
multica issue run-messages <task-id>            # 看轨迹
multica issue comment list <identifier>         # 收产物
```

闭环走通（issue: todo → in_progress → in_review → 人验收 done）即 onboarding 完成。

## Phase 1：日常派活协议（用户意图 → 你的动作）

| 用户说 | 你做 |
|---|---|
| "把 XX 丢给 agent / 帮我托管跑" | 写任务书 → `issue create --assignee <agent> --description-stdin`（多行任务书永远走 stdin） |
| "跑得怎么样 / 到哪一步了" | `issue runs` 拿最新 task → `run-messages <task-id> --since N` 增量拉轨迹 → 人话摘要 |
| "让它继续 / 换个方向 / 补个信息" | `issue comment add <id> --content "<提示>"`（多行用 `--content-stdin`；agent 下次运行会读完整 comment 记录重建上下文） |
| "验收 / 可以了" | 核对任务书里的验收标准 → `issue update <id> --status done` |
| "不合格 / 打回返工" | `comment add` 写明不合格点与整改要求 → `issue update <id> --status in_progress`（或 todo 重新排队） |
| "这周干了啥 / 出个汇报" | `issue list --output json`（`--status` / `--assignee` 过滤）+ 逐 issue `runs` 汇总 → 结构化汇报 |
| "有哪些 agent / 算力现在什么情况" | `agent list` + `runtime list`，翻译成人话 |
| "看看 XX 负责的任务" | `issue list --assignee <名字> --output json` |
| "换个 agent 接手" | `issue update --help` 自查重指派参数；改完 comment 说明交接上下文 |
| "先停下别跑了" | 用 `--help` 自查 stop/cancel 类命令；没有就 `issue update --status blocked` + comment 说明（注意：改 issue 状态不保证终止已在跑的 run，向用户说明这一点） |
| "这个不用做了" | 确认后 `issue update <id> --status cancelled` |
| "卡死了 / 一直失败" | 走 Phase 2 的[死锁识别与救活](#死锁识别与救活) |
| 贴一个 multica URL | 提取 ID → `issue get` + `issue runs` + `comment list` 三件套，输出状态/执行史/最新产物 |

**任务书四要素**（写 description 的模板——写清楚 = 少返工）：

```
目标: 要达成什么（一句话说清）
上下文: 仓库/路径/分支/相关 issue ID
验收: 怎样算完成（可检验的标准）
约束: 不许动什么、不许做什么
```

**issue 生命周期**：`todo`（等认领）→ agent 秒级认领 → `in_progress`（运行中，轨迹实时可看）→ 干完自动 `in_review`（等人类验收——这是 HITL 设计，**绝不擅自替用户验收**）→ 验收后 `done`。

## Phase 2：托管纪律（长任务的正确姿势）

**什么任务值得托管**：预计连续跑 30 分钟以上、或轨迹需要留档/给他人复盘的 → 托管给 multica agent；几分钟的小改动 → 你自己本地直接干，别为仪式感托管。

**checkpoint 习惯**：给 agent 的任务书里要求"每完成一个阶段，往 issue 加一条 `✅ [k/N] <阶段> 完成 — <产物位置>` 的 comment"。这一条同时买到三样东西：进度一目了然、审计有锚点、中断后可从断点续跑。

**断点续跑**：multica 没有暂停键。机器休眠/断网导致 run 失败**不丢 issue**——`multica issue rerun <id>` 重跑，在任务书或 comment 里嘱咐 agent"先读 checkpoint comment，从第一个没打勾的阶段继续"，即可不从头来。

### 死锁识别与救活

长会话的经典病，按序处置：

1. **判定**：`issue runs <id>` 连续 ≥2 次 failed 且错误文本**完全一致** → 会话历史被永久污染（超限内容/坏状态），继续 resume 必然复发
2. **救活**：`multica issue rerun <id>` 会重新入队一个全新任务、丢弃污染的会话历史；issue 的 comment/产物记录全保留，agent 靠读 issue 重建上下文
3. **先修再重跑**：如果根因是任务书缺信息、环境缺依赖或 agent instructions 的 bug——直接 rerun 只会在同一个地方再撞一次。先补 comment/修环境/改 instructions，再 rerun
4. 临时故障（网络抖动、超时）不用修，直接 rerun

**debug-via-issue**：issue 自己会说话——runs 的错误信息 + run-messages 轨迹 + comment 记录构成完整现场。用户想让别人帮忙时，甩一个 issue URL 就够，不需要口头复述任何上下文。

## Phase 3：团队协作模式

把这套范式带给一个团队（新项目组、临时协作、活动式冲刺）时的形态：

1. **一人建 workspace**，web 端把成员邮箱邀进来（成员各自走 Phase 0.2 登录）
2. **有算力的成员**各自 `daemon start`，机器变成共享 runtime；没算力的成员照样发 issue、看轨迹
3. **约定看板即真相**：所有任务进 issue（人类的活也建 issue 指派给 member），所有讨论走 comment，所有产物写进 outputs——散会后不需要"谁来补会议纪要"，轨迹本身就是纪要
4. **agent 按职能建**：一个 Builder 干代码、一个 Researcher 做调研、一个 Helper 管杂务，按需加；`project` 给 issue 分组、`label` 打标签、`squad` 把多个 agent 编组接活、`autopilot` 做定时/事件触发（如每晚自动出进度汇报）——这四个对象的用法以 `--help` 现场自查为准
5. 团队成员不需要都懂 CLI——**任何人身边有一个装了本 skill 的 coding agent，就等于有了全功能操作台**

## 常见故障速查

| 症状 | 处理 |
|---|---|
| issue 一直停在 todo 没人认领 | `runtime list` 看有没有 online runtime；没有 → 目标 runtime 的机器上 `daemon start`；有 → 看 agent 是否绑在离线 runtime 上（`agent get`） |
| CLI 报 401 / token 失效 | 重跑 `multica setup cloud`（或 self-host 同参数）走一遍 OAuth |
| `issue get 12` 报 404 | 用了纯数字。改用 identifier（`ABC-12`）或完整 UUID |
| run-messages 一开始就 fail | 看第一条 error——多半是任务书没给够输入（对照任务书四要素补 comment 后 rerun） |
| daemon 起不来 | `multica daemon logs` 看原因；常见：token 失效、上一个进程没退干净（先 `daemon stop` 再 start） |
| 连续同错 failed ≥2 次 | 死锁，走 Phase 2 的[死锁识别与救活](#死锁识别与救活) |

## 红线（铁律之外的补充）

- agent 干完停在 in_review 时，绝不擅自替用户验收成 done
- 本 skill 不覆盖 multica server 的部署运维（自托管 server 搭建看官方仓库文档）
- 其余行为规范见开头[铁律](#铁律先读)，两处冲突时以铁律为准
