# QQ Bot 重写方案（core / adapter / plugin）

> 状态：待确认后实施。项目放在仓库根目录 `hermes-qqbot/`，发行名与导入名统一加 `crupest` 前缀。

## 0. 两条新要求落到设计上

**① 自动行为归还 Hermes。** adapter 只保留 Hermes 做不到的事：入站过滤、出站目标夹、活跃窗口、动作白名单，外加两件必要的转换（`real_seq` 映射、通知合成）。其余全部删除或交给 Hermes/SOUL：

| 原 adapter 逻辑 | 处置 |
| --- | --- |
| @ 后自动加表情 | 删。新增 `react` 工具，是否回应由模型按 SOUL 决定 |
| `/command` 权限过滤 | 删。交给 Hermes 网关自带的命令鉴权（`allow_admin_from` 等） |
| 戳一戳/进退群合成系统消息 | **保留**，按原行为：adapter 合成文本事件并标记 `internal` |
| 黑名单、限流 | 删。单群单好友场景由 Hermes allowlist 覆盖 |
| 发送去重 | 删。已知风险见 §11 |
| 合并转发展开 | 删。渲染成 `[forward id=…]`，不展开 |
| Markdown → 纯文本 | 交给 Hermes 的能力声明；core 里留一个可关的兜底清洗 |
| 出站文本正则过滤 | 删。模型不该说的话由 SOUL 约束，不设第二套内容策略 |

表情反应的窗口副作用随之消失：**窗口改为「任何成功的出站调用」刷新**，不再需要插件在 `api_call` 里带 `chat_id`。单会话绑定让这件事退化成一次 `touch()`。

**② 代码要求。** 见 §8（错误处理）、§9（日志）、§10（测试）。三条硬约束：

- 主路径不写防御性废话；只在循环边界和 IO 边界捕获异常，且必须带堆栈和上下文日志。
- 所有跨进程数据先过模型校验；校验失败是可预期分支，不是崩溃。
- 单测按「表驱动 + golden frames」，不写只验证"函数被调用过"的测试。

## 1. 目标与非目标

**目标**：一个 QQ 会话（一个群或一个好友）对应一套 adapter+plugin；代码可读、可测、可替换；NapCat 实例可被多套共享。

**非目标**：WebUI、automation API、cron、多群配置、消息重放、跨会话隔离（由"一实例一会话"保证）。

## 2. 仓库布局

```
hermes-qqbot/                     # 仓库根目录下的独立项目
├── core/                       # 纯逻辑，无 IO，两边共用
│   ├── pyproject.toml          # crupest-hermes-qqbot-core
│   ├── src/crupest_qqbot_core/
│   │   ├── errors.py           # 异常与 retcode 映射
│   │   ├── schema.py           # OneBot 帧模型 + parse_frame
│   │   ├── segments.py         # 消息段构造/解析
│   │   ├── render.py           # 入站事件 → 模型可读文本
│   │   ├── notice.py           # 戳一戳/进退群合成
│   │   ├── text.py             # 出站文本清洗（可关）
│   │   ├── config.py           # TOML 模型、校验、sha256
│   │   └── logging.py          # 日志格式与上下文
│   └── tests/fixtures/frames/  # golden frames（两包共用）
├── adapter/
│   ├── pyproject.toml          # crupest-hermes-qqbot-adapter
│   ├── src/crupest_qqbot_adapter/
│   │   ├── __main__.py         # 入口：加载配置、起服务、优雅退出
│   │   ├── app.py              # 装配与生命周期
│   │   ├── napcat.py           # 反向 WS 接入 + echo 关联 + API 客户端
│   │   ├── relay.py            # 插件 WS 服务端 + 动作转发
│   │   ├── policy.py           # 绑定、入站判定、动作白名单、目标夹
│   │   ├── seq.py              # real_seq → message_id
│   │   └── window.py           # 单会话窗口
│   └── tests/{fakes.py,test_*.py}
└── plugin/
    ├── pyproject.toml          # crupest-hermes-qqbot-plugin
    ├── plugin.yaml
    ├── src/crupest_qqbot_plugin/
    │   ├── __init__.py         # register(ctx)
    │   ├── adapter.py          # BasePlatformAdapter 实现
    │   ├── media.py            # 媒体下载（SSRF 防护）+ 缓存
    │   └── tools.py            # react / read_history / fetch_media
    └── tests/
```

