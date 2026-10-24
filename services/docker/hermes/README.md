# Hermes + OneBot 三容器部署

```text
napcat  ──ws──▶  onebot-adapter  ──ws──▶  hermes
(QQ)              (:18800/:18810)         (gateway + agent + terminal)
```

- `onebot-adapter`、`hermes` 用同一个 runtime 镜像，两个只读 wrapper 只差
  `ROLE` / `EXPOSE` / `HEALTHCHECK`，共享全部 Docker layer。
- `napcat` 用官方 `mlikiowa/napcat-docker`。
- adapter 和 Hermes 不共享可写文件系统；Hermes 只读取 adapter 写出的
  `handoff/hermes_ws_token`，看不到完整 config。

## 目录

| 容器内路径 | 用途 |
| --- | --- |
| `/opt/hermes` | 应用与 venv |
| `/opt/data` | 唯一数据卷，`HOME` |
| `/opt/data/share` | 出站文件暂存目录；napcat 以只读方式挂同一路径 |
| `/opt/data/.hermes` | Hermes 配置、插件、skills、sessions |
| `/opt/data/.onebot_adapter` | adapter 配置、日志、限流/usage sqlite |

宿主机：

- `data/hermes` → Hermes `/opt/data`
- `data/hermes/share` → napcat `/opt/data/share:ro`（同一路径，NapCat 可直接读取）
- `data/onebot-adapter` → adapter `/opt/data`
- `data/onebot-adapter/handoff` → Hermes `/opt/onebot-adapter:ro`（只有 WS token）
- `data/napcat` → NapCat

从两容器升级时，**必须**把旧的 `data/hermes/.onebot_adapter` 移出 Hermes 卷
（例如备份到仓库外）；留在里面会让 Hermes 重新读到旧 `config.json` 的
`webui_token`。adapter 现在只使用 `data/onebot-adapter`。

## 出站文件

Hermes 和 NapCat 是两个容器，NapCat 只在**它自己的**文件系统上解析
`upload_group_file` / `send_document` 的路径。两边把同一个目录挂在同一个路径上：

- Hermes：`/opt/data/share`（宿主机 `data/hermes/share`，可写）
- napcat：`/opt/data/share`（同一宿主机目录，只读）

要发文件时，Hermes 先把文件写到 `/opt/data/share/...`，再把
`/opt/data/share/...` 传给发送工具；napcat 直接读本地文件上传，不需要临时
起 HTTP 服务。SOUL.md 里已经写明这条约定。

注意：`~/.hermes/cache/` 里的文件（例如别人发来的图片）不在共享目录内，要
转发时需要先复制到 `/opt/data/share/`。

## 构建

两个 target 共享 `frontend`、`adapter-build`、`runtime` 层：

```bash
docker build -f services/docker/hermes/Dockerfile --target adapter -t crupest-onebot-adapter .
docker build -f services/docker/hermes/Dockerfile --target hermes  -t crupest-hermes .
```

compose 会一次构建两个 target；改动 adapter 源码时 BuildKit 会复用已有的
frontend/npm/pip 缓存。

- 基础镜像：`python:3.11-slim-bookworm`，运行时无 Node/Chromium/Xvfb。
- 前端阶段：`node:22-slim` 构建 `services/onebot-adapter/frontend`。
- Python 阶段：`hermes-agent~=0.19.0` + 从 submodule 源码构建的 adapter wheel。
- `setuptools-scm` 看不到 `.git`，用
  `--build-arg ONEBOT_ADAPTER_VERSION=<x.y.z>`，默认 `1.8.0`。
- `APT_MIRROR` 可写在 `data/config`，由 compose 传 build arg。

## 配置

`data/config`（gitignore）：

```dotenv
CRUPEST_DOMAIN=...
CRUPEST_GITHUB=crupest
CRUPEST_ONEBOT_WS_TOKEN=<随机长字符串>
CRUPEST_QQ_ACCOUNT=<QQ号>
CRUPEST_QQ_GROUP_ID=<群号>
CRUPEST_DEEPSEEK_API_KEY=<key>
APT_MIRROR=
```

`gen-tmpl` 生成：

```text
services/generated/envs/adapter.env
services/generated/envs/hermes.env
services/generated/envs/napcat.env
services/generated/docker-compose.yaml
```

