"""Outbound text cleanup: QQ renders no markdown, so flatten it first."""
from __future__ import annotations

import re

_FENCE_RE = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
_HEADING_RE = re.compile(r"^[ \t]{0,3}#{1,6}[ \t]+", re.MULTILINE)
_BOLD_RE = re.compile(r"\*\*([^*\n]+)\*\*")
_UNDERSCORE_BOLD_RE = re.compile(r"__([^_\n]+)__")


def to_plain(text: str) -> str:
    """Strip code fences, inline code, headings and bold markers.

    Idempotent: running it twice yields the same string.
    """
    if not text:
        return text
    text = _FENCE_RE.sub(lambda match: match.group(1).rstrip("\n"), text)
    text = _INLINE_CODE_RE.sub(r"\1", text)
    text = _HEADING_RE.sub("", text)
    text = _BOLD_RE.sub(r"\1", text)
    return _UNDERSCORE_BOLD_RE.sub(r"\1", text)
