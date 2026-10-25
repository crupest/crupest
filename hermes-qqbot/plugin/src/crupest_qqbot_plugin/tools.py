"""QQ-specific tools registered with Hermes.

Everything a normal chat needs (text, images, files) goes through the platform
adapter's send path; these three expose what only OneBot can do.
"""
from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any

from crupest_qqbot_core.errors import QQBotError

from .media import MediaError, MediaFetcher, suffix_for

logger = logging.getLogger(__name__)

#: Hermes toolset name; must match ``platform_toolsets.onebot``.
TOOLSET = "onebot"

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "qq_react",
        "description": "给某条消息贴一个表情回应（不产生新消息）。real_seq 是消息前缀里的 #数字。",
        "parameters": {
            "type": "object",
            "properties": {
                "real_seq": {"type": "integer", "description": "消息前缀 # 后面的群内序号"},
                "emoji_id": {"type": "string", "description": "QQ 表情编号，例如 124"},
            },
            "required": ["real_seq", "emoji_id"],
        },
    },
    {
        "name": "qq_read_history",
        "description": "读取当前群最近的历史消息，返回 NapCat 的原始 JSON。",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "条数，默认 20"},
                "message_seq": {"type": "integer", "description": "起始消息 ID，0 表示最新"},
            },
        },
    },
    {
        "name": "qq_fetch_media",
        "description": "按消息占位符里的 id 取回媒体文件，返回本地路径。图片/语音/文件都可以试。",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "占位符里的 id 值"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "qq_set_nickname",
        "description": "改自己的 QQ 昵称。",
        "parameters": {
            "type": "object",
            "properties": {"nickname": {"type": "string", "description": "新昵称"}},
            "required": ["nickname"],
        },
    },
    {
        "name": "qq_set_avatar",
        "description": "换自己的头像。file 推荐传图片 URL；本地路径要求 NapCat 容器也能读到。",
        "parameters": {
            "type": "object",
            "properties": {"file": {"type": "string", "description": "图片 URL 或路径"}},
            "required": ["file"],
        },
    },
    {
        "name": "qq_set_group_card",
        "description": "改自己在这个群里的群名片（只能改自己）。",
        "parameters": {
            "type": "object",
            "properties": {"card": {"type": "string", "description": "新群名片"}},
            "required": ["card"],
        },
    },
]


def _error(message: object) -> str:
    return f"错误: {message}"


#: A few names the model may use instead of raw QQ emoji ids.
EMOJI_ALIASES = {"ok": "124", "👌": "124", "收到": "124", "good": "124"}


def resolve_emoji_id(value: object) -> str:
    """Map a friendly name to a QQ emoji id; numeric ids pass through."""
    text = str(value or "").strip()
    return EMOJI_ALIASES.get(text.lower(), EMOJI_ALIASES.get(text, text))


async def react(platform: Any, args: dict[str, Any]) -> str:
    try:
        real_seq = int(args["real_seq"])
        emoji_id = resolve_emoji_id(args["emoji_id"])
    except (KeyError, TypeError, ValueError) as exc:
        return _error(f"参数不合法: {exc}")
    if not emoji_id:
        return _error("emoji_id 不能为空")
    try:
        await platform.api("set_msg_emoji_like", {"real_seq": real_seq, "emoji_id": emoji_id})
    except QQBotError as exc:
        return _error(exc)
    return "ok"


async def read_history(platform: Any, args: dict[str, Any]) -> str:
    if getattr(platform, "chat_kind", "dm") != "group":
        return _error("当前会话不是群聊")
    try:
        count = int(args.get("count") or 20)
        message_seq = int(args.get("message_seq") or 0)
    except (TypeError, ValueError) as exc:
        return _error(f"参数不合法: {exc}")
    try:
        data = await platform.api("get_group_msg_history", {"count": count, "message_seq": message_seq})
    except QQBotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def set_nickname(platform: Any, args: dict[str, Any]) -> str:
    nickname = str(args.get("nickname") or "").strip()
    if not nickname:
        return _error("nickname 不能为空")
    try:
        await platform.api("set_qq_profile", {"nickname": nickname})
    except QQBotError as exc:
        return _error(exc)
    return "ok"


