"""QQ-specific tools registered with Hermes.

Everything a normal chat needs (text, images, files) goes through the platform
adapter's send path; these tools expose what only OneBot can do.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from typing import Any

from crupest_chatbot_core.errors import ChatbotError
from crupest_chatbot_core.richtext import RichTextError

from .media import MediaError, MediaFetcher

logger = logging.getLogger(__name__)

#: Hermes toolset name; platform-agnostic so other chat adapters can reuse it.
TOOLSET = "chatbot"

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "name": "chatbot_react",
        "description": "给某条消息贴一个表情回应（不产生新消息）。real_seq 是消息前缀里的 #数字。",
        "parameters": {
            "type": "object",
            "properties": {
                "real_seq": {"type": "integer", "description": "消息前缀 # 后面的群内序号"},
                "emoji_id": {"type": "string", "description": "QQ 表情编号，例如 124；不确定可传 ok（映射到 👌）"},
            },
            "required": ["real_seq", "emoji_id"],
        },
    },
    {
        "name": "chatbot_send_message",
        "description": (
            "发送一条带特殊内容的消息：@人、QQ 表情、骰子/猜拳、引用。\n"
            "segments 按顺序拼成一条消息，最多 20 段，文本合计不超过 4500 字。段类型：\n"
            "- text：text 填文本；\n"
            "- at：qq 填群成员 QQ 号或 all；all 需要机器人是群管理员，且请谨慎使用；\n"
            "- face：name 填 QQ faceText，例如 微笑、得意、敲敲、汪汪；\n"
            "- dice / rps：无字段，发骰子 / 猜拳；\n"
            "- reply：seq 填消息前缀 # 后的序号（私聊用消息 ID），且必须放在第一段。\n"
            "face 的 name 用 faceText（不带 /）；QQ 可能把单发的一个表情显示为大表情，不能指定大小。\n"
            "发送成功后本轮只回复 NO_REPLY，不要再输出正文。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "segments": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "description": "按顺序发送的消息段；文本合计不超过 4500 字",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["text", "at", "face", "dice", "rps", "reply"],
                            },
                            "text": {"type": "string", "description": "text 段：文本内容"},
                            "qq": {"type": "string", "description": "at 段：QQ 号或 all"},
                            "name": {"type": "string", "description": "face 段：QQ faceText，如 微笑"},
                            "seq": {"type": "integer", "description": "reply 段：消息前缀 # 后的序号"},
                        },
                        "required": ["type"],
                    },
                },
            },
            "required": ["segments"],
        },
    },
    {
        "name": "chatbot_poke",
        "description": (
            "戳一戳群成员。不传 user_id 就戳刚发消息的人；群聊里可以指定任意群成员，"
            "私聊只能戳绑定的好友。谨慎使用，别连续戳、别刷屏。"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "要戳的 QQ 号；不传则戳刚发消息的人"},
            },
        },
    },
    {
        "name": "chatbot_send_forward",
        "description": "把当前会话里的几条消息合并转发。real_seqs 是消息前缀里的 #数字（私聊用消息 ID），一次最多 20 条。",
        "parameters": {
            "type": "object",
            "properties": {
                "real_seqs": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "minItems": 1,
                    "maxItems": 20,
                    "description": "要转发的消息序号列表",
                },
            },
            "required": ["real_seqs"],
        },
    },
    {
        "name": "chatbot_upload_group_file",
        "description": "把本机共享目录（/opt/data/share）里的文件上传到本群群文件。path 必须是该目录下的文件。",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径（相对或绝对，最终必须在共享目录内）"},
                "name": {"type": "string", "description": "显示的文件名，默认用原文件名"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "chatbot_read_history",
        "description": "读取当前会话最近的历史消息（群聊/私聊都支持），返回 NapCat 的原始 JSON。",
        "parameters": {
            "type": "object",
            "properties": {
                "count": {"type": "integer", "description": "条数，默认 20"},
                "message_seq": {"type": "integer", "description": "起始消息 ID，0 表示最新"},
            },
        },
    },
    {
        "name": "chatbot_fetch_media",
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
        "name": "chatbot_set_nickname",
        "description": "改自己的 QQ 昵称。",
        "parameters": {
            "type": "object",
            "properties": {"nickname": {"type": "string", "description": "新昵称"}},
            "required": ["nickname"],
        },
    },
    {
        "name": "chatbot_set_avatar",
        "description": "换自己的头像。file 推荐传图片 URL；本地路径要求 NapCat 容器也能读到。",
        "parameters": {
            "type": "object",
            "properties": {"file": {"type": "string", "description": "图片 URL 或路径"}},
            "required": ["file"],
        },
    },
    {
        "name": "chatbot_set_group_card",
        "description": "改自己在这个群里的群名片（只能改自己）。",
        "parameters": {
            "type": "object",
            "properties": {"card": {"type": "string", "description": "新群名片"}},
            "required": ["card"],
        },
    },
    {
        "name": "chatbot_list_group_members",
        "description": "列出本群成员，返回 JSON 数组（user_id、昵称、群名片、角色等）。人多的群可传 limit 截断。",
        "parameters": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "description": "最多返回多少个成员，默认 100；0 表示全部"},
            },
        },
    },
    {
        "name": "chatbot_get_group_member",
        "description": "查本群某个成员的资料（群名片、昵称、角色、入群时间等），返回 JSON。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "成员的 QQ 号"},
                "no_cache": {"type": "boolean", "description": "跳过缓存，默认 false"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "chatbot_get_group_info",
        "description": "查本群的信息（群名、人数、公告等），返回 JSON。",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "chatbot_get_user_info",
        "description": "查任意 QQ 用户的公开资料（昵称、性别、年龄等），返回 JSON；不要求是群成员。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "integer", "description": "QQ 号"},
                "no_cache": {"type": "boolean", "description": "跳过缓存，默认 false"},
            },
            "required": ["user_id"],
        },
    },
    {
        "name": "chatbot_get_login_info",
        "description": "查 bot 自己登录的 QQ 号与昵称。",
        "parameters": {"type": "object", "properties": {}},
    },
    {
        "name": "chatbot_transcribe_voice",
        "description": "把一条语音转成文字。real_seq 是消息前缀 # 后的序号；从历史 JSON 里拿到的消息可用 message_id。",
        "parameters": {
            "type": "object",
            "properties": {
                "real_seq": {"type": "integer", "description": "消息前缀 # 后面的群内序号"},
                "message_id": {"type": "string", "description": "消息 ID（与 real_seq 二选一）"},
            },
        },
    },
    {
        "name": "chatbot_read_forward",
        "description": "读取合并转发的内容。id 是占位符 [forward id=...] 里的值。",
        "parameters": {
            "type": "object",
            "properties": {
                "id": {"type": "string", "description": "合并转发的 id"},
            },
            "required": ["id"],
        },
    },
    {
        "name": "chatbot_list_group_files",
        "description": "列出群文件。不传 folder_id 时列根目录；返回 files / folders。",
        "parameters": {
            "type": "object",
            "properties": {
                "folder_id": {"type": "string", "description": "文件夹 ID，留空表示根目录"},
                "count": {"type": "integer", "description": "最多返回多少个，默认 50"},
            },
        },
    },
    {
        "name": "chatbot_get_group_file_url",
        "description": "取群文件的下载链接。file_id 来自群文件列表。",
        "parameters": {
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "群文件 ID"}},
            "required": ["file_id"],
        },
    },
    {
        "name": "chatbot_fetch_group_file",
        "description": "把群文件下载到本地缓存并返回路径；可以再用 MEDIA: 发给别人。",
        "parameters": {
            "type": "object",
            "properties": {"file_id": {"type": "string", "description": "群文件 ID"}},
            "required": ["file_id"],
        },
    },
    {
        "name": "chatbot_get_group_file_system_info",
        "description": "查群文件系统的容量和数量。",
        "parameters": {"type": "object", "properties": {}},
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
    except ChatbotError as exc:
        return _error(exc)
    return "ok"


def _group_only(platform: Any) -> str | None:
    if getattr(platform, "chat_kind", "dm") != "group":
        return "当前会话不是群聊"
    return None


async def read_history(platform: Any, args: dict[str, Any]) -> str:
    try:
        count = int(args.get("count") or 20)
        message_seq = int(args.get("message_seq") or 0)
    except (TypeError, ValueError) as exc:
        return _error(f"参数不合法: {exc}")
    action = "get_group_msg_history" if getattr(platform, "chat_kind", "dm") == "group" else "get_friend_msg_history"
    try:
        data = await platform.api(action, {"count": count, "message_seq": message_seq})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def set_nickname(platform: Any, args: dict[str, Any]) -> str:
    nickname = str(args.get("nickname") or "").strip()
    if not nickname:
        return _error("nickname 不能为空")
    try:
        await platform.api("set_qq_profile", {"nickname": nickname})
    except ChatbotError as exc:
        return _error(exc)
    return "ok"


async def set_avatar(platform: Any, args: dict[str, Any]) -> str:
    file = str(args.get("file") or "").strip()
    if not file:
        return _error("file 不能为空")
    try:
        await platform.api("set_qq_avatar", {"file": file})
    except ChatbotError as exc:
        return _error(exc)
    return "ok"


async def set_group_card(platform: Any, args: dict[str, Any]) -> str:
    card = str(args.get("card") or "").strip()
    if not card:
        return _error("card 不能为空")
    try:
        # group_id / user_id are pinned by the adapter, so only the bot's own card can change.
        await platform.api("set_group_card", {"card": card})
    except ChatbotError as exc:
        return _error(exc)
    return "ok"


async def list_group_members(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    try:
        limit = int(args.get("limit", 100))
    except (TypeError, ValueError):
        return _error("limit 必须是整数")
    try:
        data = await platform.api("get_group_member_list", {})
    except ChatbotError as exc:
        return _error(exc)
    if isinstance(data, list) and limit > 0:
        data = data[:limit]
    return json.dumps(data, ensure_ascii=False)


async def get_group_member(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    try:
        user_id = int(args["user_id"])
    except (KeyError, TypeError, ValueError):
        return _error("user_id 必须是 QQ 号")
    params: dict[str, Any] = {"user_id": user_id}
    if "no_cache" in args:
        params["no_cache"] = bool(args["no_cache"])
    try:
        data = await platform.api("get_group_member_info", params)
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def get_group_info(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    try:
        data = await platform.api("get_group_info", {})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def get_user_info(platform: Any, args: dict[str, Any]) -> str:
    try:
        user_id = int(args["user_id"])
    except (KeyError, TypeError, ValueError):
        return _error("user_id 必须是 QQ 号")
    # NapCat marks no_cache required for get_stranger_info.
    params: dict[str, Any] = {"user_id": user_id, "no_cache": bool(args.get("no_cache", False))}
    try:
        data = await platform.api("get_stranger_info", params)
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def get_login_info(platform: Any, args: dict[str, Any]) -> str:
    try:
        data = await platform.api("get_login_info", {})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def transcribe_voice(platform: Any, args: dict[str, Any]) -> str:
    params: dict[str, Any] = {}
    if args.get("real_seq") not in (None, ""):
        try:
            params["real_seq"] = int(args["real_seq"])
        except (TypeError, ValueError):
            return _error("real_seq 必须是整数")
    elif args.get("message_id") not in (None, ""):
        params["message_id"] = str(args["message_id"])
    else:
        return _error("需要 real_seq 或 message_id")

    # NapCat downloads the PTT element lazily; reading the message first makes
    # the first transcription attempt much more reliable. Failure is harmless.
    try:
        await platform.api("get_msg", params)
    except ChatbotError:
        pass

    last_error: ChatbotError | None = None
    for attempt in range(2):
        try:
            data = await platform.api("fetch_ptt_text", params)
        except ChatbotError as exc:
            last_error = exc
        else:
            text = str(data.get("text") or "") if isinstance(data, dict) else ""
            if text:
                return text
            last_error = ChatbotError("没有识别出文字")
        if attempt == 0:
            await asyncio.sleep(1.0)
    return _error(last_error or "没有识别出文字")


async def read_forward(platform: Any, args: dict[str, Any]) -> str:
    forward_id = str(args.get("id") or "").strip()
    if not forward_id:
        return _error("id 不能为空")
    try:
        data = await platform.api("get_forward_msg", {"id": forward_id})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def list_group_files(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    try:
        count = int(args.get("count", 50))
    except (TypeError, ValueError):
        return _error("count 必须是整数")
    folder_id = str(args.get("folder_id") or "").strip()
    if folder_id:
        action = "get_group_files_by_folder"
        params: dict[str, Any] = {"folder_id": folder_id, "file_count": count}
    else:
        action = "get_group_root_files"
        params = {"file_count": count}
    try:
        data = await platform.api(action, params)
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def get_group_file_url(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    file_id = str(args.get("file_id") or "").strip()
    if not file_id:
        return _error("file_id 不能为空")
    try:
        data = await platform.api("get_group_file_url", {"file_id": file_id})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def fetch_group_file(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    file_id = str(args.get("file_id") or "").strip()
    if not file_id:
        return _error("file_id 不能为空")
    fetcher = getattr(platform, "media", None) or getattr(platform, "_media", None)
    if fetcher is None:
        return _error("媒体下载未配置")
    try:
        data = await platform.api("get_group_file_url", {"file_id": file_id})
    except ChatbotError as exc:
        return _error(exc)
    url = str(data.get("url") or "") if isinstance(data, dict) else ""
    if not url:
        return _error("NapCat 没有给出下载链接")
    try:
        path, _content_type, size = await fetcher.fetch_to_cache(url)
    except MediaError as exc:
        return _error(f"下载失败: {exc}")
    return json.dumps({"path": path, "size": size, "url": url}, ensure_ascii=False)


async def get_group_file_system_info(platform: Any, args: dict[str, Any]) -> str:
    if (problem := _group_only(platform)) is not None:
        return _error(problem)
    try:
        data = await platform.api("get_group_file_system_info", {})
    except ChatbotError as exc:
        return _error(exc)
    return json.dumps(data, ensure_ascii=False)


async def _resolve_url(platform: Any, media_id: str) -> tuple[str, dict[str, Any]]:
    """Try every NapCat action that can turn an id into a download URL."""
    attempts: list[tuple[str, dict[str, Any]]] = [
        ("get_file", {"file_id": media_id}),
        ("get_image", {"file": media_id}),
        ("get_record", {"file": media_id, "out_format": "mp3"}),
    ]
    for action, params in attempts:
        try:
            data = await platform.api(action, params)
        except ChatbotError as exc:
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
        path, _content_type, size = await fetcher.fetch_to_cache(url)
    except MediaError as exc:
        return _error(f"下载失败: {exc}")
    return json.dumps(
        {
            "path": path,
            "size": size,
            "name": str(meta.get("file_name") or meta.get("file") or ""),
            "url": url,
        },
        ensure_ascii=False,
    )


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False)


async def send_message(platform: Any, args: dict[str, Any]) -> str:
    items = args.get("segments")
    if not isinstance(items, list) or not items:
        return _json({
            "ok": False,
            "error": "segments 必须是非空数组",
            "hint": "按工具 schema 传 [{type, ...}]；纯文字请直接回复",
        })
    try:
        result = await platform.send_rich(items)
    except RichTextError as exc:
        return _json({
            "ok": False,
            "error": str(exc),
            "hint": "按提示修正 segments 后重试；纯文字请直接回复",
        })
    except ChatbotError as exc:
        return _json({
            "ok": False,
            "error": str(exc),
            "hint": "消息未发送；修正后重试，或改用纯文本回复",
        })
    if result.success:
        return _json({"ok": True, "message_id": result.message_id or ""})
    return _json({
        "ok": False,
        "error": result.error or "发送失败",
        "hint": "消息未发送；修正后重试，或改用纯文本回复",
    })


async def poke(platform: Any, args: dict[str, Any]) -> str:
    raw = args.get("user_id")
    target: str | None = None
    if raw not in (None, ""):
        if isinstance(raw, bool) or not isinstance(raw, (int, str)):
            return _error("user_id 必须是 QQ 号")
        target = str(raw).strip()
        if not target.isdigit():
            return _error("user_id 必须是 QQ 号")
    try:
        result = await platform.poke(target)
    except ChatbotError as exc:
        return _error(exc)
    return "ok" if result.success else _error(result.error or "戳一戳失败")


async def send_forward(platform: Any, args: dict[str, Any]) -> str:
    raw = args.get("real_seqs")
    if not isinstance(raw, list) or not raw:
        return _error("real_seqs 不能为空")
    seqs: list[int] = []
    for value in raw:
        if isinstance(value, bool):
            return _error(f"real_seqs 必须是整数: {value!r}")
        if isinstance(value, str) and value.strip().isdigit():
            seqs.append(int(value.strip()))
            continue
        if not isinstance(value, int):
            return _error(f"real_seqs 必须是整数: {value!r}")
        seqs.append(value)
    try:
        result = await platform.send_forward(seqs)
    except ChatbotError as exc:
        return _error(exc)
    return "ok" if result.success else _error(result.error or "转发失败")


async def upload_group_file(platform: Any, args: dict[str, Any]) -> str:
    path = str(args.get("path") or "").strip()
    if not path:
        return _error("path 不能为空")
    name = args.get("name")
    if name is not None and not isinstance(name, str):
        return _error("name 必须是字符串")
    try:
        result = await platform.upload_group_file(path, name)
    except ChatbotError as exc:
        return _error(exc)
    return "ok" if result.success else _error(result.error or "上传失败")


async def dispatch(name: str, platform: Any, args: dict[str, Any]) -> str:
    """Run one tool by name against *platform*."""
    if name == "chatbot_react":
        return await react(platform, args)
    if name == "chatbot_send_message":
        return await send_message(platform, args)
    if name == "chatbot_poke":
        return await poke(platform, args)
    if name == "chatbot_send_forward":
        return await send_forward(platform, args)
    if name == "chatbot_upload_group_file":
        return await upload_group_file(platform, args)
    if name == "chatbot_read_history":
        return await read_history(platform, args)
    if name == "chatbot_fetch_media":
        fetcher = getattr(platform, "media", None) or getattr(platform, "_media", None)
        if fetcher is None:
            return _error("媒体下载未配置")
        return await fetch_media(platform, args, fetcher)
    if name == "chatbot_set_nickname":
        return await set_nickname(platform, args)
    if name == "chatbot_set_avatar":
        return await set_avatar(platform, args)
    if name == "chatbot_set_group_card":
        return await set_group_card(platform, args)
    if name == "chatbot_list_group_members":
        return await list_group_members(platform, args)
    if name == "chatbot_get_group_member":
        return await get_group_member(platform, args)
    if name == "chatbot_get_group_info":
        return await get_group_info(platform, args)
    if name == "chatbot_get_user_info":
        return await get_user_info(platform, args)
    if name == "chatbot_get_login_info":
        return await get_login_info(platform, args)
    if name == "chatbot_transcribe_voice":
        return await transcribe_voice(platform, args)
    if name == "chatbot_read_forward":
        return await read_forward(platform, args)
    if name == "chatbot_list_group_files":
        return await list_group_files(platform, args)
    if name == "chatbot_get_group_file_url":
        return await get_group_file_url(platform, args)
    if name == "chatbot_fetch_group_file":
        return await fetch_group_file(platform, args)
    if name == "chatbot_get_group_file_system_info":
        return await get_group_file_system_info(platform, args)
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
