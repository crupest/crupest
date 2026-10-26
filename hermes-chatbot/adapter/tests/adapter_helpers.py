from __future__ import annotations

from typing import Any

from crupest_chatbot_core.schema import Event

SELF_ID = 1950119910

#: The default message mentions the bot, so the default event clears the trigger gate.
DEFAULT_MESSAGE = [
    {"type": "at", "data": {"qq": str(SELF_ID)}},
    {"type": "text", "data": {"text": " 在吗"}},
]


def make_event(**overrides: Any) -> Event:
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
        "message": DEFAULT_MESSAGE,
        "sender": {"user_id": 10001, "nickname": "张三"},
    }
    payload.update(overrides)
    return Event.model_validate(payload)