| 变量 | 作用 |
| --- | --- |
| `CRUPEST_ONEBOT_WS_TOKEN` | NapCat → adapter 的共享 token；adapter bootstrap 写回 `onebot_ws_token` |
| `CRUPEST_QQ_ACCOUNT` | NapCat `-q` 快速登录账号 |
| `CRUPEST_QQ_GROUP_ID` | 可选；导出 `ONEBOT_HOME_CHANNEL=group:<id>` |
| `CRUPEST_DEEPSEEK_API_KEY` | DeepSeek 聊天、vision 和 web search/fetch 共用 |

NapCat WebUI 的 token 不由 `data/config` 提供：`webui.json` 不存在时 NapCat 会
自动生成一个，保存到 `data/napcat/config/webui.json`；直接读这个文件即可。
已有 `webui.json` 时，删掉它再重启才会重新生成。

adapter 的 `hermes_ws_token` / `webui_token` 由它自己的 `--init-config` 生成。
adapter bootstrap 只把 `hermes_ws_token` 写到 `handoff/hermes_ws_token` 给
Hermes；`webui_token` 留在 adapter 容器内，不暴露给 Hermes。

## 启动

`entrypoint.sh` 根据镜像里的 `ROLE` 分流，`bootstrap.py --role adapter|hermes`
共用：

- adapter：初始化/同步 `config.json`，然后 `exec hermes-onebot-adapter`。
- hermes：安装插件、写 `SOUL.md`/首次配置、读取 adapter token，然后
  `exec hermes gateway run`。
- 每个容器只跑一个进程，靠 Docker `restart` 重启；没有 supervisord。

首次启动会写：

- `group_sessions_per_user: false`
- `display.memory_notifications: off`
- DeepSeek model（有 key 且无 model）
- `agent.image_input_mode: native`
- `web.backend: crupest-deepseek`
- `platform_toolsets.onebot`
- `plugins.entries.onebot.tool_allowlist`
- `GATEWAY_ALLOW_ALL_USERS=true`

模型使用 `deepseek-v4-flash` + `supports_vision: true`：Hermes 0.19 还不认识
`deepseek-flash` 这个名字，而 DeepSeek 目前把 `deepseek-v4-flash` 兼容路由到
V4.1 Flash（多模态）。

镜像内置一个 `crupest-deepseek` provider，`web_search` / `web_extract` 直接调用
DeepSeek 的 `/v1/tools/search` 和 `/v1/tools/fetch`，复用
`DEEPSEEK_API_KEY`；不需要额外的 Firecrawl/Tavily key。

`web_extract` 的 404 不一定是接口写错：DeepSeek Fetch 对目标站的反爬拦截会
返回 `failed to fetch URL`，换一个可抓取的来源即可。

`.onebot_toolsets_initialized` 存在时不重写首次配置。

## 工具与权限

```yaml
platform_toolsets:
  onebot: [file, terminal, cronjob, memory, skills, todo, clarify,
           onebot, session_search, web, vision]
```

OneBot 工具 allowlist：

- 保留：发送/转发、上传、贴表情、戳一戳、点赞、标记已读、`get_*` /
  `fetch_*` / `nc_get_*`。
- 保留自身资料：`onebot_set_avatar`（头像）、`onebot_set_qq_profile`
  （昵称）、`onebot_set_group_card`（自己的群名片）。
- 隐藏：踢人、禁言、设/撤管理员、改他人群名片/群名、退群、处理加群/好友、
  撤回、删文件/公告/精华、改群设置、黑名单写操作。

`set_group_card` 在 adapter 层还会检查目标 `user_id` 必须等于 bot 的
`self_id`，所以只能改自己的群名片；`set_qq_profile` / `set_qq_avatar`
本身没有目标参数，只影响 bot 自己。

这三个工具的默认权限是 `everyone`：任何能让 bot 响应的群成员都可以要求它
改自己的身份。只想让管理员触发时，把对应 `tool_policies` 的
`permission` 改成 `admin`。

adapter 的 `_handle_api_call` 是第二层 action allowlist；Hermes 的 terminal
即使改配置也只能调用白名单 action。automation API 保持
`automation_api_enabled=false`；只有人工能通过 adapter WebUI 打开它，Hermes
拿不到 `webui_token`。

## 验证

```bash
docker compose -f docker-compose.yaml ps
docker compose -f docker-compose.yaml logs --tail 50 onebot-adapter
docker compose -f docker-compose.yaml logs --tail 50 hermes
docker exec crupest-onebot-adapter-1 curl -fsS http://127.0.0.1:18820/api/v1/health
```