依赖方向：`plugin → core`、`adapter → core`，core 不依赖任何一方。两个镜像都 `pip install ./core`，插件目录整体拷进 Hermes 的 plugins。

## 3. 线协议

两段都是 OneBot 11 子集，**不加任何自定义帧**，只加一个连接就绪的 meta event。

```
NapCat  --反向WS(18800)-->  adapter  --WS(18810)-->  plugin
        事件 / action / 响应              同上
```

### 3.1 三类帧

| 帧 | 判别 | 说明 |
| --- | --- | --- |
| 事件 | 有 `post_type` | 只有 `message` 和合成通知会被转发，其余记 debug 丢弃 |
| 请求 | 有 `action` | 插件/适配器 → 对端 |
| 响应 | 有 `echo` | `{status, retcode, reason?, wording?, data?, echo}`，与请求配对 |

判别顺序固定为 **echo → post_type → 丢弃**：响应帧在收帧的同步路径上直接 resolve，**事件帧才进队列**。

### 3.2 就绪帧

```json
{"post_type":"meta_event","meta_event_type":"adapter_ready",
 "adapter":{"version":"0.1.0","config_sha":"9f2c…",
            "chat":{"kind":"group","id":"123456789"}}}
```

插件核对 `config_sha`：不一致记 ERROR 但**继续运行**（拒绝连接会变成静默停机）。`adapter_ready` 在插件每次（重）连时重发。

### 3.3 扩展点

仅两个可选字段，均为增量、可忽略：

- `adapter.internal: true` —— 合成通知事件（戳一戳/进退群），插件据此设 `MessageEvent.internal=True`，绕过去抖。
- `adapter.origin: "poke" | "member_join" | "member_leave" | "member_kick"` —— 只用于日志和排查，不参与判定。

普通消息**不加任何字段**；命令判定与 @ 渲染都在插件侧（见 §4.3）。

## 4. core

### 4.1 schema.py

pydantic v2 模型，`model_config = ConfigDict(extra="allow")`（保留未知字段，便于将来扩展）。

- `MessageSegment(type, data)`；`Message(array|str)` 统一成 list。
- `Event`：`time, self_id, post_type, message_type?, sub_type?, message_id?, group_id?, user_id?, message?, sender?, raw_message?`。合成通知没有 `message_id`，必须允许缺省。
- `adapter?`：可选扩展对象（`internal` / `origin`），未知名原样保留。
- `ApiRequest(action, params, echo)`、`ApiResponse(status, retcode, data, echo, reason?, wording?)`。
- `parse_frame(raw: bytes|str) -> Event | ApiResponse`：JSON 解析失败抛 `SchemaError(kind="json")`；缺关键字段抛 `SchemaError(kind="shape", path=...)`。**不抛裸 ValueError/KeyError。**

### 4.2 segments.py

纯函数：`text(s)`, `at(qq)`, `image(url_or_path)`, `reply(id)`, `file(...)`；`flatten(segs) -> str`（文本原样 + `[@self]`/`[@qq]` + 媒体占位，日志预览也用它）；`mentions_self(segs, self_id) -> bool`（任意位置的 at）；`COMMAND_RE`（`^\s*\[@self\]\s*(/.*)$`，DOTALL）；`has_content(segs) -> bool`（去掉纯空白文本后是否还剩内容——**at 段算内容**）；`format_sender_prefix(name, qq, seq) -> str`（产出 `[昵称(QQ)#序号]`，沿用旧格式）。

QQ 的 `at.qq` 是字符串，`at.qq == "all"` 表示 @全体，必须显式区分。

### 4.3 render.py

`render_event(event, self_id, media: list[MediaResult]) -> str | None`，`media` 按媒体段出现顺序给出每个的落盘结果（`path` / `failed` / `none`），由插件在下载后传入；core 不碰 IO。

