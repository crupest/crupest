"""Synthesise a text event from a group notice (poke / member change).

NapCat pushes ``post_type="notice"`` events; the bot can only act on them if
they look like messages.  The wording is the same as the previous adapter so
behaviour does not change.
"""
from __future__ import annotations

from typing import Any

from .schema import Event


def _display_name(event: Event) -> str:
    if event.sender is not None:
        name = event.sender.card or event.sender.nickname
        if name:
            return name
    return str(event.user_id or "")


def render_notice(event: Event, self_id: Any, group_id: Any) -> dict[str, Any] | None:
    """Return a synthetic message event, or ``None`` when this notice is ignored."""
    notice_type = event.notice_type or ""
    sub_type = event.sub_type or ""
    user_id = str(event.user_id or "")
    self_text = str(self_id or "")

    if notice_type == "notify" and sub_type == "poke":
        if str(event.target_id or "") != self_text or user_id == self_text:
            return None
        text = f"[系统] 用户 {_display_name(event)}({user_id}) 戳了戳你"
        origin = "poke"
    elif notice_type == "group_increase":
        if not user_id or user_id == self_text:
            return None
        text = f"[系统] 用户 {_display_name(event)}({user_id}) 加入了群聊"
        origin = "member_join"
    elif notice_type == "group_decrease":
        if not user_id or user_id == self_text:
            return None
        if sub_type == "kick":
            text = f"[系统] 用户 {_display_name(event)}({user_id}) 被管理员移出了群聊"
            origin = "member_kick"
        else:
            text = f"[系统] 用户 {_display_name(event)}({user_id}) 退出了群聊"
            origin = "member_leave"
    else:
        return None

    return {
        "time": event.time,
        "self_id": event.self_id,
        "post_type": "message",
        "message_type": "group",
        "group_id": group_id,
        "user_id": event.user_id,
        "message": [{"type": "text", "data": {"text": text}}],
        "adapter": {"internal": True, "origin": origin},
    }