adapter 和 hermes 镜像构建后的测试基线：`ruff check .` + `pytest -q`（Linux 下全绿；Windows 本机有 9 个文件权限/路径相关的环境失败，与业务无关）；镜像内 `web_search` / `web_extract` 和 DeepSeek vision 都已手工验证。

## 端口

| 端口 | 位置 | 说明 |
| --- | --- | --- |
| `18800` | adapter | NapCat 反向 WS，仅容器网络 |
| `18810` | adapter | Hermes 插件 WS，仅容器网络 |
| `18820` | adapter | WebUI，只发布 `127.0.0.1` |
| `6099` | napcat | WebUI/扫码，只发布 `127.0.0.1` |

固定 IP：hermes `.8`、napcat `.9`、adapter `.10`。

三个服务的 `mem_limit` 都是 `800m`；`/dev/shm` 分别是 hermes `128m`、
napcat `256m`，adapter 用 Docker 默认 `64m`。shm 是容量上限，不预分配，但
实际占用会算进 `mem_limit`。

adapter WebUI token：

```bash
docker compose exec onebot-adapter \
  python -c 'import json;print(json.load(open("/opt/data/.onebot_adapter/config.json"))["webui_token"])'
```

## 首次部署

```bash
# 1. data/config + chmod 600
# 2. 生成并放到仓库根
deno run -A deno/tools/main.ts service --project-dir . gen-tmpl --no-dry-run
cp services/generated/docker-compose.yaml docker-compose.yaml

# 3. 构建并启动三个容器
docker compose -f docker-compose.yaml build onebot-adapter hermes
docker compose -f docker-compose.yaml up -d onebot-adapter hermes napcat

# 4. SSH 隧道
ssh -N -L 18820:127.0.0.1:18820 -L 6099:127.0.0.1:6099 user@host
```

打开 `http://127.0.0.1:6099`，用 `data/napcat/config/webui.json` 里的
`token` 登录扫码。会话保存在 `data/napcat/qq`；第二次起用 `ACCOUNT` 快速登录。

## 升级与回滚

```bash
cd services/onebot-adapter
git fetch upstream --tags
git switch -c crupest-<new-tag> <new-tag>
git push origin crupest-<new-tag>
cd ../..
git add services/onebot-adapter
git commit -m "chore: bump onebot adapter"

docker compose -f docker-compose.yaml build
docker compose -f docker-compose.yaml up -d onebot-adapter hermes
```

- 每次启动 bootstrap 都会重装/更新插件，不需要手工 `install`。
- 升级前备份 `data/hermes` 与 `data/onebot-adapter`。
- 回滚：子模块切回上一个 commit，重新 build/up；同时保留上一个镜像 digest。

## 常见故障

| 现象 | 排查 |
| --- | --- |
| adapter 不健康 | `docker compose logs onebot-adapter`；18820 health |
| Hermes 插件不连 | `docker compose logs hermes`；`ONEBOT_ADAPTER_URL`；adapter 18810 |
| NapCat 不登录 | 6099 扫码；检查 `data/napcat/qq` 权限；`ACCOUNT` |
| 群消息没反应 | 是否 `@bot`；群是否启用；`self_id`；窗口是否过期 |
| 有事件无回复 | Hermes 是否配置模型/API key；看 provider 错误 |
| 内存高 | `docker stats`；adapter 约 50–100 MiB，hermes 约 80–260 MiB |

## 注意

- `data/config`、`services/generated`、根 `docker-compose.yaml` 含 secret，
  已 gitignore；不要提交。
- 不要公网发布 18800/18810/18820/6099；统一走 SSH 隧道。
- NapCat 是非官方客户端，有封号风险；固定 tag `v4.18.41`，用专用小号。
- adapter 容器无 terminal；Hermes 的 terminal 不能直接改 adapter 代码/配置。
- Hermes 容器内 `hermes` 用户有 passwordless sudo，可自行 `apt`/装包、看进程；
  adapter 镜像没有这条 sudoers，两个角色的权限不共享。
- `/opt/hermes` 保持 root 所有，hermes 用户只读；要改应用/venv 必须用 sudo。
  这去掉了 `chown -R /opt/hermes` 的 310MB 重复层，但也意味着 Hermes 的
  lazy deps/self-update 不能直接写 venv，需要显式 sudo 或构建期预装。
- Hermes 容器没有 Docker socket、没有 host 目录挂载，root 只在本容器内有效；
  compose 额外 `cap_drop: NET_RAW`，避免用 sudo 后抓容器网络包。
- Hermes 只能读到 WS token，拿不到 `webui_token`，不能登录 adapter WebUI。