1. `adapter.internal` 为真：直接返回文本，不加前缀。
2. 把段扁平化成一段文本：文本段原样（不 strip）、at(self) → `[@self]`、其他 at → `[@qq]`、媒体按序占位。**不加前缀、不处理 `reply`。**
3. 命令：**先要求原始事件里 `mentions_self` 为真**（否则有人手打 `[@self] /reset` 就能伪造命令），再用扁平文本匹配 `^\s*\[@self\]\s*(/.*)$`（DOTALL）。命中就返回捕获组（不含前导空格），不加前缀、不带引用、不处理媒体。触发条件仍由 adapter 判定。
4. 否则组装：群消息再加 `[昵称(QQ)#<real_seq>] ` 前缀（`real_seq` 缺失时用 `message_id`），私聊不加。**引用不写进正文**，由插件另填 `MessageEvent.reply_to_*`（见 §6.2）。
5. 扁平文本为空且没有 at：返回 `None`，adapter 按 `empty` 丢弃。

私聊没有前缀，扁平文本原样就是最终文本，所以私聊里直接打 `/reset` 仍然生效，不要求带 @。

媒体占位（英文标签，编号按类型从 1 起）：

| 类型 | 形态 |
| --- | --- |
| 图片 | `[image1 id=<原生file> cache=<路径>]` / `cache=failed` / `cache=none` |
| 语音 | `[voice1 id=<原生file> cache=…]` |
| 视频 | `[video1 id=<原生file> cache=…]` |
| 文件 | `[file1 name=<文件名> id=<file_id> cache=…]` |
| 合并转发 | `[forward id=<id>]`（不缓存） |

`id` 直接用 NapCat 段里的原生标识（图片/语音/视频取 `data.file`，文件取 `data.file_id`，缺失时退回 `data.file`），**不另造短引用**。`cache` 三态：落盘路径 / `failed`（试过但失败）/ `none`（压根没有 URL 或没尝试）。取回靠工具按 `id` 走 NapCat。

值里可能有空格或 `]`（文件名最常见），一律用双引号包起来：`name="报告 v2.pdf"`；内部的 `"` 和 `\` 做转义。这样占位符永远能按空格切回来。

### 4.4 text.py

`to_plain(text) -> str`：去 ``` 围栏、`**`/`__`/`#` 标题、行内 code 反引号。幂等，默认开启，可配置关闭。

### 4.5 config.py

`load_config(path) -> Config`：TOML → dataclass；`ConfigError` 聚合**全部**错误（不是遇到第一个就抛），启动时一次性打印。`config_sha` 为文件字节的 sha256 前 16 位。

### 4.6 errors.py

```
SchemaError(kind, path, raw_excerpt)
PolicyError(action, reason)      → retcode 200
TransportError(reason)           → retcode 500
UpstreamTimeout(action, secs)    → retcode 400
ConfigError(errors: list[str])   → 仅启动期
```

retcode：`0` 成功、`100` 参数错、`103` 未知 action、`200` 策略拒绝、`400` 上游超时、`500` 连接不可用。

原因码（放进响应的 `reason` 字段，插件据此决定给模型看什么）：`policy_denied`、`target_mismatch`、`not_connected`、`napcat_timeout`、`napcat_failed`、`media_unavailable`。映射集中在一个函数里，两端共用。

### 4.7 notice.py

`render_notice(notice, self_id) -> SyntheticEvent | None`，复刻旧版行为：

| notice | 条件 | 产出文本 | `adapter.origin` |
| --- | --- | --- | --- |
| `notify/poke` | `target_id == self_id` 且 `user_id != self_id` | `[系统] 用户 张三(12345) 戳了戳你` | `poke` |
| `group_increase` | `user_id != self_id` | `[系统] 用户 张三(12345) 加入了群聊` | `member_join` |
| `group_decrease`（`leave`） | `user_id != self_id` | `[系统] 用户 张三(12345) 退出了群聊` | `member_leave` |
| `group_decrease`（`kick`） | `user_id != self_id` | `[系统] 用户 张三(12345) 被管理员移出了群聊` | `member_kick` |

其余情况返回 `None`（丢弃）。缺昵称时退化为 `QQ号`。产出的事件恒为 `post_type="message"`、`message_type="group"`、`group_id` 用绑定值、`message` 为单 text 段、`adapter.internal=true`、无 `message_id`。

## 5. adapter

### 5.1 启动

1. 读 `config.toml`（缺失时用内置默认值），从环境变量取两个 token；`QQBOT_GROUP_ID` /
   `QQBOT_USER_ID` 覆盖 `[chat]` 绑定。缺 token 或最终没有绑定时退出；配置文件不存在
   时适配器会用镜像里的模板自动拷一份。
