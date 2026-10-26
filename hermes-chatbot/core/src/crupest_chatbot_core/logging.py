"""Logging setup shared by both processes."""
from __future__ import annotations

import logging

_FORMAT = "%(asctime)s %(levelname)-5s %(name)s %(message)s"


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=_FORMAT,
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )


def preview(text: object, limit: int = 80) -> str:
    """One-line, length-bounded copy of message content for logs."""
    compact = " ".join(str(text or "").split())
    if limit <= 0:
        return ""
    return compact if len(compact) <= limit else compact[:limit] + "..."
