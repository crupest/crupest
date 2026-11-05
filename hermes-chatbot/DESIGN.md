# hermes-chatbot 设计

## 1. 基本模型

一个实例只服务一个会话（一个群或一个好友）。多会话就是多套 adapter + plugin 容器，
共享一个 NapCat；隔离由进程边界保证，不靠单进程里的多租户状态。

```
NapCat ──反向 WS /onebot──▶ adapter ──WS /hermes──▶ plugin（Hermes）
```

- `adapter` 是唯一接触 NapCat 的进程。它只做 Hermes 做不到的事：会话绑定、入站过滤、
  出站目标固定、动作白名单、活跃窗口、`seq` 映射、通知合成。
- `plugin` 是 Hermes 的 `BasePlatformAdapter`。负责事件 → `MessageEvent`、媒体落盘、
  `chatbot_*` 工具和发送结果映射。
- `core` 是两边共用的纯逻辑：协议模型、渲染、富文本校验、配置解析。core 不做 IO。

adapter 不做内容策略、不自动回复、不重试。模型层的行为由 Hermes + SOUL 决定。

## 2. 线协议

两段都走 OneBot 11 子集，不增加业务自定义帧：

- 事件：`post_type`
- 请求：`{action, params, echo}`
- 响应：`{status, retcode, reason?, wording?, data?, echo}`

唯一的自定义 meta event 是 `adapter_ready`，携带版本、`config_sha` 和当前会话绑定；
插件只校验并记日志，不因 `config_sha` 不一致拒绝连接。

adapter 只把消息事件和合成通知转给插件；其余事件、未知 `post_type`、坏帧直接丢弃。
普通消息原样过线，adapter 不改写正文。

## 3. 会话与配置

- 绑定目标为 `group_id` 或 `user_id`，二者至少有一个；环境变量
  `CHATBOT_GROUP_ID` / `CHATBOT_USER_ID` 优先于配置文件。
- 两侧读同一份 `/opt/chatbot/config.toml`。adapter 可写，Hermes 只读；文件缺失时
  adapter 从镜像模板补一份。
- token 不进配置文件：`CHATBOT_ONEBOT_TOKEN` 只给 adapter，`CHATBOT_PLUGIN_TOKEN`
  只给 adapter 和插件。两条链路必须使用不同 token。
- 配置不热重载，改完重启。`config_sha` 只计算配置文件本身。
- `[features]` 控制模型能发哪些段；`[limits]` 控制冷却、段数、转发条数、上传目录和大小。

## 4. 入站

adapter 先做第一道闸：

- 只处理绑定会话；群消息需要 @ bot 或处于活跃窗口；私聊直接放行。
- 活跃窗口由**任意一次成功的出站动作**刷新；私聊不建窗口。
- 戳一戳、进退群按 `[notify]` 合成文本事件，并标记 `internal` 和 `origin`。
- 群命令先要求原始事件里真实的 @ self，再剥掉标记；手打 `[[@self]] /cmd` 不能伪造。

插件负责渲染：

- 群消息加 `[昵称(QQ)#序号]` 前缀，私聊不加。
- 引用不写进正文，填到 `MessageEvent.reply_to_*`；取不到被引消息时照常投递正文。
- 媒体占位符带原生 `id` 和缓存状态，供模型决定是否调用取回工具。

## 5. 出站

adapter 是唯一的策略边界：

- 动作白名单；只允许工具暴露的参数子集，多余字段拒绝。
- 目标固定：群号/好友号必须等于绑定值；缺失时补齐，显式不同则拒绝。
- `send_*_msg` 的 `message` 必须是数组；CQ 码字符串直接拒绝。
- 段级校验按 `[features]` 和 `[limits]` 执行；未知段类型拒绝。
- `@` 任意数字 QQ 都放行，成员关系交给 NapCat；`@self` 允许；`@all` 发送前检查 bot
  是否为群主/管理员，非管理员直接拒绝，避免 NapCat 超时但消息已发出的歧义。
- 媒体只接受 `limits.upload_dir` 下的本地文件；`http(s)` 由插件先经 SSRF 防护下载，
  adapter 不接受远程 URL，避免让 NapCat 去抓内网地址。

动作成功后刷新活跃窗口。`seq` 映射在 adapter 内维护；查不到的 `real_seq` 原样透传，
不做猜测。

## 6. 富内容与媒体

纯文字仍走 Hermes 的直接回复。以下内容只通过 `chatbot_send_message` 发送：

- `at` / `face` / `dice` / `rps` / `reply`
- 参数是类型化 `segments` 数组，不是 OneBot 原始段
- 最多 20 段，文本合计最多 4500 字
- `reply` 必须位于第一段

入站标记统一为文本：

```
[[@self]]  [[@12345]]
[[表情:得意]]  [[大表情:汪汪]]  [[贴表情:敲敲]]
```

表情使用 QQ `faceText`，不把内部 id 暴露给模型。入站接受任意表情；出站只接受
`core/faces.py` 表内的 `faceText`，表外的新表情能显示但可能无法回发。单发一个表情时
QQ 可能自动放大成“大表情/贴表情”，这是客户端行为，工具没有大小参数。

媒体由插件流式下载到 `[plugin] cache_dir`；该目录与 NapCat 共享，所以缓存可以直接回发。
缓存启动时清理一次，之后每 24 小时清理：删 7 天前的文件，总量超过 1 GB 再从最旧的删。
下载只允许 http/https，禁止跳转到私有网段/环回，大小受配置限制。

`MEDIA:` 图片/文件继续走 Hermes 自带链路，插件不拦截、不替换。

## 7. 工具与 SOUL

工具统一 `chatbot_*` 前缀，覆盖发送、戳一戳、转发、上传、历史、成员、群文件、媒体取回、
资料修改等能力。工具的参数、返回值和错误格式以 tool description 为准，文档不重复。

SOUL 只写行为规则：何时回、何时不回、`NO_REPLY`、隐私确认、发送纪律。平台格式在
`platform_hint`，工具契约在 tool description。

## 8. 失败与重试

- 失败分两类：策略拒绝（不可重试）和传输/上游失败（可重试）。
- 策略拒绝立即返回最终失败，不走 Hermes 的纯文本兜底。
- 传输/上游失败标记 `retryable`，交给 Hermes 重试；插件不自己重试。
- 插件等待 RPC 的超时必须长于 adapter 的动作超时；上传类再留额外余量，避免两层超时叠加。
- 面向模型的失败都带可读原因和原因码，不静默降级。

## 9. 已知取舍

| 取舍 | 影响 |
| --- | --- |
| 无事件重放 | Hermes 重启期间的消息会丢 |
| 无发送去重 | 网关重试可能重复发送；换取失败不被伪装成成功 |
| 无排队 | 多人同时说话交给 Hermes 的 busy 合并 |
| 不展开合并转发 | 模型只看到 `[forward id=…]`，需要时调用工具读取 |
| 单会话绑定 | 群和好友需要各一个实例 |
| 长文切分后部分失败 | 后段失败会导致整段重发，前段可能重复 |