2. 校验绑定：`group_id` 与 `user_id` 至少一个。
3. 起 aiohttp app，挂两条路由：`/onebot`（NapCat）、`/hermes`（插件）。
4. 注册信号处理，关闭时先拒新连接、再 fail pending、最后关 WS。

### 5.2 NapCatLink

- 只接受一条连接；第二条到达时关掉新的并记 WARNING（多租户靠多条 client entry 指向不同 adapter）。
- 鉴权：query `access_token` 或 `Authorization: Bearer`，常量时间比较。
- 收帧：解析 → 响应帧 resolve future → 事件帧投递到单消费者队列 → 其余 debug 丢弃。
- **单 worker 串行处理**，保证事件顺序。
- `call(action, params, timeout)`：分配 uuid echo、登记 future、发送；超时抛 `UpstreamTimeout`；断线时把该连接所有 pending 置 `TransportError`。
- 断线：日志、清 pending、等待 NapCat 重拨（默认 5s）。

### 5.3 PluginLink

- 只接受一条插件连接（新的顶掉旧的，记 WARNING）。
- 连上即发 `adapter_ready`。
- 收到 `{action, params, echo}`：走 policy 检查 → 转发 NapCatLink → 回 `{status, retcode, reason?, wording?, data?, echo}`。**所有失败都以响应帧返回，不抛给连接层**。
- 无事件时保持空闲；断线即丢弃未处理事件（无重放），并让该连接上未回的动作立即失败。

### 5.4 policy.py

四个纯函数，输入输出都是数据结构，便于表驱动测试：

```python
decide_event(event, binding, window) -> Decision(action="forward"|"drop", reason=str)
check_action(action, params, binding) -> None | PolicyError
apply_binding(action, params, binding) -> dict   # 缺省补目标，显式不同则报错
check_target(action, params, binding) -> None | PolicyError
```

判定表：

| 场景 | 结果 |
| --- | --- |
| 群消息，`group_id` 不匹配 | drop(`other_chat`) |
| 群消息，发送者是 bot 自己 | drop(`self`) |
| 消息没有任何内容（无段，或只有空白段；at 段算内容） | drop(`empty`) |
| 群消息，@ 了 bot（**哪怕没有正文**） | forward(`mention`) |
| 群消息，窗口未激活 | drop(`inactive`) |
| 群消息，窗口激活 | forward(`window`) |
| 私聊，`user_id` 不匹配 | drop(`other_chat`) |
| 私聊，匹配 | forward(`dm`) |
| `notice` 的 `group_id` 不等于绑定群 / 实例只绑了私聊 | drop(`other_chat`) |
| `notice` 且对应开关打开、`render_notice` 有产出 | forward(`notice`)，标 `internal` |
| `notice` 且开关关闭 / 产出为空 | drop(`notice_ignored`) |
| 其他 `post_type`（`meta_event`、`request`） | drop(`unsupported`) |

动作白名单（默认）：

```
send_msg send_group_msg send_private_msg
send_group_forward_msg send_private_forward_msg
upload_group_file upload_private_file
set_msg_emoji_like mark_msg_as_read
get_group_msg_history get_msg get_group_member_info get_group_member_list
get_login_info get_group_info
get_file get_image get_record get_group_file_url get_private_file_url
set_qq_profile set_qq_avatar set_group_card
```

`send_msg` / `send_group_msg` / `send_private_msg` 的 `message` 必须是**数组**；字符串
（CQ 码形态）在 `authorize` 直接拒绝，避免绕过插件手搓 WS 时让 NapCat 解析 `[CQ:...]`。

目标夹：`send_group_msg`/`upload_group_file`/`get_group_msg_history` 的 `group_id`、`send_private_msg`/`upload_private_file` 的 `user_id` 必须等于绑定值；缺失则由 `apply_binding` 补齐。`send_msg` 按 `message_type` 分流：`group` 查 `group_id`、`private` 查 `user_id`，`message_type` 缺失或非二者之一直接拒（`100`）。

`set_group_card` 是唯一能改「别人」外观的动作，因此单独夹：`group_id` 必须等于绑定群，`user_id` 强制填自己的 QQ（从入站事件的 `self_id` 学来），显式传别人直接拒；还不知道自己 QQ 时拒绝执行而不是猜。

### 5.5 window.py

