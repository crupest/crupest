"""Minimal stand-ins for the Hermes gateway types.

The plugin normally imports the real ``gateway.*`` objects; when Hermes is not
installed (unit tests, plain ``pip install``) these local shapes keep the module
importable.  They mirror the parts of the contract the adapter relies on —
including the abstract methods, so a missing override fails the tests instead of
failing at gateway startup.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any


@dataclass
class SendResult:
    success: bool
    message_id: str | None = None
    error: str | None = None
    raw_response: Any = None
    retryable: bool = False
    retry_after: float | None = None
    continuation_message_ids: tuple = ()
    error_kind: str | None = None


@dataclass
class MessageEvent:
    text: str
    message_type: Any = None
    source: Any = None
    raw_message: Any = None
    message_id: str | None = None
    media_urls: list[str] = field(default_factory=list)
    media_types: list[str] = field(default_factory=list)
    reply_to_message_id: str | None = None
    reply_to_text: str | None = None
    reply_to_author_id: str | None = None
    reply_to_author_name: str | None = None
    internal: bool = False
    timestamp: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


class _MessageType:
    TEXT = "text"


MessageType = _MessageType


class BasePlatformAdapter(ABC):
    MAX_MESSAGE_LENGTH = 4096
    supports_code_blocks = False

    def __init__(self, config: Any = None, platform: Any = None) -> None:
        self.config = config
        self.platform = platform
        self.name = "chatbot"
        self.handler = None
        self._running = False

    # ── lifecycle bookkeeping (mirrors gateway/platforms/base.py) ──
    def _mark_connected(self, **kwargs: Any) -> None:
        self._running = True

    def _mark_disconnected(self) -> None:
        self._running = False

    @property
    def is_connected(self) -> bool:
        return self._running

    # ── abstract contract ──
    @abstractmethod
    async def connect(self, *, is_reconnect: bool = False) -> bool: ...

    @abstractmethod
    async def disconnect(self) -> None: ...

    @abstractmethod
    async def send(
        self, chat_id: str, content: str, reply_to: str | None = None, metadata: Any = None,
    ) -> SendResult: ...

    @abstractmethod
    async def get_chat_info(self, chat_id: str) -> dict[str, Any]: ...

    # ── helpers the adapter uses ──
    def build_source(self, **kwargs: Any) -> SimpleNamespace:
        return SimpleNamespace(**kwargs)

    async def handle_message(self, event: MessageEvent) -> None:
        if self.handler is not None:
            await self.handler(event)

    def truncate_message(self, content: str, max_length: int = 4096) -> list[str]:
        """Split *content* into chunks of at most *max_length* characters."""
        limit = max(1, int(max_length))
        if len(content) <= limit:
            return [content]
        chunks: list[str] = []
        remaining = content
        while len(remaining) > limit:
            cut = remaining.rfind("\n", 0, limit)
            if cut <= 0:
                cut = limit
            chunks.append(remaining[:cut])
            remaining = remaining[cut:].lstrip("\n")
        if remaining:
            chunks.append(remaining)
        return chunks

    async def _send_plain_fallback(self, chat_id: str, content: str, *, reply_to=None, metadata=None) -> SendResult:
        return SendResult(success=False, error="plain-text fallback disabled", retryable=False)

    def _send_retry_is_final(self, result: SendResult) -> bool:
        return False
