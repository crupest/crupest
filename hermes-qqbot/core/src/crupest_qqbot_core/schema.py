"""Pydantic models for the OneBot 11 subset we actually use.

Unknown fields are preserved (``extra="allow"``) so a newer NapCat can add
fields without breaking either process.  ``parse_frame`` is the only entry
point: it never raises raw ``ValueError``/``KeyError`` — everything becomes a
:class:`~crupest_qqbot_core.errors.SchemaError`.
"""
from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .errors import SchemaError


class MessageSegment(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


class Sender(BaseModel):
    model_config = ConfigDict(extra="allow")

    user_id: Any = None
    nickname: str | None = None
    card: str | None = None
    role: str | None = None
    title: str | None = None


class AdapterMeta(BaseModel):
    model_config = ConfigDict(extra="allow")

    internal: bool = False
    origin: str = ""


class Event(BaseModel):
    """A OneBot 11 event. Only ``self_id``/``post_type`` are required."""

    model_config = ConfigDict(extra="allow")

    time: float = 0
    self_id: Any = None
    post_type: str
    message_type: str | None = None
    sub_type: str | None = None
    notice_type: str | None = None
    message_id: Any = None
    real_seq: Any = None
    message_seq: Any = None
    group_id: Any = None
    user_id: Any = None
    target_id: Any = None
    operator_id: Any = None
    message: list[MessageSegment] | str | None = None
    raw_message: str | None = None
    sender: Sender | None = None
    adapter: AdapterMeta | None = None


class ApiRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    action: str
    params: dict[str, Any] = Field(default_factory=dict)
    echo: str = ""


class ApiResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str = "ok"
    retcode: int = 0
    data: Any = None
    echo: str = ""
    reason: str | None = None
    wording: str | None = None
    message: str | None = None


def _excerpt(raw: str | bytes) -> str:
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "replace")
    return raw[:200]


def _validate(model: type[BaseModel], payload: dict[str, Any], raw: str | bytes):
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0] if exc.errors() else {"loc": (), "msg": "invalid"}
        path = ".".join(str(part) for part in first["loc"])
        raise SchemaError("shape", path=path, raw_excerpt=_excerpt(raw)) from exc


def parse_frame(raw: str | bytes) -> Event | ApiResponse:
    """Parse one inbound frame, or raise :class:`SchemaError`."""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise SchemaError("json", raw_excerpt=_excerpt(raw)) from exc
    if not isinstance(payload, dict):
        raise SchemaError("shape", path="root", raw_excerpt=_excerpt(raw))
    if "post_type" in payload:
        return _validate(Event, payload, raw)
    if "echo" in payload:
        return _validate(ApiResponse, payload, raw)
    raise SchemaError("unknown_frame", path="post_type|echo", raw_excerpt=_excerpt(raw))