```python
class Window:
    def __init__(self, ttl: float): ...
    def touch(self) -> None
    def active(self) -> bool
```

`touch()` 只在出站成功（retcode 0）之后调用，对所有动作生效：`send_*`、`upload_*`、`set_msg_emoji_like`——旧版就是贴表情也会续窗。私聊不建窗口（不影响判定）。

### 5.6 事件转发

adapter 把**原始 OneBot 事件**原样转发给插件（普通消息不加任何字段），notice 事件则经 `render_notice` 合成一条 text 事件，带 `adapter.internal` 与 `adapter.origin`。渲染、媒体、会话映射全部在插件侧（用 core）。

消息内容原样过线：adapter 只判断 `mentions_self` / 窗口 / `has_content`，不做任何改写、不 strip。命令特判与 @ 渲染都在 `render_event` 里，wire 上不需要额外标记。

### 5.7 seq.py（real_seq → message_id）

旧版靠 `SeqMap` 把模型看到的 `#real_seq` 换回 API 需要的 `message_id`。单会话绑定后这件事很轻：

- 收事件时若带 `real_seq`，记 `real_seq → message_id`（单条 dict，容量上限 2000，超出按 FIFO 淘汰）；
- 出站前对 `set_msg_emoji_like` / `mark_msg_as_read` / `get_msg` 这类动作，把参数里的 `real_seq` 换成 `message_id`；
- 查不到就**原样透传** `real_seq` 当 `message_id`（和旧版一致，兼容 go-cqhttp/Lagrange）。

不需要旧版那张按 scope 分区的大表和 `get_msg` 回填——机器人自己发的消息没有 `real_seq`，也不会有人对它贴表情。

## 6. plugin

### 6.1 连接

`QQPlatform(BasePlatformAdapter)`。注册走 Hermes 0.19 的插件 API（已对源码核对）：

```python
ctx.register_platform(
    name="onebot", label="QQ (NapCat)",
    adapter_factory=build_platform,   # PlatformConfig -> QQPlatform
    check_fn=..., validate_config=..., required_env=[...],
    max_message_length=4500, platform_hint=...,
)
```

`Platform("onebot")` 能成立，是因为 `register_platform` 先把它写进 `platform_registry`，`Platform._missing_` 才放行——所以适配器必须在工厂里构造，不能放在模块导入期。

- 后台任务连 `ws://adapter:18810/hermes`，Bearer token；
- 指数退避重连（1s → 30s），断线期间不缓冲；**断线时把所有挂起的 RPC 立即置失败**，否则 Hermes 要干等到超时；
- 收到 `adapter_ready` 校验 `config_sha`。

### 6.2 入站

`render_event` → `MessageEvent`：

| 字段 | 值 |
| --- | --- |
| `text` | `render_event(...)` |
| `chat_id` | `group:<gid>` 或 `user:<uid>` |
| `chat_type` | `group` / `dm` |
| `sender_id` / `sender_name` | 事件字段 |
| `media_urls` / `media_types` | 图片/语音/视频/文件下载到 `~/.hermes/cache` 后填入 |
| `internal` | 事件带 `adapter.internal` 时为 `True`（合成通知），否则 `False` |
| `reply_to_message_id` / `reply_to_text` / `reply_to_author_*` | 由 `get_msg` 展开的被引消息（旧版同款）；取不到则留空 |

媒体按旧行为处理（等价于原来的 `cache` 模式，不再保留 `passthrough` 开关）：带 URL 的图/语音/视频/文件下载后缓存到 `~/.hermes/cache` 并填 `media_urls`/`media_types`。下载结果（路径 / failed / none）传给 `render_event`，由它写进占位符的 `cache=` 字段；模型据此知道哪些拿到了、哪些要按 `id` 去取。

**引用回复**按旧版展开：事件里有 `reply` 段时，插件经 adapter 调一次 `get_msg`，把被引消息渲染成 `[昵称(QQ)#序号]: 正文` 填进 `MessageEvent.reply_to_text`，同时填 `reply_to_message_id` / `reply_to_author_id` / `reply_to_author_name`。取不到就记 WARNING、照常投递正文（`reply_to_text` 留空）。

下载限制：仅 http/https，禁跳转到私有网段/环回，上限由配置给（默认 20MB）。

### 6.3 出站

