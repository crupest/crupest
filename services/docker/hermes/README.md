# Hermes + QQ 三容器部署

```
napcat  ──反向 WS──▶  chatbot-adapter  ──WS──▶  hermes
(QQ)                 (:18800 / :18810)        (gateway + agent)
```

Hermes 镜像从 `v0.22.7` 源码构建，Python 3.14 + uv，并带 Node.js 26 LTS / npm；
不包含浏览器、TUI 和桌面组件。运行时保留 uv 和 Node，方便在容器内排查、安装插件
或运行 `npx` 类 MCP server。`connections` toolset 保留，用于托管应用连接和 MCP 管理。

- `napcat`：QQ 协议端，只负责登录和收发。
- `chatbot-adapter`：单会话适配器（[hermes-chatbot](../../../hermes-chatbot)），负责过滤、
  目标固定、活跃窗口和动作白名单。
- `hermes`：agent 本体；插件把事件转成 Hermes 消息，并注册 `chatbot_*` 工具。

## 配置

两侧读同一份 `data/chatbot/config.toml`。adapter 可写，Hermes 只读；文件不存在时
adapter 会从镜像里的样例补一份。

会话绑定优先取环境变量：`CHATBOT_GROUP_ID` 由模板从 `CRUPEST_QQ_GROUP_ID` 注入；
绑好友时在 `envs/chatbot-adapter.env` 加 `CHATBOT_USER_ID=<QQ号>`。环境变量优先于
配置文件。完整字段见 [config.example.toml](../../../hermes-chatbot/config/config.example.toml)。

token 由 env 文件注入，不进 `config.toml`，也不进数据卷：

| 变量 | 用途 |
| --- | --- |
| `CRUPEST_ONEBOT_WS_TOKEN` | NapCat → adapter |
| `CRUPEST_CHATBOT_PLUGIN_TOKEN` | adapter ↔ 插件 |
| `CRUPEST_QQ_ACCOUNT` | NapCat 登录的 QQ 号 |
| `CRUPEST_QQ_GROUP_ID` | 生成 `CHATBOT_HOME_CHANNEL=group:<id>` |

两个 token 必须不同。共用时 Hermes 会拿到 OneBot 侧的 token，可以直连 adapter 的
`/onebot` 伪造事件。生成用 `openssl rand -hex 24`，加在 `data/config`，再生成
`envs/chatbot-adapter.env`、`envs/hermes.env`、`envs/napcat.env`。

配置不热重载，改完重启两侧。

## 从 0.19 迁移

启动时 bootstrap 自动完成：

- `config.yaml` 迁移（当前从 33 到 52），备份到 `$HERMES_HOME/backups/config/`
- 同步 SOUL、复制并启用 `crupest-chatbot`
- 关闭 `sessions.auto_prune`
- 保留 `connections` toolset

手动只做数据备份、停服、构建和启动验收。`envs/hermes.env` 已包含
`GATEWAY_ALLOW_ALL_USERS=true`；旧卷 `$HERMES_HOME/.env` 里的同名行需要删掉，
避免它覆盖容器环境。

## 数据目录

| 宿主 | 容器 | 内容 |
| --- | --- | --- |
| `data/chatbot` | adapter `/opt/chatbot`（rw）、hermes `/opt/chatbot:ro` | 共享配置 |
| `data/hermes` | hermes `/opt/data` | Hermes 状态、插件、SOUL、共享目录 |
| `data/hermes/share` | napcat `/opt/data/share:ro` | 出站文件、媒体缓存 |
| `data/napcat` | napcat | QQ 登录态、OneBot 配置 |

`data/hermes/share` 是唯一两边都能读的目录：发文件放这里；下载的媒体缓存到
`share/media/`，可以直接回发。

## 启动

- `chatbot-adapter`：读配置，缺失时自动拷贝默认文件；校验失败退出码 2，错误一次列全。
- `hermes`：bootstrap 同步 SOUL、复制并启用 `crupest-chatbot`；只有全新卷写
  首次默认配置，已有卷只做 Hermes 配置迁移（带备份），并关闭
  `sessions.auto_prune`。
- `CHATBOT_*` 从 `envs/hermes.env` 继承；默认 `CHATBOT_HOME_CHANNEL=group:<QQ群号>`，
  绑好友时改成 `user:<QQ号>`。

## 排查

| 现象 | 先看 |
| --- | --- |
| adapter 起不来 | `docker compose logs chatbot-adapter`；配置是否合法、`data/chatbot` 是否可写 |
| NapCat 连不上 adapter | NapCat 的 `ONEBOT_URL`；token 是否一致 |
| Hermes 无回复 | `docker compose logs hermes`；插件是否启用；`CHATBOT_ADAPTER_URL` |
| 发文件失败 | 文件是否在 `data/hermes/share` 下；路径是否两边一致 |
| 图片只有占位符 | 占位符里的 `cache=failed/none`；NapCat 是否给出可下载 URL |
