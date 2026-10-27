"""Everything the adapter decides: who may talk, and what the bot may call.

Two independent answers live here:

* :func:`decide_event` — may this inbound event reach Hermes?
* :func:`authorize` — may this outbound action run, and against which target?

Both are pure functions over config + event, so the whole behaviour is a table
in the tests.  Filesystem checks (``check_upload``) and message-id checks
(``SeqMap``) are deliberately separate: they need IO and are called by the
relay right before the upstream call.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

from crupest_chatbot_core import segments
from crupest_chatbot_core.config import FeaturesConfig, LimitsConfig, NotifyConfig
from crupest_chatbot_core.errors import REASON_BAD_PARAM, REASON_POLICY_DENIED, REASON_TARGET_MISMATCH, PolicyError
from crupest_chatbot_core.schema import Event

#: The complete outbound surface.  Anything not listed never reaches NapCat.
ALLOWED_ACTIONS = frozenset({
    "send_msg",
    "send_group_msg",
    "send_private_msg",
    "send_poke",
    "send_group_forward_msg",
    "send_private_forward_msg",
    "upload_group_file",
    "upload_private_file",
    "set_msg_emoji_like",
    "mark_msg_as_read",
    "get_group_msg_history",
    "get_friend_msg_history",
    "get_forward_msg",
    "fetch_ptt_text",
    "get_group_root_files",
    "get_group_files_by_folder",
    "get_group_file_url",
    "get_group_file_system_info",
    "get_msg",
    "get_group_member_info",
    "get_group_member_list",
    "get_group_info",
    "get_login_info",
    "get_stranger_info",
    "get_file",
    "get_image",
    "get_record",
    "get_private_file_url",
    # NapCat extensions (not in the OneBot 11 spec); the model-facing tools are
    # chatbot_set_nickname / chatbot_set_avatar / chatbot_set_group_card.
    "set_qq_profile",
    "set_qq_avatar",
    "set_group_card",
})

_GROUP_TARGETS = frozenset({
    "send_group_msg",
    "send_group_forward_msg",
    "upload_group_file",
    "get_group_msg_history",
    "get_group_member_info",
    "get_group_member_list",
    "get_group_info",
    "get_group_file_url",
    "get_group_root_files",
    "get_group_files_by_folder",
    "get_group_file_system_info",
})
_USER_TARGETS = frozenset({
    "send_private_msg",
    "send_private_forward_msg",
    "upload_private_file",
    "get_private_file_url",
    "get_friend_msg_history",
})
FORWARD_ACTIONS = frozenset({"send_group_forward_msg", "send_private_forward_msg"})

UPLOAD_ACTIONS = frozenset({"upload_group_file", "upload_private_file"})
#: Actions whose ``message`` field must be an array of segments.  A string is
#: the CQ-code form, which NapCat would parse (at-all, cards, URL fetches), so
#: it is rejected here even though the plugin never sends one.
MESSAGE_ACTIONS = frozenset({"send_msg", "send_group_msg", "send_private_msg"})

#: Mutating actions where the plugin exposes only a subset of what the NapCat
#: action accepts (or where the action can target things the tool cannot name).
#: Anything outside this set is rejected at the boundary, not passed through.
_ACTION_PARAMS: dict[str, frozenset[str]] = {
    # No ``message_id`` (would bypass the real_seq map) and no ``set=false``
    # (the tool only adds reactions; removing them is not exposed).
    "set_msg_emoji_like": frozenset({"real_seq", "emoji_id"}),
    "set_qq_profile": frozenset({"nickname"}),
    "set_qq_avatar": frozenset({"file"}),
    "set_group_card": frozenset({"card", "group_id", "user_id"}),
    # Tool takes real_seq (mapped by the adapter) or an id from history JSON.
    "fetch_ptt_text": frozenset({"real_seq", "message_id"}),
    "send_poke": frozenset({"group_id", "user_id"}),
    # Only node-by-id forwards; no ``content``/``user_id``/``nickname`` nodes.
    "send_group_forward_msg": frozenset({"group_id", "messages"}),
    "send_private_forward_msg": frozenset({"user_id", "messages"}),
    "upload_group_file": frozenset({"group_id", "file", "name", "folder"}),
    "upload_private_file": frozenset({"user_id", "file", "name"}),
}
WINDOW_ACTIONS = frozenset({
    "send_msg",
    "send_group_msg",
    "send_private_msg",
    "send_group_forward_msg",
    "send_private_forward_msg",
    "upload_group_file",
    "upload_private_file",
    "set_msg_emoji_like",
})

_QQ_RE = re.compile(r"\d{1,12}")
_FACE_RE = re.compile(r"\d{1,3}")
_FORBIDDEN_NAME = re.compile(r"[/\\\x00-\x1f]")


@dataclass(frozen=True)
class Binding:
    """The one conversation this adapter serves (either field may be ``None``)."""

    group_id: int | None = None
    user_id: int | None = None

    @property
    def kind(self) -> str:
        return "group" if self.group_id is not None else "dm"

    @property
    def chat_id(self) -> str:
        if self.group_id is not None:
            return f"group:{self.group_id}"
        return f"user:{self.user_id}"


@dataclass(frozen=True)
class Context:
    """Identity used for the few actions that need the bot's own QQ."""

    self_id: str = ""