async def set_avatar(platform: Any, args: dict[str, Any]) -> str:
    file = str(args.get("file") or "").strip()
    if not file:
        return _error("file 不能为空")
    try:
        await platform.api("set_qq_avatar", {"file": file})
    except QQBotError as exc:
        return _error(exc)
    return "ok"


async def set_group_card(platform: Any, args: dict[str, Any]) -> str:
    card = str(args.get("card") or "").strip()
    if not card:
        return _error("card 不能为空")
    try:
        # group_id / user_id are pinned by the adapter, so only the bot's own card can change.
        await platform.api("set_group_card", {"card": card})
    except QQBotError as exc:
        return _error(exc)
    return "ok"


async def _resolve_url(platform: Any, media_id: str) -> tuple[str, dict[str, Any]]:
    """Try every NapCat action that can turn an id into a download URL."""
    attempts: list[tuple[str, dict[str, Any]]] = [
        ("get_file", {"file_id": media_id}),
        ("get_image", {"file": media_id}),
        ("get_record", {"file": media_id}),
    ]
    for action, params in attempts:
        try:
            data = await platform.api(action, params)
        except QQBotError as exc:
            logger.debug("media resolve %s failed: %s", action, exc)
            continue
        if isinstance(data, dict):
            url = str(data.get("url") or "")
            if url.startswith(("http://", "https://")):
                return url, data
    return "", {}


async def fetch_media(platform: Any, args: dict[str, Any], fetcher: MediaFetcher) -> str:
    media_id = str(args.get("id") or "").strip()
    if not media_id:
        return _error("id 不能为空")
    url, meta = await _resolve_url(platform, media_id)
    if not url:
        return _error(f"无法取回媒体 id={media_id}（NapCat 没有给出下载地址，请让对方重发）")
    try:
        data, content_type = await fetcher.fetch(url)
        path = fetcher.save(data, suffix_for(content_type))
    except MediaError as exc:
        return _error(f"下载失败: {exc}")
    return json.dumps(
        {
            "path": path,
            "size": len(data),
            "name": str(meta.get("file_name") or meta.get("file") or ""),
            "url": url,
        },
        ensure_ascii=False,
    )


async def dispatch(name: str, platform: Any, args: dict[str, Any]) -> str:
    """Run one tool by name against *platform*."""
    if name == "qq_react":
        return await react(platform, args)
    if name == "qq_read_history":
        return await read_history(platform, args)
    if name == "qq_fetch_media":
        fetcher = getattr(platform, "media", None) or getattr(platform, "_media", None)
        if fetcher is None:
            return _error("媒体下载未配置")
        return await fetch_media(platform, args, fetcher)
    if name == "qq_set_nickname":
        return await set_nickname(platform, args)
    if name == "qq_set_avatar":
        return await set_avatar(platform, args)
    if name == "qq_set_group_card":
        return await set_group_card(platform, args)
    return _error(f"未知工具: {name}")


def register_tools(ctx: Any, platform_provider: Callable[[], Any]) -> None:
    """Declare the tools; handlers resolve the adapter lazily (it is built on connect)."""
    register = getattr(ctx, "register_tool", None)
    if not callable(register):
        logger.warning("plugin context has no register_tool; QQ tools unavailable")
        return

    for spec in TOOL_SPECS:
        name = spec["name"]

        async def handler(args: dict[str, Any], _name: str = name, **_: Any) -> str:
            platform = platform_provider()
            if platform is None:
                return _error("适配器尚未初始化")
            return await dispatch(_name, platform, args)

        register(
            name=name,
            toolset=TOOLSET,
            schema={
                "name": name,
                "description": spec["description"],
                "parameters": spec["parameters"],
            },
            handler=handler,
            is_async=True,
            description=spec["description"],
            emoji="🐧",
        )