实现 `BasePlatformAdapter` 的发送族（按 0.19 实际签名核对）：`send_text` → `send_msg` + text 段；`send_image`/`send_document` → 图片/文件段。发送前先过 `to_plain()`（可关）把 markdown 削平。长文切分沿用旧插件：`MAX_MESSAGE_LENGTH = 4500`，发送前用 `truncate_message()` 切段按序发（Hermes 只提供这个工具函数，切分是我们自己做的）。

`api(action, params)` → `{action, params, echo}`，等响应。失败一律转成失败的 `SendResult`，并把 `wording` 一起带出去（例如「发送失败：NapCat 超时」）——不吞掉原因，也不自己重试。

**超时只由 adapter 判定。** 插件的 RPC 等待必须比 adapter 的动作超时长（留 15–20 秒余量；上传类用 `upload_timeout + 40`）。这消掉的只是“两层超时叠加”造成的那部分重叠：插件先超时、网关重发，而 adapter 那边其实还在等。它消不掉超时本身的歧义——见 §11。

发送结果怎么映射，直接决定 Hermes 会不会重试：

| adapter 失败 | `SendResult` | 结果 |
| --- | --- | --- |
| `napcat_timeout` / `napcat_failed` / `not_connected` | `success=False, retryable=True` | Hermes 重试 2 次，共最多 3 发；耗尽后发一条发送失败提示 |
| `policy_denied` / `target_mismatch` | `success=False, retryable=False`，并覆写 `_send_retry_is_final()` 返回 True | 不重试、不走纯文本兜底，原因直接交回 |

两个坑（都是读 Hermes 0.19 代码确认的）：Hermes 默认**对超时错误不重试**（`_is_timeout_error`），必须靠 `retryable=True` 覆盖这个判断，否则“暴力重试”根本不会发生；另外非 retryable 的失败会掉进 Hermes 的纯文本兜底（`_send_plain_fallback`：内容前面加一段提示横幅再发一次），所以发送类失败要始终 `retryable=True`，策略拒绝则必须用 `_send_retry_is_final=True` 在第一次就短路。

兜底本身没有开关，但它是可覆写方法：插件里把 `_send_plain_fallback()` 覆写成“直接返回失败、不发送”，从结构上关掉这条路径（否则只靠 flag 一致，将来某条分支忘了置位就又冒出来）。覆写处留注释写明原因和对应的 Hermes 版本，升级时复查。

### 6.4 工具

只注册六个：

- `qq_react(real_seq, emoji_id)` → `set_msg_emoji_like`。`emoji_id` 传 QQ 数字编号；也接受
  `ok` / `收到` / `good` / `👌` 这类常见说法，映射到 124。
- `qq_read_history(count)` → `get_group_msg_history`（仅群），**返回原始 JSON**，和旧版一样由模型自己读。
- `qq_fetch_media(id)` → 拿占位符里的 `id` 依次试 `get_file(file_id)` / `get_image(file)` / `get_record(file)`（NapCat 最新文档：文件用 `file_id`，图片/语音用消息里的 `file` 名），拿到 http(s) 地址后下载到缓存目录，返回本地路径、名称、大小。都拿不到就返回明确的失败原因，不猜。群文件接口（`get_group_file_url`）需要 `busid`，对消息段里收到的文件用不上，故不做回退。
- `qq_set_nickname(nickname)` → `set_qq_profile`：改自己的昵称。
- `qq_set_avatar(file)` → `set_qq_avatar`：换头像，URL 最稳（本地路径要 NapCat 也能读到）。
- `qq_set_group_card(card)` → `set_group_card`：改自己的群名片，目标由 adapter 钉死。

其余能力（发文字/图/文件）由 Hermes 自带的发送链路完成，不再注册 100 个工具。

SOUL 里描述：什么时候值得回应一个表情、什么时候不要刷。不写工具参数细节。

另外在 SOUL 的消息格式说明里补一行（自然语言，不列字段）：`[@self]` 是有人 @ 了你，`[@数字]` 是 @ 了别人；`[image1 …]`、`[file1 …]` 是媒体占位，`cache=` 后面是本地路径、`failed` 或 `none`。

## 7. 配置

`/opt/qqbot/config.toml`（adapter 可写、Hermes 只读；不存在时 adapter 从镜像模板拷贝）

