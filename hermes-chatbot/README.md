# hermes-chatbot

单会话 QQ 接入：一个群或好友对应一套 adapter + Hermes 插件；多会话就是多套实例，
共享一个 NapCat。

- `adapter`：唯一接 NapCat 的进程。负责会话绑定、入站过滤、出站目标固定、动作白名单，
  以及必要的 OneBot 转换。
- `plugin`：Hermes 平台适配器。把事件转成 `MessageEvent`，下载媒体，注册 `chatbot_*` 工具。
- `core`：纯协议模型、渲染、配置与校验；不做 IO。

设计见 [DESIGN.md](DESIGN.md)，部署见 [services/docker/hermes](../services/docker/hermes/README.md)。

## 结构

```
core/     共享协议模型、渲染、配置
adapter/  NapCat 反向 WS + 插件 WS 服务端
plugin/   Hermes 平台适配器 + QQ 工具
config/   配置样例
```

依赖方向：`adapter → core`、`plugin → core`。

## 开发

在 `hermes-chatbot/` 下，先装 workspace（Python 3.14）：

```bash
uv sync
uv run pytest
uv run ruff check .
```

测试使用 fake，不启动 NapCat，也不连网。

## 关键约定

- 平台名固定为 `onebot`，工具名统一用 `chatbot_*`。
- 配置只有一份 `/opt/chatbot/config.toml`；adapter 可写，Hermes 只读；token 只走环境变量。
- 纯文字直接回复；`@`、QQ 表情、骰子/猜拳、引用只通过 `chatbot_send_message` 发送。
- `MEDIA:` 图片/文件继续走 Hermes 自带链路，插件不另造发送通道。
- 工具契约在 tool description；SOUL 只写行为时机和规则，不写平台格式或工具参数。
