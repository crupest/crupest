# Hermes + QQ 三容器部署

```
napcat  ──反向 ws──▶  chatbot-adapter  ──ws──▶  hermes
(QQ)                 (:18800 / :18810)        (gateway + agent + terminal)
```

- `napcat`：QQ 协议端，只负责登录和收发。
- `chatbot-adapter`：单会话适配器（[`hermes-chatbot/`](../../../hermes-chatbot)），负责过滤、目标夹、活跃窗口、动作白名单。
- `hermes`：agent 本体，插件把事件转成 Hermes 的消息，并暴露 21 个 QQ 工具。

## 镜像与构建

```bash
docker compose -f docker-compose.yaml build chatbot-adapter hermes
```

单独构建时注意 Dockerfile 的上下文：

```bash
docker build -f services/docker/hermes/Dockerfile -t crupest-hermes .
docker build -f hermes-chatbot/adapter/Dockerfile -t crupest-chatbot-adapter hermes-chatbot
```

## 配置

适配器和插件读**同一份** `data/chatbot/config.toml`。adapter 可写（首次启动时若文件
不存在，会从镜像里的 `config.example.toml` 自动拷一份），hermes 只读。

会话绑定优先取环境变量：`CHATBOT_GROUP_ID`（模板已从 `CRUPEST_QQ_GROUP_ID` 注入）；
要绑好友，自己在 `envs/chatbot-adapter.env` 里加一行 `CHATBOT_USER_ID=<QQ号>`。环境变量
优先于 `config.toml` 里的 `[chat]`，所以通常不需要手写配置。

```toml
# 自动生成的默认值；一般不用改
[chat]
active_window_seconds = 300
```

完整字段见 `hermes-chatbot/config/config.example.toml`。改完要重启两侧，没有热重载。

token 由 env 文件注入容器（不写进 `config.toml`，也不写进数据卷），
**两条链路各用各的 token**：

| 变量 | 用途 |
| --- | --- |
| `CRUPEST_ONEBOT_WS_TOKEN` | NapCat → adapter；只有这两个容器知道 |
| `CRUPEST_CHATBOT_PLUGIN_TOKEN` | adapter ↔ 插件；Hermes 只知道这一个 |
| `CRUPEST_QQ_ACCOUNT` | NapCat 登录的 QQ 号 |
| `CRUPEST_QQ_GROUP_ID` | 生成 `CHATBOT_HOME_CHANNEL=group:<id>` |

两者必须不同：如果共用一个值，Hermes 就拿到了 OneBot 侧的 token，可以自己连
adapter 的 `/onebot` 伪造事件（绕过所有入站过滤，甚至把 NapCat 顶下线）。生成：

```bash
openssl rand -hex 24
```

新变量加在 `data/config` 里（和 `CRUPEST_ONEBOT_WS_TOKEN` 放在一起）。

对应的 env 文件由模板生成：`envs/chatbot-adapter.env`、`envs/hermes.env`、`envs/napcat.env`。

## 数据目录

| 宿主 | 容器 | 内容 |
| --- | --- | --- |
| `data/chatbot` | adapter `/opt/chatbot`（rw）、hermes `/opt/chatbot:ro` | 共享配置 |
| `data/hermes` | hermes `/opt/data` | Hermes 状态、插件、SOUL、共享目录 |
| `data/hermes/share` | napcat `/opt/data/share:ro` | 出站文件（含媒体缓存 `media/`） |
| `data/napcat` | napcat | QQ 登录态、OneBot 配置 |

`data/hermes/share` 是唯一两边都能读的目录：要发文件先放这里；下载回来的媒体也缓存到
`share/media/`，所以可以直接回发。

## 启动行为

- `chatbot-adapter`：读 `config.toml`（缺失时自动拷贝默认文件），校验失败直接退出
  （退出码 2，错误一次列全）。
