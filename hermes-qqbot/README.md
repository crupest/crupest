# hermes-qqbot

单会话 QQ 接入：一个群（或一个好友）对应一套 **adapter + Hermes 插件**。
两个进程都说 OneBot 11，adapter 负责与 NapCat 通信并做策略收敛，插件只做
Hermes 侧的事件/媒体/发送结果转换。

设计文档见 [DESIGN.md](DESIGN.md)。

## 结构

```
core/     共享协议（pydantic 模型）、渲染、通知合成、配置解析
adapter/  反向 WS 接 NapCat + WS 服务端接插件；过滤、目标夹、窗口、seq 映射
plugin/   Hermes 平台插件：事件 → MessageEvent、媒体下载、六个 QQ 工具
config/   配置样例
```

依赖方向：`adapter → core`、`plugin → core`。core 不依赖任何一方。

## 本地检查

```bash
# 在 hermes-qqbot/ 下
python -m pytest          # 全部单元测试
python -m ruff check .
```

测试不启动 NapCat、不连网：需要 IO 的地方都有 fake（`FakeNapCat` / `FakeWS` /
`FakePlugin`）。

## 部署

### adapter

在 `hermes-qqbot/` 下构建（Dockerfile 在 `adapter/`，但上下文需要包含 `core/`）：

```bash
docker build -f adapter/Dockerfile -t crupest-qqbot-adapter .
```

运行时挂载配置：adapter 可写（首次启动会补一份默认配置），Hermes 只读；两者和
NapCat 在同一网络。

```
/opt/qqbot/config.toml   ← 挂载；adapter 可写，缺失时首次启动自动拷贝默认配置
```

会话绑定用环境变量：`QQBOT_GROUP_ID` / `QQBOT_USER_ID`（优先于文件里的 `[chat]`）。

token 走环境变量：`QQBOT_ONEBOT_TOKEN`（NapCat 这条）和 `QQBOT_PLUGIN_TOKEN`
（Hermes 插件这条）。

NapCat 侧加一条反向 WS（`websocketClients`），URL 指向
`ws://<adapter>:18800/onebot?access_token=<QQBOT_ONEBOT_TOKEN>`。

### 插件

插件装进 Hermes 镜像，而不是单独容器：

1. `pip install /path/to/core /path/to/plugin`
2. 把 `src/crupest_qqbot_plugin/`（含 `plugin.yaml`）放进 Hermes 的 plugins 目录
3. 设置环境变量：
   - `QQBOT_CONFIG`：共享配置的绝对路径（默认 `/opt/qqbot/config.toml`）
   - `QQBOT_ADAPTER_URL`：`ws://<adapter>:18810/hermes`
   - `QQBOT_ADAPTER_TOKEN`：与 adapter 的 `QQBOT_PLUGIN_TOKEN` 相同
   - `QQBOT_CACHE_DIR`（可选）：媒体缓存目录，默认取 `[plugin] cache_dir`（建议放在
     Hermes 与 NapCat 共用的挂载目录里，这样缓存的图能直接回发，也能被 cron 清理）

平台名沿用 `onebot`，这样 Hermes 里已有的 toolset 配置不用改。

### 多租户

一套 adapter+plugin 只服务一个会话。多群/多好友 = 多套容器，共享一个 NapCat：
每个 adapter 在 NapCat 里配一条独立的 `websocketClients`（各自的 URL 和 token）。
每个 adapter 仍然会收到全部事件，靠第一道「会话绑定」闸丢弃别人的。

## 配置

见 [config/config.example.toml](config/config.example.toml)。首次启动会把它拷贝到
`/opt/qqbot/config.toml`（如果不存在）；`group_id`/`user_id` 可以留空，由
`QQBOT_GROUP_ID` / `QQBOT_USER_ID` 注入，环境变量优先。两个 token 从环境变量读
（`QQBOT_ONEBOT_TOKEN` / `QQBOT_PLUGIN_TOKEN`）。改完需要重启，没有热重载；两边通过
`adapter_ready.config_sha` 互相核对是否跑着同一份配置。

## 行为要点

- 入站：只处理绑定会话；群里需要 @ 或处于活跃窗口，私聊直接放行。通知按
  `[notify]` 开关合成。
- 出站：动作白名单 + 目标夹（`group_id`/`user_id` 只能指向绑定会话）。`message`
  必须是数组段；字符串（CQ 码形态）在 adapter 直接拒绝。
- 媒体：下载并发、缓存到 `[plugin] cache_dir`；这个目录同时挂给 NapCat，所以缓存
  文件可以直接回发。
- 工具：`qq_react`、`qq_read_history`、`qq_fetch_media`、`qq_set_nickname`、
  `qq_set_avatar`、`qq_set_group_card`（后三个只能改 bot 自己）。

## 已知取舍

见 DESIGN.md §11：无重放、无去重、无排队、长文切分后部分失败会整段重发。