```toml
[chat]
# 绑定优先取环境变量 QQBOT_GROUP_ID / QQBOT_USER_ID；这里可留空
# group_id = 123456789
# user_id  = 100001
active_window_seconds = 300

[adapter]
onebot_port = 18800
plugin_port = 18810
call_timeout_seconds = 60
upload_timeout_seconds = 600

[plugin]
media_max_bytes = 20971520
strip_markdown = true
max_message_length = 4500

[notify]
poke = false
member_change = false

[logging]
level = "INFO"
message_preview_chars = 80
```

`QQBOT_ONEBOT_TOKEN` / `QQBOT_PLUGIN_TOKEN` 由 compose 的 env 文件注入进程环境。

规则：不热重载；改完重启。配置和 token 都不进镜像（配置走挂载，token 走 env 文件）。
`config_sha` 只算 `config.toml`。两侧读同一份文件，**校验只针对本进程用到的字段**，别的 section 和未知 key 一律忽略（记 debug）——否则一边加字段，另一边就起不来。

## 8. 错误处理

两条总原则：

1. **边界捕获、内部不吞异常。**
2. **面向模型的一切失败都是硬错误**：带可读原因的失败结果，不重试、不静默降级、不用默认值糊过去。NapCat 本来就不稳，取不到是常态，把原因交给 Hermes 让它决定怎么办。

区分两类“没有继续”：

| 类别 | 例子 | 处理 |
| --- | --- | --- |
| **静默丢弃**（不是错误，没人可回） | 不属于本会话的入站事件、坏帧、未知 `post_type`、插件断线期间的事件 | 记日志后丢弃 |
| **硬错误**（调用方能处理） | 动作失败/超时/无连接、媒体取不回、工具失败、策略拒绝 | 返回带 `wording` 与原因码的结果 |

| 位置 | 处理 |
| --- | --- |
| 收帧解析 | `SchemaError` → WARNING（含 `kind`/`path`/前 200 字节原文），丢弃该帧，循环继续 |
| 未知 `post_type` / `action` | DEBUG，丢弃 |
| 未订阅的事件类型 | DEBUG，丢弃 |
| 事件处理内部异常 | ERROR + 堆栈，丢弃该事件，不退出循环 |
| 出站动作 | `PolicyError`/`UpstreamTimeout`/`TransportError` → 转成 failed 响应帧（`retcode` + `wording` + 原因码），不抛给连接 |
| NapCat 断线 | WARNING + 清 pending（置 `TransportError`） |
| 插件断线 | INFO，事件直接丢（无重放） |
| 下载失败 | WARNING，保留占位符 |
| 配置非法 | 启动期收集全部错误后退出码 2 |
| 未捕获异常 | 顶层 handler 记录后 `sys.exit(1)`，交给容器重启 |

禁止：`except Exception: pass`；用裸 `KeyError`/`ValueError` 表达协议错误；把异常字符串直接回给模型而不带 action 名。

## 9. 日志

统一格式：

```
2026-10-25T12:00:00+08:00 INFO  adapter.relay chat=group:123 msg=4512 action=send_group_msg req=7f3a ok latency=83ms
```

约定：

- 每条动作日志必带 `action`、`req`、结果、耗时；每个事件日志必带 `msg` 和转发/丢弃原因。
- 消息正文只记前 `message_preview_chars` 字，且只在 DEBUG 与 INFO 的 `preview=` 字段出现。
- token、URL query 一律不落日志（连接日志只留 remote host）。
- `exc_info=True` 只在 ERROR 使用。
- 插件侧日志走 Hermes 的 logger（`crupest_qqbot.plugin` 前缀），同样字段。

## 10. 测试

`core`：pytest，覆盖率 ≥ 95%。

- schema：合法 8 类帧、缺字段、类型错、未知字段保留、非法 JSON、超大 frame。
- segments：构造/解析、`at all`、嵌套、`flatten`（`[@self]` 渲染）、`mentions_self`、`has_content`（at-only 为真、纯空白为假）；`COMMAND_RE` 的正反例（含 `[@12345] /x` 不命中）。
- render：群/私聊前缀（`[昵称(QQ)#real_seq]`，缺失退回 `message_id`）、媒体编号顺序、多图、`internal` 不加前缀；at(self) → `[@self]`、其他 at → `[@qq]`、裸 @ 保留为 `[@self]`；消息正文不被 strip；命令正则——`@bot /reset`、`  @bot   /reset`、`@bot\n/reset`、`[reply, at(bot), /reset]` 都返回裸 `/reset`；`/reset`（无 @）、`你好 /reset`、`@别人 /reset`、手打 `[@self] /reset`（事件里没有真 at）都不命中。
- notice：戳自己 / 戳别人 / 自己戳自己、进退群四种文案、缺昵称退化、开关关闭返回 None。
- text：围栏、标题、粗体、幂等。
- config：完整、缺 section、类型错、两个目标都缺、sha 稳定性、错误聚合。
- errors：retcode 与原因码的映射表（每个异常类 → 固定的一对 retcode/reason）。