- `hermes`：bootstrap 把镜像里内置的 `crupest-chatbot` 插件复制到 `$HERMES_HOME/plugins/`
  并启用；**只有全新卷（`config.yaml` 不存在）**才会写 `group_sessions_per_user=false`、
  `platform_toolsets.onebot`（列表里包含工具集 `chatbot`）、DeepSeek 默认模型等。
  已有卷的配置不会自动修改，升级/改名迁移一律手动。
  `CHATBOT_*` 直接从容器环境继承（来自 `envs/hermes.env`），其中
  `CHATBOT_HOME_CHANNEL=group:<CRUPEST_QQ_GROUP_ID>` 由模板生成；绑定好友而不是群时，
  把 env 里这行改成 `user:<QQ号>`。不再生成 `.entrypoint.env`；旧镜像留下的文件/变量
  由迁移时手动清理。

## 常用操作

```bash
docker compose -f docker-compose.yaml logs --tail 100 chatbot-adapter
docker compose -f docker-compose.yaml logs --tail 100 hermes
docker compose -f docker-compose.yaml restart chatbot-adapter hermes
```

改 token：改 `data/config` 里的 `CRUPEST_ONEBOT_WS_TOKEN` / `CRUPEST_CHATBOT_PLUGIN_TOKEN`，
`gen-tmpl` 后重启 `chatbot-adapter`、`hermes`；OneBot 那个还要在 NapCat 的 OneBot
配置里同步。

## 从旧（qqbot / onebot-adapter）迁移

1. `data/config`：把 `CRUPEST_QQBOT_PLUGIN_TOKEN` 改名为
   `CRUPEST_CHATBOT_PLUGIN_TOKEN`；`CRUPEST_ONEBOT_WS_TOKEN`、`CRUPEST_QQ_ACCOUNT`、
   `CRUPEST_QQ_GROUP_ID`、`CRUPEST_DEEPSEEK_API_KEY` 保持不变。
2. 数据目录改名：`mv data/qqbot data/chatbot`（里面只有自动生成的默认配置）。
3. 删旧插件，避免和新插件抢 `onebot` 平台：
   - `plugins.enabled` 里去掉 `crupest-qqbot`（如果还有 `onebot-platform` 也去掉）；
   - `rm -rf data/hermes/.hermes/plugins/crupest_qqbot`。
4. 改工具集：`config.yaml` 的 `platform_toolsets.onebot` 列表里，把 `onebot` 换成
   `chatbot`（新插件的工具集叫 `chatbot`；已有卷 bootstrap 不会改配置，必须手动编辑）。
5. 手动清理旧镜像的产物：删掉 `data/hermes/.hermes/.entrypoint.env`，并清掉
   `data/hermes/.hermes/.env` 里的 `QQBOT_*` / `CHATBOT_*` / `ONEBOT_ADAPTER_*` 行。
6. `bash services/manage gen-tmpl --no-dry-run`，然后重建/拉取镜像并 `docker compose up -d`。
7. NapCat 不用改：`chatbot-adapter` 保留了 `onebot-adapter` 的网络别名，旧配置里的
   `ws://onebot-adapter:18800/onebot?...` 继续可用。
8. `SOUL.md` 会自动同步成镜像里的版本，旧文件备份为 `SOUL.md.bak.<timestamp>`。
9. 开启消息时间戳（已有卷）：`config.yaml` 里加
   ```yaml
   gateway:
     message_timestamps:
       enabled: true
   ```
   新卷由 bootstrap 自动写入；容器 `TZ` / `HERMES_TIMEZONE` 都是 `Asia/Shanghai`，前缀里的 `CST` 指 UTC+8。

旧的 `data/onebot-adapter` 目录和旧容器可以随后删掉。

## 排查

| 现象 | 先看 |
| --- | --- |
| adapter 起不来 | `docker compose logs chatbot-adapter`；配置是否合法、`data/chatbot` 是否可写 |
| NapCat 连不上 adapter | NapCat 日志里的 `ONEBOT_URL`；token 是否一致 |
| Hermes 侧无回复 | `docker compose logs hermes`；插件是否启用；`CHATBOT_ADAPTER_URL` |
| 发文件失败 | 文件是否在 `data/hermes/share` 下；路径是否两边一致 |
| 图片只显示占位符 | 占位符里的 `cache=failed/none`；NapCat 是否给出可下载 URL |
