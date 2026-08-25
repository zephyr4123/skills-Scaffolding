---
name: zephyr-cloud-cli-ops
description: Use when 要配置云上资源（对象存储 / CDN / 证书 / DNS 解析）、静态资产要迁上云分发、用户拿出一个新云账号想让 agent 接管运维、或线上 CDN 加载慢 / 零星握手失败 / 测速结果反复要排查时 —— CLI-first 云运维分工协议：控制台是人的界面、API 才是 agent 的界面，人只做付钱 / 开通 / 发密钥三类控制台专属动作，其余（建桶 / 传件 / 证书 / 加速域名 / DNS / 防盗链 / 预热 / 验证）全由 agent 用 CLI+SDK 完成。含开工四步协议（凭据归位 → 验活 → 摸底 → 动手）、COS+CDN 静态资产十步全链蓝图（每步带完成判据）、实测陷阱清单（边缘证书铺设窗口期误诊、`--resolve` 指定节点是错误测法、本机 VPN 隧道废掉测速）。方法论跨云成立，worked example 是腾讯云。
engines: [claude-code, codex]
---

# zephyr-cloud-cli-ops：一把密钥，agent 把云配完

> **心法：云控制台是人的界面，API 才是 agent 的界面。** 人在控制台只做三类事——付钱、开通、发密钥；其余一切都该是 agent 用 CLI/SDK 完成的。这类活低效的根源几乎只有一个：分工划错——要么让人替 agent 去点控制台，要么 agent 拿不到密钥在那儿隔靴搔痒。

> 🔴 密钥处理的硬规矩（绝不进代码 / argv / history、按需加载、登记册）权威副本在 `zephyr-secrets-hygiene` 与 HABITS 红线节；开通计费资源、不可逆操作前经用户确认也是 HABITS 的规矩。本 skill 只讲它们在云运维场景怎么落地。命令与 API 名是腾讯云的（tccli + cos-python-sdk-v5）；换云的差异与不变量见 §五。

## 一、分工判据：什么必须引导用户做

判据一条：**API 做不了的才轮到人。** 云厂商把四类动作锁死在控制台——其中实名认证是一次性前置（多数账号早已完成），日常真正要引导的就是付钱 / 开通 / 发密钥三类：

| 人在控制台做 | 为什么 API 做不了 | agent 怎么引导 |
|---|---|---|
| 实名认证 | 法规要求人证对应 | 开工前确认状态即可（多数账号早已完成） |
| 充值少量余额 | 支付要人 | 按量付费余额为 0 会开不了服务 / 欠费停服；个人项目 10~20 元够跑很久。同时把计费模式（存储 / 流量单价）讲给用户 |
| 开通服务（点「同意协议」） | 协议勾选是法律动作 | 报产品名让用户在控制台搜索进入，提示「开通即可，别的都不用点」——**明确拦住用户往下配置** |
| 创建 API 密钥 | 密钥签发是授权动作 | **首选引导建 CAM 子账号密钥、只授本次所需的产品权限**（腾讯云有 QcloudCOSFullAccess 这类产品级预设策略）；图省事用主账号根密钥也能干活，但要讲明爆炸半径是全账号、事后建议轮换。交接首选存成 600 权限文件给路径；直接粘贴也行，但明文会留在会话记录里，粘贴过的密钥视为待轮换。到手立刻按 secrets-hygiene 归位，原地不留副本 |

用户还要**拍板**的决策（是决策不是操作）：加速区域（大陆节点要求域名有 ICP 备案，无备案走境外 / 全球）、CDN 子域名叫什么、桶放哪个地域（贴近回源方 / 主要用户）。

**除此之外不要让用户碰控制台。** 用户跑去点「添加域名」表单是分工失守的信号——当场拦下（"这步是我的活，退出来就行"）。控制台向导会引导人手工做 agent 三秒钟能做对的事，又慢又留不下可复核的记录。

## 二、开工协议（agent 侧，四步定序）

