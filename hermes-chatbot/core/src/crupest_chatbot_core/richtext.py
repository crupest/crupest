"""Typed rich-text items → OneBot segments.

This is the contract behind the ``chatbot_send_message`` tool.  The model sends
a JSON array of small, typed objects (text / at / face / dice / rps / reply);
this module validates them and turns them into wire segments.  Deliberately not
raw OneBot segment dicts: the model should not have to know protocol field
shapes, and unknown keys never reach NapCat.
"""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any

from . import faces, segments
from .config import FeaturesConfig

MAX_SEGMENTS = 20
MAX_TEXT_CHARS = 4500
_QQ_RE = re.compile(r"\d{1,12}")


class RichTextError(ValueError):
    """A bad items array; ``index`` is the 0-based item position."""

    def __init__(self, index: int, message: str) -> None:
        self.index = index
        super().__init__(f"segments[{index + 1}]: {message}")


def build(
    items: Any,
    features: FeaturesConfig | None = None,
    *,
    max_text: int = MAX_TEXT_CHARS,
    group: bool = True,
    resolve_seq: Callable[[Any], str | None] | None = None,
) -> list[dict[str, Any]]:
    """Validate *items* and build the segment list.

    Raises :class:`RichTextError` with the offending index so the tool can tell
    the model which item to fix.
    """
    settings = features or FeaturesConfig()
    if not isinstance(items, list) or not items:
        raise RichTextError(0, "至少需要一段")
    if len(items) > MAX_SEGMENTS:
        raise RichTextError(0, f"最多 {MAX_SEGMENTS} 段")

    out: list[dict[str, Any]] = []
    text_chars = 0
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise RichTextError(index, "必须是对象")
        kind = item.get("type")
        if kind == "text":
            text = item.get("text")
            if not isinstance(text, str) or not text:
                raise RichTextError(index, "text 必须是非空字符串")
            text_chars += len(text)
            if text_chars > max_text:
                raise RichTextError(index, f"文本合计不能超过 {max_text} 字")
            out.append(segments.text(text))
        elif kind == "at":
            if not settings.at:
                raise RichTextError(index, "@ 已关闭")
            if not group:
                raise RichTextError(index, "私聊里不能 @ 人")
            target = str(item.get("qq") or "")
            if target == "all":
                if not settings.at_all:
                    raise RichTextError(index, "@全体未开启")
            elif not _QQ_RE.fullmatch(target):
                raise RichTextError(index, "qq 必须是 QQ 号或 all")
            out.append(segments.at(target))
        elif kind == "face":
            if not settings.face:
                raise RichTextError(index, "QQ 表情已关闭")
            name = str(item.get("name") or "").strip()
            face_id = faces.face_id(name)
            if face_id is None:
                raise RichTextError(index, f"未知表情名 {name!r}，请使用工具说明里的名字")
            out.append(segments.face(face_id))
        elif kind == "dice":
            if not settings.dice:
                raise RichTextError(index, "骰子已关闭")
            out.append(segments.dice())
        elif kind == "rps":
            if not settings.rps:
                raise RichTextError(index, "猜拳已关闭")
            out.append(segments.rps())
        elif kind == "reply":
            if index != 0:
                raise RichTextError(index, "reply 必须是第一段")
            seq = item.get("seq")
            if resolve_seq is None:
                raise RichTextError(index, "当前会话不支持引用")
            message_id = resolve_seq(seq)
            if not message_id:
                raise RichTextError(index, f"找不到消息序号 {seq!r}")
            out.append(segments.reply(message_id))
        else:
            raise RichTextError(index, f"不支持的类型 {kind!r}")
    return out