@dataclass(frozen=True)
class Decision:
    forward: bool
    reason: str


def _same(left: Any, right: Any) -> bool:
    return str(left) == str(right)


def _decide_message(event: Event, binding: Binding, window: Any) -> Decision:
    message_segments = segments.event_segments(event)

    if event.message_type == "group":
        if binding.group_id is None or not _same(event.group_id, binding.group_id):
            return Decision(False, "other_chat")
        if _same(event.user_id, event.self_id):
            return Decision(False, "self")
        if not segments.has_content(message_segments):
            return Decision(False, "empty")
        if segments.mentions_self(message_segments, event.self_id):
            return Decision(True, "mention")
        if window is not None and window.active():
            return Decision(True, "window")
        return Decision(False, "inactive")

    if binding.user_id is None or not _same(event.user_id, binding.user_id):
        return Decision(False, "other_chat")
    if _same(event.user_id, event.self_id):
        return Decision(False, "self")
    if not segments.has_content(message_segments):
        return Decision(False, "empty")
    return Decision(True, "dm")


def _decide_notice(event: Event, binding: Binding, notify: NotifyConfig) -> Decision:
    notice_type = event.notice_type or ""
    if notice_type == "notify" and (event.sub_type or "") == "poke":
        if not notify.poke:
            return Decision(False, "notice_ignored")
    elif notice_type in ("group_increase", "group_decrease"):
        if not notify.member_change:
            return Decision(False, "notice_ignored")
    else:
        return Decision(False, "unsupported")

    if binding.group_id is None or not _same(event.group_id, binding.group_id):
        return Decision(False, "other_chat")
    return Decision(True, "notice")


def decide_event(event: Event, binding: Binding, window: Any, notify: NotifyConfig) -> Decision:
    """Gate 1: may this event be forwarded to Hermes?"""
    if event.post_type == "message":
        return _decide_message(event, binding, window)
    if event.post_type == "notice":
        return _decide_notice(event, binding, notify)
    return Decision(False, "unsupported")


def _require_group(action: str, params: dict[str, Any], binding: Binding) -> None:
    if binding.group_id is None:
        raise PolicyError(action, REASON_TARGET_MISMATCH, f"{action}: 本实例未绑定群")
    target = params.get("group_id")
    if target in (None, ""):
        params["group_id"] = binding.group_id
    elif not _same(target, binding.group_id):
        raise PolicyError(action, REASON_TARGET_MISMATCH, f"{action}: 目标群不是本实例绑定的群")


def _require_user(action: str, params: dict[str, Any], binding: Binding) -> None:
    if binding.user_id is None:
        raise PolicyError(action, REASON_TARGET_MISMATCH, f"{action}: 本实例未绑定私聊")
    target = params.get("user_id")
    if target in (None, ""):
        params["user_id"] = binding.user_id
    elif not _same(target, binding.user_id):
        raise PolicyError(action, REASON_TARGET_MISMATCH, f"{action}: 目标不是本实例绑定的好友")


def _bad(action: str, message: str) -> PolicyError:
    return PolicyError(action, REASON_BAD_PARAM, message)


def _check_at(
    action: str, data: dict[str, Any], binding: Binding, features: FeaturesConfig,
) -> None:
    if binding.group_id is None:
        raise _bad(action, f"{action}: 私聊不能 @ 人")
    target = str(data.get("qq") or "")
    if target == "all":
        if not features.at_all:
            raise PolicyError(action, REASON_POLICY_DENIED, f"{action}: @全体未开启")
        return
    if not _QQ_RE.fullmatch(target):
        raise _bad(action, f"{action}: at.qq 必须是 QQ 号或 all")