1. **凭据归位再动手**：按 `zephyr-secrets-hygiene` 入家目录（600 + `withkey` 按需加载）。腾讯云是零副本的好例子：`TENCENTCLOUD_SECRET_ID/KEY` 两个环境变量 tccli 与 COS Python SDK 通吃 → **轮换只改一处**。工具选型就看这条：能读环境变量的 CLI/SDK 优先；要求密钥进 argv 或独立配置文件的（如 coscli）能不用就不用。
2. **工具链隔离**：专用 venv（如 `~/.venvs/<云名>`），不污染全局。通用 CLI 一装全产品线 API 都在（腾讯云 tccli 覆盖 CDN/DNS/SSL/CAM/STS…）；对象存储的桶 / 对象操作通常**不在**通用 CLI 里，补装官方 SDK（腾讯云：cos-python-sdk-v5）。
3. **验活先行**：第一条调用必须只读且无副作用（腾讯云：`sts GetCallerIdentity`）。一次验三件事：密钥活的、身份是预期账号、CLI 链路通了。
4. **摸底再动手**：花两三条只读调用拿关键前置事实。腾讯云：`cam GetUserAppId`（桶名强制 `<名>-<APPID>` 后缀）、`dnspod DescribeDomainList`（**域名解析是否托管在同账号——这是证书验证与 CNAME 能否全自动的分水岭**，不在同账号就要把 DNS 步骤降级成引导用户去他的解析商操作）。

## 三、蓝图：静态资产上 COS + CDN（走通过的全链）

每步 = 目的 + API + **完成判据**（没判据的步骤等于没做完）。步骤序是通用骨架，API 名是腾讯云：

| # | 步骤 | 腾讯云做法 | 完成判据 |
|---|---|---|---|
| 1 | 建桶 | SDK `create_bucket`，公开资产 ACL public-read | `create_bucket` 无异常返回；终判交给步骤 2 的匿名 HEAD |
| 2 | 上传 | SDK `upload_file` + 显式 `ContentType` + `CacheControl: public, max-age=31536000, immutable` | 逐文件 HEAD 比对 Content-Length；匿名 curl 能 200 |
| 3 | 免费证书 | `ssl ApplyCertificate --DvAuthMethod DNS_AUTO`（解析同账号时全自动，常分钟级签发） | `DescribeCertificateDetail` Status=1（已颁发） |
| 4 | CDN 归属验证 | `cdn CreateVerifyRecord` → dnspod 写 TXT → `cdn VerifyDomainRecord`（TXT 零成本，留着最稳妥；同主域再接入是否免验未实测） | Result=true |
| 5 | 加速域名 | `cdn AddCdnDomain`：COS 源、`ServerName` 与源站同值、回源 HTTPS；大陆 `Area=mainland` | `DescribeDomains` Status 由 processing → online（实测十余分钟） |
| 6 | CNAME | dnspod `CreateRecord` 指向 CDN 分配的 `*.cdn.dnsv1.com` | dig 解析出边缘节点 IP |
| 7 | 绑 HTTPS | `cdn UpdateDomainConfig --Https`（CertId + http2 on） | `curl -I` 走 HTTP/2 返回 200 |
| 8 | 防盗链 | `UpdateDomainConfig --Referer` 白名单 | **正反例都测**：本站 referer 200 / 陌生 referer 403 |
| 9 | 预热 | `cdn PushUrlsCache` 全量 URL | `DescribePushTasks` 全 done（复测响应头 `X-Cache-Lookup: Cache Hit` 可作旁证） |
| 10 | 消费方联动 | 站点侧把新域名加进资源白名单（CSP `media-src` / `img-src` 等） | 线上响应头可见新域名，页面资源实际加载 |

配套纪律：

