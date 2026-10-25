from __future__ import annotations

from typing import Any

from crupest_qqbot_core.schema import Event

SELF_ID = 1950119910


def make_event(**overrides: Any) -> Event:
    """Build a group message event with sensible defaults."""
    payload: dict[str, Any] = {
        "time": 1792848561,
        "self_id": SELF_ID,
        "post_type": "message",
        "message_type": "group",
        "sub_type": "normal",
        "message_id": 1234,
        "real_seq": 8821,
        "group_id": 123456,
        "user_id": 10001,
        "message": [{"type": "text", "data": {"text": "你好"}}],
        "sender": {"user_id": 10001, "nickname": "张三", "card": "", "role": "member"},
    }
    payload.update(overrides)
    return Event.model_validate(payload)
