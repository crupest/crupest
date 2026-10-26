# hermes-chatbot

单会话 QQ 接入：一个群（或一个好友）对应一套 **adapter + Hermes 插件**。
两个进程都说 OneBot 11，adapter 负责与 NapCat 通信并做策略收敛，插件只做
Hermes 侧的事件/媒体/发送结果转换。

设计文档见 [DESIGN.md](DESIGN.md)。

## 结构

```
core/     共享协议（pydantic 模型）、渲染、通知合成、配置解析
adapter/  反向 WS 接 NapCat + WS 服务端接插件；过滤、目标夹、窗口、seq 映射
plugin/   Hermes 平台插件：事件 → MessageEvent、媒体下载、17 个 QQ 工具
config/   配置样例
```

依赖方向：`adapter → core`、`plugin → core`。core 不依赖任何一方。

## 本地检查

```bash
# 在 hermes-chatbot/ 下
python -m pytest          # 全部单元测试
python -m ruff check .
```

测试不启动 NapCat、不连网：需要 IO 的地方都有 fake（`FakeNapCat` / `FakeWS` /
`FakePlugin`）。

## 部署

### adapter

在 `hermes-chatbot/` 下构建（Dockerfile 在 `adapter/`，但上下文需要包含 `core/`）：

```bash
docker build -f adapter/Dockerfile -t crupest-chatbot-adapter .
```

运行时挂载配置：adapter 可写（首次启动会补一份默认配置），Hermes 只读；两者和
NapCat 在同一网络。

```
/opt/chatbot/config.toml   ← 挂载；adapter 可写，缺失时首次启动自动拷贝默认配置
```

会话绑定用环境变量：`CHATBOT_GROUP_ID` / `CHATBOT_USER_ID`（优先于文件里的 `[chat]`）。

token 走环境变量：`CHATBOT_ONEBOT_TOKEN`（NapCat 这条）和 `CHATBOT_PLUGIN_TOKEN`
（Hermes 插件这条）。

NapCat 侧加一条反向 WS（`websocketClients`），URL 指向
`ws://<adapter>:18800/onebot?access_token=<CHATBOT_ONEBOT_TOKEN>`。

### 插件

插件装进 Hermes 镜像，而不是单独容器：

1. `pip install /path/to/core /path/to/plugin`
2. 把 `src/crupest_chatbot_plugin/`（含 `plugin.yaml`）放进 Hermes 的 plugins 目录
3. 设置环境变量：
   - `CHATBOT_CONFIG`：共享配置的绝对路径（默认 `/opt/chatbot/config.toml`）
   - `CHATBOT_ADAPTER_URL`：`ws://<adapter>:18810/hermes`
   - `CHATBOT_ADAPTER_TOKEN`：与 adapter 的 `CHATBOT_PLUGIN_TOKEN` 相同
   - `CHATBOT_CACHE_DIR`（可选）：媒体缓存目录，默认取 `[plugin] cache_dir`（建议放在
     Hermes 与 NapCat 共用的挂载目录里，这样缓存的图能直接回发；插件会定期清理）

平台名仍是 `onebot`（协议名）；工具集和工具名统一用 `chatbot_*`，以后接别的聊天平台
可以直接复用同一套工具名。

### 多租户

一套 adapter+plugin 只服务一个会话。多群/多好友 = 多套容器，共享一个 NapCat：
每个 adapter 在 NapCat 里配一条独立的 `websocketClients`（各自的 URL 和 token）。
每个 adapter 仍然会收到全部事件，靠第一道「会话绑定」闸丢弃别人的。

## 配置

见 [config/config.example.toml](config/config.example.toml)。首次启动会把它拷贝到
`/opt/chatbot/config.toml`（如果不存在）；`group_id`/`user_id` 可以留空，由
`CHATBOT_GROUP_ID` / `CHATBOT_USER_ID` 注入，环境变量优先。两个 token 从环境变量读
（`CHATBOT_ONEBOT_TOKEN` / `CHATBOT_PLUGIN_TOKEN`）。改完需要重启，没有热重载；两边通过
`adapter_ready.config_sha` 互相核对是否跑着同一份配置。

## 行为要点

- 入站：只处理绑定会话；群里需要 @ 或处于活跃窗口，私聊直接放行。通知按
  `[notify]` 开关合成。
- 出站：动作白名单 + 目标夹（`group_id`/`user_id` 只能指向绑定会话）。`message`
  必须是数组段；字符串（CQ 码形态）在 adapter 直接拒绝。改写类动作只接受工具暴露的
  参数子集，多出来的字段（如 emoji 的 `message_id`/`set`、profile 的 `sex`）一律拒绝。
- 断线提示：插件 WS 断开后等 30 秒仍未重连，adapter 会以 bot 身份给绑定会话发一条
  英文提示（10 分钟冷却）。
- 时间戳：`gateway.message_timestamps.enabled` 打开后，用户消息前会带
  `[Mon 2026-10-26 11:49:15 CST]`；`CST` 是 UTC+8（SOUL 里有说明），时间取 OneBot
  事件的 `time`，不是收到时间。
- 媒体：下载并发、流式写盘、缓存到 `[plugin] cache_dir`；这个目录同时挂给 NapCat，所以缓存
  文件可以直接回发。缓存启动时清理一次、之后每 24 小时清理一次：删 7 天前的文件，
  总量超过 1 GB 时再从最旧的删。
- 工具：`chatbot_react`、`chatbot_read_history`（群/私聊）、`chatbot_fetch_media`、
  `chatbot_set_nickname`、`chatbot_set_avatar`、`chatbot_set_group_card`（后三个只能改
  bot 自己）；只读的还有 `chatbot_list_group_members`、`chatbot_get_group_member`、
  `chatbot_get_group_info`、`chatbot_get_user_info`、`chatbot_get_login_info`、
  `chatbot_transcribe_voice`、`chatbot_read_forward`、`chatbot_list_group_files`、
  `chatbot_get_group_file_url`、`chatbot_fetch_group_file`、`chatbot_get_group_file_system_info`。

## 已知取舍

见 DESIGN.md §11：无重放、无去重、无排队、长文切分后部分失败会整段重发。