def _check_media_ref(action: str, kind: str, data: dict[str, Any], limits: LimitsConfig) -> None:
    """Local media must come from the shared volume.

    Remote URLs are rejected here: the plugin downloads them through its SSRF
    guard and sends a local path.  Local paths are confined so a prompt-injected
    ``MEDIA:`` line cannot read adapter-only files such as the config or tokens.
    """
    ref = str(data.get("file") or "")
    if not ref:
        raise _bad(action, f"{action}: {kind} 段缺少 file")
    if ref.startswith(("http://", "https://")):
        raise PolicyError(
            action, REASON_POLICY_DENIED, f"{action}: 远程媒体必须由插件先下载",
        )
    if ref.startswith("base64://"):
        return
    if "://" in ref and not ref.startswith("file://"):
        raise PolicyError(
            action, REASON_POLICY_DENIED, f"{action}: 不支持的媒体协议",
        )
    if ref.startswith("file://"):
        ref = unquote(urlparse(ref).path)
    candidate = Path(ref)
    if not candidate.is_absolute():
        candidate = Path(limits.upload_dir) / candidate
    try:
        path = candidate.resolve(strict=False)
        root = Path(limits.upload_dir).resolve(strict=False)
    except OSError as exc:
        raise _bad(action, f"{action}: 文件路径无效 ({exc})") from exc
    if not path.is_relative_to(root):
        raise PolicyError(
            action, REASON_POLICY_DENIED, f"{action}: 只能发送 {limits.upload_dir} 下的文件",
        )


def _check_message_segments(
    action: str, prepared: dict[str, Any], binding: Binding,
    features: FeaturesConfig, limits: LimitsConfig,
) -> None:
    """Validate every outbound segment; reject disabled/unknown features.

    The plugin has the same checks, but the adapter is the hard boundary: a
    bypassing client must not be able to send a disabled segment type.
    """
    message = prepared.get("message")
    if not isinstance(message, list):
        raise _bad(action, f"{action}: message 必须是数组")
    if len(message) > limits.max_segments_per_message:
        raise _bad(action, f"{action}: message 段数超过 {limits.max_segments_per_message}")

    kept: list[dict[str, Any]] = []
    for index, segment in enumerate(message):
        if not isinstance(segment, dict):
            raise _bad(action, f"{action}: message[{index}] 不是对象")
        kind = str(segment.get("type") or "")
        raw_data = segment.get("data")
        data = raw_data if isinstance(raw_data, dict) else {}

        if kind == "text":
            if not isinstance(data.get("text"), str):
                raise _bad(action, f"{action}: text 段缺少文本")
        elif kind == "at":
            if not features.at:
                raise PolicyError(action, REASON_POLICY_DENIED, "@ 已关闭")
            _check_at(action, data, binding, features)
        elif kind == "face":
            if not features.face:
                raise PolicyError(action, REASON_POLICY_DENIED, "QQ 表情已关闭")
            face_id = str(data.get("id") or "")
            if not _FACE_RE.fullmatch(face_id):
                raise _bad(action, f"{action}: face.id 必须是 0-999 的数字")
        elif kind in ("dice", "rps"):
            if not (features.dice if kind == "dice" else features.rps):
                raise PolicyError(action, REASON_POLICY_DENIED, f"{kind} 已关闭")
            if data:
                raise _bad(action, f"{action}: {kind} 段不接受参数")
        elif kind in ("image", "record", "video"):
            _check_media_ref(action, kind, data, limits)
        elif kind == "file":
            _check_media_ref(action, kind, data, limits)
        elif kind == "reply":
            if not str(data.get("id") or ""):
                raise _bad(action, f"{action}: reply 段缺少 id")
        else:
            raise _bad(action, f"{action}: 不允许的消息段 {kind or '?'}")
        kept.append(segment)

    prepared["message"] = kept


def _check_forward(action: str, prepared: dict[str, Any], limits: LimitsConfig) -> None:
    messages = prepared.get("messages")
    if not isinstance(messages, list):
        raise _bad(action, f"{action}: messages 必须是数组")
    if not 1 <= len(messages) <= limits.forward_max_nodes:
        raise _bad(action, f"{action}: 转发条数必须在 1-{limits.forward_max_nodes} 之间")
    for index, node in enumerate(messages):
        if not isinstance(node, dict) or set(node) != {"type", "data"} or node.get("type") != "node":
            raise _bad(action, f"{action}: messages[{index}] 必须是 node 段")
        data = node.get("data")
        if not isinstance(data, dict) or set(data) != {"id"}:
            raise _bad(action, f"{action}: node 只接受 id（不接受伪造的 content/user_id）")
        if not _QQ_RE.fullmatch(str(data.get("id") or "")):
            raise _bad(action, f"{action}: node.id 必须是消息 ID")