`adapter`：覆盖率 ≥ 90%。

- `fakes.py`：`FakeNapCat`（接受反向 WS、按 echo 回包、可注入延迟/断线）、`FakePlugin`。
- policy：判定表逐行（含 notice 开关矩阵）、动作白名单逐条、目标夹（缺失补齐 / 显式不同 / 显式相同）、未知 action。
- napcat：响应先于事件、事件先于响应、交错、未知 echo、超时、断线时 pending 全部失败、单连接限制。
- relay：ready 内容、动作转发、失败响应帧、无插件连接时的行为。
- window：ttl 边界、touch 后 active、私聊不建窗。
- seq：命中替换、未命中透传、容量淘汰、非数字 `real_seq` 原样放行。
- 集成：golden frames 回放 → 断言产出的事件序列与决策序列。

`plugin`：覆盖率 ≥ 80%（Hermes 依赖处用 fake）。

- 事件 → `MessageEvent` 字段映射、群/私聊 chat_id、`reply_to_*` 填充（成功 / `get_msg` 失败仍投递）、媒体下载成功/失败/超限/SSRF；占位符三态（`cache=路径` / `failed` / `none`）、编号按类型、`id` 取值优先级（`file` → `file_id`）。
- `fetch_media(id)`：`get_file` 命中、回退到 `get_group_file_url`/`get_private_file_url`、两者都失败、下载失败、返回字段。
- 发送映射：文本、超长切分、图片、文件、失败传播。
- 重连退避序列、config_sha 不一致告警。
- 工具参数校验与错误返回。

门禁：`ruff check` + `pytest`，本地与镜像内各跑一次。

## 11. 已知取舍

| 取舍 | 影响 | 何时补 |
| --- | --- | --- |
| 无重放 | Hermes 重启期间的群消息丢失 | 需要时加 seq+ack+小环 |
| 无去重 | 网关重试可能重复发送一次；换来的是失败不会被伪装成成功。做过内容指纹去重，但去重 TTL 与发送超时是两套独立计时：TTL 长 → 真失败被吸收（消息丢失），TTL 短 → 重试照发（重复），怎么调都只是选一种错法 | 接受，不补 |
| 无排队 | 多人同时说话交给 Hermes 的 busy 合并 | 若出现互相打断再加 |
| 不展开合并转发 | 模型只看到 `[forward id=…]` | 需要时调 `get_forward_msg` |
| 表情反应不校验目标 | 只能靠 `real_seq` 指认，风险低但存在 | 可加白名单 |
| 单会话绑定 | 群和好友需要各一个实例（或同实例两槽位） | 已确认 |
| 媒体占位较长 | 每个媒体多 40–80 字符（`id=` + `cache=`），换来的是一条消息里三种状态都自解释 | 嫌长可只留 `id` |
| 表情 id 要模型自己填 | 工具只收 QQ 的数字 `emoji_id`，模型可能填错或干脆不用 | 以后可加别名表 |
| 切分后部分失败 | 第 2 段失败 → Hermes 整段重发 → 第 1 段重复 | 旧版就这样，暂时接受 |

## 12. 实施顺序

1. **core + fixtures**：schema/segments/render/notice/text/config/errors/logging，全部单测。产出可被两边 import 的包。
2. **adapter**：policy → napcat → relay → app，配合 fakes 逐层测。
3. **plugin**：连接 → 入站 → 出站 → 工具，用 `FakeAdapter`。
4. **镜像与切换**：新 compose 服务、NapCat 加 client entry、先在测试群跑一周再切。

每步的验收：`ruff` + `pytest` 全绿；第 2 步追加"回放旧系统录制的真实帧，决策一致"。
