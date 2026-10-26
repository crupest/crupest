"""Everything the adapter decides: who may talk, and what the bot may call.

Two independent answers live here:

* :func:`decide_event` — may this inbound event reach Hermes?
* :func:`authorize` — may this outbound action run, and against which target?

Both are pure functions over config + event, so the whole behaviour is a table
in the tests.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from crupest_chatbot_core import segments
from crupest_chatbot_core.config import NotifyConfig
from crupest_chatbot_core.errors import REASON_BAD_PARAM, REASON_POLICY_DENIED, REASON_TARGET_MISMATCH, PolicyError
from crupest_chatbot_core.schema import Event

#: The complete outbound surface.  Anything not listed never reaches NapCat.
ALLOWED_ACTIONS = frozenset({
    "send_msg",
    "send_group_msg",
    "send_private_msg",
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


def authorize(
    action: str, params: dict[str, Any] | None, binding: Binding, self_id: str = "",
) -> dict[str, Any]:
    """Gate 2: validate an outbound action and pin its target.

    Returns a new params dict with missing targets filled in.  Raises
    :class:`PolicyError` for anything that is not allowed.
    """
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
    elif action == "set_group_card":
        # Only the bot's own card — a model must never rename a member.
        _require_group(action, prepared, binding)
        me = str(self_id or "")
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

    return prepared