def check_upload(action: str, prepared: dict[str, Any], limits: LimitsConfig) -> None:
    """Confine uploads to the shared directory and cap their size.

    Runs in the adapter (the process NapCat talks to), so it is the hard
    boundary even if the plugin is bypassed.
    """
    raw = str(prepared.get("file") or "")
    if not raw:
        raise _bad(action, f"{action}: file 不能为空")
    try:
        candidate = Path(raw)
        if not candidate.is_absolute():
            candidate = Path(limits.upload_dir) / candidate
        path = candidate.resolve(strict=True)
        root = Path(limits.upload_dir).resolve(strict=False)
    except OSError as exc:
        raise _bad(action, f"{action}: 文件不可读 ({exc})") from exc
    if not path.is_relative_to(root):
        raise PolicyError(action, REASON_POLICY_DENIED, f"{action}: 只能上传 {limits.upload_dir} 下的文件")
    if not path.is_file():
        raise _bad(action, f"{action}: 不是普通文件")
    size = path.stat().st_size
    if size > limits.upload_max_bytes:
        raise _bad(action, f"{action}: 文件超过 {limits.upload_max_bytes} 字节")
    name = str(prepared.get("name") or path.name).strip()
    if not name or len(name) > 100 or _FORBIDDEN_NAME.search(name):
        raise _bad(action, f"{action}: 文件名不合法")
    prepared["file"] = str(path)
    prepared["name"] = name
    if "folder" in prepared and not isinstance(prepared["folder"], str):
        raise _bad(action, f"{action}: folder 必须是字符串")


def authorize(
    action: str,
    params: dict[str, Any] | None,
    binding: Binding,
    self_id: str = "",
    *,
    context: Context | None = None,
    features: FeaturesConfig | None = None,
    limits: LimitsConfig | None = None,
) -> dict[str, Any]:
    """Gate 2: validate an outbound action and pin its target.

    Returns a new params dict with missing targets filled in.  Raises
    :class:`PolicyError` for anything that is not allowed.
    """
    features = features or FeaturesConfig()
    limits = limits or LimitsConfig()
    if context is None:
        context = Context(self_id=str(self_id or ""))
    elif not context.self_id and self_id:
        context = replace(context, self_id=str(self_id))

    if action not in ALLOWED_ACTIONS:
        raise PolicyError(action, REASON_POLICY_DENIED, f"不允许的动作: {action}")
    prepared: dict[str, Any] = dict(params or {})

    allowed_params = _ACTION_PARAMS.get(action)
    if allowed_params is not None:
        extra = sorted(set(prepared) - allowed_params)
        if extra:
            raise PolicyError(
                action, REASON_BAD_PARAM, f"{action}: 不支持的参数: {', '.join(extra)}",
            )

    if action in MESSAGE_ACTIONS and isinstance(prepared.get("message"), str):
        raise PolicyError(
            action, REASON_BAD_PARAM, f"{action}: message 必须是数组格式（不接受 CQ 字符串）",
        )

    if action == "send_msg":
        message_type = prepared.get("message_type")
        if message_type == "group":
            _require_group(action, prepared, binding)
        elif message_type == "private":
            _require_user(action, prepared, binding)
        else:
            raise PolicyError(action, REASON_BAD_PARAM, "send_msg 需要 message_type=group|private")
    elif action == "send_poke":
        if not features.poke:
            raise PolicyError(action, REASON_POLICY_DENIED, "戳一戳已关闭")
        if binding.group_id is not None:
            _require_group(action, prepared, binding)
            target = str(prepared.get("user_id") or "")
            if not _QQ_RE.fullmatch(target):
                raise _bad(action, "send_poke: user_id 必须是 QQ 号")
        else:
            if prepared.get("group_id") not in (None, ""):
                raise PolicyError(action, REASON_TARGET_MISMATCH, "私聊里不能用 group_id")
            _require_user(action, prepared, binding)
    elif action in FORWARD_ACTIONS:
        if not features.forward:
            raise PolicyError(action, REASON_POLICY_DENIED, "合并转发已关闭")
        if action == "send_group_forward_msg":
            _require_group(action, prepared, binding)
        else:
            _require_user(action, prepared, binding)
        _check_forward(action, prepared, limits)
    elif action in UPLOAD_ACTIONS:
        if not features.upload:
            raise PolicyError(action, REASON_POLICY_DENIED, "文件上传已关闭")
        if action == "upload_group_file":
            _require_group(action, prepared, binding)
        else:
            _require_user(action, prepared, binding)
    elif action == "set_group_card":
        # Only the bot's own card — a model must never rename a member.
        _require_group(action, prepared, binding)
        me = str(context.self_id or self_id or "")
        if not me:
            raise PolicyError(action, REASON_BAD_PARAM, "还没有拿到自己的 QQ 号，稍后再试")
        target = str(prepared.get("user_id") or me)
        if target != me:
            raise PolicyError(action, REASON_TARGET_MISMATCH, "只能改自己的群名片")
        prepared["user_id"] = me
    elif action in _GROUP_TARGETS:
        _require_group(action, prepared, binding)
    elif action in _USER_TARGETS:
        _require_user(action, prepared, binding)

    if action in MESSAGE_ACTIONS:
        _check_message_segments(action, prepared, binding, features, limits)

    return prepared
