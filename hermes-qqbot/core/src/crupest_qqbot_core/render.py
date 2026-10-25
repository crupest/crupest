"""Turn an inbound OneBot event into the text the model actually reads.

Only two things are special-cased: ``@bot /command`` (returned bare so Hermes
can recognise it) and synthetic notices (already rendered by ``notice.py``).
Everything else is passed through: text is not stripped, ``at`` segments
become ``[@self]`` / ``[@12345]``, media become placeholders that say exactly
what happened to the download.
"""
from __future__ import annotations

from dataclasses import dataclass

from . import segments
from .schema import Event


@dataclass(frozen=True)
class MediaResult:
    """Outcome of downloading one media segment."""

    path: str | None = None
    failed: bool = False

    @property
    def cache(self) -> str:
        if self.path:
            return self.path
        return "failed" if self.failed else "none"


def _quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _internal_text(message_segments: list[dict]) -> str | None:
    parts = [
        str(segments.data_of(segment).get("text", ""))
        for segment in message_segments
        if segment.get("type") == "text"
    ]
    text = "".join(parts)
    return text or None


def _placeholder(kind: str, index: int, segment: dict, result: MediaResult) -> str:
    cache = _quote(result.cache)
    identifier = _quote(segments.media_id(segment))
    if kind == "file":
        return f"[file{index} name={_quote(segments.media_name(segment))} id={identifier} cache={cache}]"
    return f"[{kind}{index} id={identifier} cache={cache}]"


def flatten(
    message_segments: list[dict], self_id: object, media: tuple[MediaResult, ...] | list[MediaResult] = (),
) -> str:
    counters: dict[str, int] = {}
    parts: list[str] = []
    media_index = 0
    for segment in message_segments:
        kind = str(segment.get("type", ""))
        if kind == "text":
            parts.append(str(segments.data_of(segment).get("text", "")))
        elif kind == "at":
            target = str(segments.data_of(segment).get("qq", ""))
            parts.append("[@self]" if target == str(self_id) else f"[@{target}]")
        elif kind == "reply":
            continue
        elif kind == "forward":
            forward_id = str(segments.data_of(segment).get("id", ""))
            parts.append(f"[forward id={_quote(forward_id)}]")
        else:
            media_kind = segments.media_kind(segment)
            if media_kind is None:
                continue
            counters[media_kind] = counters.get(media_kind, 0) + 1
            result = media[media_index] if media_index < len(media) else MediaResult()
            media_index += 1
            parts.append(_placeholder(media_kind, counters[media_kind], segment, result))
    return "".join(parts)


def render_event(
    event: Event, self_id: object, media: tuple[MediaResult, ...] | list[MediaResult] = (),
) -> str | None:
    """Render *event* for the model, or ``None`` when there is nothing to say."""
    message_segments = segments.event_segments(event)

    if event.adapter is not None and event.adapter.internal:
        return _internal_text(message_segments)

    if not segments.has_content(message_segments):
        return None

    flat = flatten(message_segments, self_id, media)

    if segments.mentions_self(message_segments, self_id):
        match = segments.COMMAND_RE.match(flat)
        if match:
            return match.group(1)

    if event.message_type == "group":
        sender = event.sender
        name = ""
        if sender is not None:
            name = sender.card or sender.nickname or ""
        seq = event.real_seq if event.real_seq not in (None, "") else event.message_id
        prefix = segments.format_sender_prefix(name, event.user_id, seq)
        return f"{prefix} {flat}"
    return flat