- **视频先查 faststart**：moov atom 在文件尾部时浏览器要多一次 range 往返才能起播。判法：解析 mp4 顶层 atom 顺序，moov 应在 mdat 之前；不满足就 `ffmpeg -c copy -movflags +faststart` 无损重封装（秒级）再传。
- **防盗链白名单必须含**：本站各级域名 + `localhost` / `127.0.0.1`（本地开发）+ 允许空 referer（直开 / 老客户端）。漏 localhost 的代价是本地 dev 资源全 403，而且往往上线后才被发现。
- **不可变风格**：内容变了就换对象名（URL），不复用旧名；非要复用就必须 `PurgeUrlsCache` 且接受边缘生效延迟。对象名用语义名（`video/home-hero.mp4`），别沿用上游的哈希乱名。
- **续期台账**：免费证书普遍 90 天，AutoRenewFlag 不可尽信——**签发当场**把到期日与续期动作（重新 Apply + UpdateDomainConfig 换绑）记进项目记忆 / 台账。到期没换，资源全断。
- **镜像前查授权**：把第三方 CDN 的资产搬进自己的桶之前，确认许可条款允许镜像自用。

## 四、你看到的 vs 真相（实测陷阱清单）

| 你看到的 | 真相 | 怎么防 |
|---|---|---|
| 域名刚 online，零星 SSL 握手失败（curl exit 35） | 边缘节点证书还没铺满的窗口期，几分钟内自愈 | 别当故障修；隔几分钟连续复测，**稳定失败**才是问题 |
| `curl --resolve` 指定某边缘 IP 超时 →「这节点挂了」 | 你绕过了调度器的运营商匹配，跨网访问别家运营商的边缘节点超时是常态 | **永远用正常域名解析测**；解析结果每次都在换 IP，那是调度不是故障 |
| 本机测速恒定几百 KB/s →「CDN 不行」 | 本机代理 / VPN 隧道在绕路。特征：到大陆边缘 connect >100ms + 吞吐恒定低值 | 结论必须来自干净大陆 vantage（如同厂商云服务器）；本机数字只作参考，顺手提醒用户给自己域名加 DIRECT 分流 |
| nginx reload 后立刻 curl，响应头还是旧值 | reload 异步，撞上了还没退役的旧 worker | 隔 1~2 秒复测再下结论；以文件实际内容 + 复测为准 |
| 两次测速差 4 倍 → 「速度反复横跳」 | 单次测量噪声：冷热缓存、节点轮换、本机负载 | 连续 3+ 次、带 `remote_ip` 与分段耗时（connect / 首字节 / 吞吐），分段定位瓶颈在哪一跳 |
| 控制台里的「购买资源包」入口 →「要先买才能用」 | 资源包只是可选的预付折扣，按量付费不需要预购（腾讯云 COS/CDN 实测；其他产品未逐一验证——未开通的产品打开控制台通常是开通引导页，那才是要用户点开通的信号） | 给用户讲清计费模式，别让「购买」字样吓停流程 |

## 五、跨云通用性

分工协议（§一）、开工四步（§二）、蓝图骨架（§三的步骤序与判据思路）、陷阱（§四大半）在 AWS / 阿里云 / Cloudflare 同样成立。换云要重查的只有：各步 API 名、桶命名规则、证书签发方式、大陆合规差异（备案）、以及最小权限子身份怎么建（IAM / RAM / CAM，名字不同一回事）。**换云时别丢的是定序**：归位 → 验活 → 摸底 → 蓝图逐步带判据推进。

## 反模式

❌ 让用户在控制台一步步点操作 —— 把 agent 的活推给人，分工失守。
❌ 拿到密钥第一条就跑写操作 —— 验活必须只读。
❌ 密钥进 argv / shell history / 仓库 —— 权威规矩见 secrets-hygiene。
❌ 用户没确认就开通计费资源，或不告知计费模式。
❌ 测一次速就下「快 / 慢」结论；拿 `--resolve` 的结果说「节点挂了」。
❌ 把账号 ID / 桶名 / 证书 ID 这类实例信息写进会进 git 的文档 —— 实例信息归项目记忆，方法论才进仓库。

## 本 skill 不带脚本，这是有意的

每一步的参数都取决于当次的域名 / 桶名 / 地域 / 资产清单，固定脚本会把「判断」伪装成「执行」，还得为多云多版本长期负责。给的是分工协议、定序、判据与陷阱；具体 API 调用当场照官方文档拼——这正是 agent 最擅长、也最不需要预制的部分。
