"""Pure helpers over OneBot 11 message segments.

No IO, no policy: build segments, flatten them, and answer questions about a
segment list (mentions the bot? has any content? which native id?).
"""
from __future__ import annotations

import re
from typing import Any

from .schema import Event

#: ``@bot /command`` — the bot mention must be real (segment level) *and* lead
#: the flattened text.  Erring on the side of "no command" is deliberate:
#: otherwise typing ``[@self] /reset`` by hand would reset the session.
COMMAND_RE = re.compile(r"^\s*\[@self\]\s*(/.*)$", re.DOTALL)

MEDIA_SEGMENTS = {"image": "image", "record": "voice", "video": "video", "file": "file"}


def text(content: str) -> dict[str, Any]:
    return {"type": "text", "data": {"text": content}}


def at(qq: str | int) -> dict[str, Any]:
    return {"type": "at", "data": {"qq": str(qq)}}


def image(file: str = "", url: str = "") -> dict[str, Any]:
    data: dict[str, Any] = {"file": file}
    if url:
        data["url"] = url
    return {"type": "image", "data": data}


def record(file: str = "") -> dict[str, Any]:
    return {"type": "record", "data": {"file": file}}


def video(file: str = "") -> dict[str, Any]:
    return {"type": "video", "data": {"file": file}}


def reply(message_id: str | int) -> dict[str, Any]:
    return {"type": "reply", "data": {"id": str(message_id)}}


def file(file_id: str = "", name: str = "") -> dict[str, Any]:
    return {"type": "file", "data": {"file_id": file_id, "file": name, "file_name": name}}


def event_segments(event: Event) -> list[dict[str, Any]]:
    """Return the message as a list of plain dicts.

    ``messagePostFormat`` is configured as ``array`` on NapCat, but a plain
    string is still accepted and treated as a single text segment so a
    misconfiguration degrades instead of dropping every message.
    """
    message = event.message
    if message is None:
        return []
    if isinstance(message, str):
        return [{"type": "text", "data": {"text": message}}]
    return [segment.model_dump() for segment in message]


def data_of(segment: dict[str, Any]) -> dict[str, Any]:
    data = segment.get("data")
    return data if isinstance(data, dict) else {}


def mentions_self(segments: list[dict[str, Any]], self_id: Any) -> bool:
    """True when any ``at`` segment targets the bot (``@all`` does not count)."""
    target = str(self_id or "")
    if not target:
        return False
    for segment in segments:
        if segment.get("type") != "at":
            continue
        if str(data_of(segment).get("qq", "")) == target:
            return True
    return False


def has_content(segments: list[dict[str, Any]]) -> bool:
    """True when the message carries anything at all.

    An ``at`` segment counts as content — a bare ``@bot`` must survive the
    empty-message check so the model can see it was mentioned.
    """
    for segment in segments:
        if segment.get("type") == "text":
            if str(data_of(segment).get("text", "")).strip():
                return True
        elif segment.get("type"):
            return True
    return False


def media_kind(segment: dict[str, Any]) -> str | None:
    return MEDIA_SEGMENTS.get(str(segment.get("type", "")))


def media_id(segment: dict[str, Any]) -> str:
    """Native NapCat identifier for a media segment.

    Images/records/videos carry it in ``data.file``; files prefer
    ``data.file_id`` and fall back to ``data.file``.
    """
    data = data_of(segment)
    kind = str(segment.get("type", ""))
    if kind == "file":
        return str(data.get("file_id") or data.get("file") or "")
    return str(data.get("file") or "")


def media_name(segment: dict[str, Any]) -> str:
    data = data_of(segment)
    return str(data.get("file_name") or data.get("name") or data.get("file") or "")


def extract_reply_id(segments: list[dict[str, Any]]) -> str | None:
    for segment in segments:
        if segment.get("type") == "reply":
            value = str(data_of(segment).get("id", "") or "")
            return value or None
    return None


def extract_forward_id(segments: list[dict[str, Any]]) -> str | None:
    for segment in segments:
        if segment.get("type") == "forward":
            value = str(data_of(segment).get("id", "") or "")
            return value or None
    return None


def format_sender_prefix(name: str, qq: Any, seq: Any = "") -> str:
    """``[昵称(QQ)#序号]`` — the shape the model has always seen."""
    label = name or str(qq or "")
    base = f"[{label}({qq})" if qq else f"[{label}"
    if seq:
        base += f"#{seq}"
    return base + "]"
