"""Hermes platform adapter for one QQ conversation.

The plugin owns Hermes-facing concerns: it builds ``MessageEvent`` objects,
downloads media, and maps send results onto ``SendResult``.  Everything about
QQ itself happens in the adapter process behind the WebSocket.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Callable
from datetime import UTC, datetime
from functools import partial
from typing import Any

import aiohttp
from crupest_chatbot_core import segments
from crupest_chatbot_core.errors import ChatbotError
from crupest_chatbot_core.render import MediaResult, flatten, render_event
from crupest_chatbot_core.schema import Event
from crupest_chatbot_core.text import to_plain

from .media import MediaError, MediaFetcher
from .stubs import BasePlatformAdapter, MessageEvent, MessageType, SendResult

logger = logging.getLogger(__name__)

# Hermes 0.19 re-exports MessageEvent from gateway.platforms.base (there is no
# gateway.platforms.event module).  Each import is isolated: a failure in one
# must not null out a name the others already bound.
try:  # pragma: no cover - exercised only inside Hermes
    from gateway.config import Platform
except ImportError:  # pragma: no cover
    Platform = None  # type: ignore[assignment]

try:  # pragma: no cover - exercised only inside Hermes
    from gateway.platforms.base import (
        BasePlatformAdapter,  # type: ignore[no-redef]
        MessageEvent,  # type: ignore[no-redef]
        MessageType,  # type: ignore[no-redef]
        SendResult,  # type: ignore[no-redef]
    )

    HERMES_AVAILABLE = True
except ImportError:  # pragma: no cover - unit tests run without Hermes
    HERMES_AVAILABLE = False
    logger.warning("Hermes gateway modules unavailable; using local stubs")

#: Errors Hermes must not retry: the request itself is wrong.
POLICY_REASONS = frozenset({"policy_denied", "target_mismatch", "bad_param", "schema"})

_SUFFIX_BY_KIND = {"image": ".jpg", "voice": ".amr", "video": ".mp4", "file": ".bin"}


class RpcUnavailable(Exception):
    """The adapter connection is down or the call timed out."""


class RpcError(ChatbotError):
    """The adapter answered with a failure."""

    def __init__(self, action: str, wording: str, reason: str = "", retcode: int = 0) -> None:
        self.action = action
        self.reason = reason or "rpc_failed"
        self.retcode = retcode
        super().__init__(f"{action}: {wording}")

    @property
    def retryable(self) -> bool:
        return self.reason not in POLICY_REASONS


class RpcClient:
    """JSON request/response over the adapter WebSocket."""

    def __init__(self) -> None:
        self._ws: Any = None
        self._ws_loop: asyncio.AbstractEventLoop | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._counter = 0

    @property
    def connected(self) -> bool:
        return self._ws is not None

    def attach(self, ws: Any) -> None:
        self._ws = ws
        try:
            self._ws_loop = asyncio.get_running_loop()
        except RuntimeError:
            self._ws_loop = None

    def detach(self) -> None:
        self._ws = None
        self._ws_loop = None
        self.fail_all("adapter 连接已断开")

    async def call(self, action: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
        if self._ws is None:
            raise RpcUnavailable("adapter 未连接")
        if self._ws_loop is None:
            self._ws_loop = asyncio.get_running_loop()
        self._counter += 1
        echo = f"q{self._counter}"
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[echo] = future
        try:
            await self._send({"action": action, "params": params, "echo": echo})
        except RpcUnavailable:
            self._pending.pop(echo, None)
            raise
        except Exception as exc:
            self._pending.pop(echo, None)
            raise RpcUnavailable(f"发送失败: {exc}") from exc
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            raise RpcUnavailable(f"{action}: 等待适配器超时") from None
        finally:
            self._pending.pop(echo, None)

    async def _send(self, payload: dict[str, Any]) -> None:
        """Send on the WebSocket's loop; tool handlers may run in a worker loop."""
        ws = self._ws
        loop = self._ws_loop
        if ws is None or loop is None:
            raise RpcUnavailable("adapter 未连接")
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            await ws.send_json(payload)
            return
        try:
            scheduled = asyncio.run_coroutine_threadsafe(ws.send_json(payload), loop)
            await asyncio.wrap_future(scheduled)
        except RuntimeError as exc:
            raise RpcUnavailable(f"发送失败: {exc}") from exc

    def resolve(self, payload: dict[str, Any]) -> None:
        echo = str(payload.get("echo") or "")
        future = self._pending.pop(echo, None)
        if future is not None:
            self._deliver(future, partial(self._set_result, future, payload))

    def fail_all(self, reason: str) -> None:
        pending, self._pending = self._pending, {}
        for future in pending.values():
            self._deliver(future, partial(self._set_failure, future, reason))

    @staticmethod
    def _deliver(future: asyncio.Future[Any], callback: Callable[[], None]) -> None:
        """Run *callback* on the loop that owns *future*.

        Hermes runs async tools in a disposable worker loop; the WebSocket
        reader lives in the gateway loop.  Touching ``set_result`` from the
        wrong loop leaves the tool waiting for its full timeout.
        """
        loop = future.get_loop()
        if loop.is_closed():
            return
        try:
            running = asyncio.get_running_loop()
        except RuntimeError:
            running = None
        if running is loop:
            callback()
            return
        try:
            loop.call_soon_threadsafe(callback)
        except RuntimeError:
            pass

    @staticmethod
    def _set_result(future: asyncio.Future[Any], payload: dict[str, Any]) -> None:
        if not future.done():
            future.set_result(payload)

    @staticmethod
    def _set_failure(future: asyncio.Future[Any], reason: str) -> None:
        if not future.done():
            future.set_exception(RpcUnavailable(reason))


def _event_timestamp(epoch: float) -> datetime | None:
    """OneBot ``time`` is Unix seconds; ignore malformed values instead of dropping the event."""
    if not epoch:
        return None
    try:
        return datetime.fromtimestamp(epoch, tz=UTC)
    except (OverflowError, OSError, ValueError):
        return None


def build_message_event(
    *,
    text: str,
    source: Any,
    message_id: str,
    media_urls: list[str],
    media_types: list[str],
    reply: tuple[str, str, str, str] | None,
    raw: dict[str, Any],
    internal: bool = False,
    timestamp: datetime | None = None,
) -> MessageEvent:
    reply_id, reply_text, reply_author_id, reply_author_name = reply or ("", "", "", "")
    return MessageEvent(
        text=text,
        message_type=MessageType.TEXT,
        source=source,
        raw_message=raw,
        message_id=message_id,
        media_urls=media_urls,
        media_types=media_types,
        reply_to_message_id=reply_id or None,
        reply_to_text=reply_text or None,
        reply_to_author_id=reply_author_id or None,
        reply_to_author_name=reply_author_name or None,
        internal=internal,
        timestamp=timestamp or datetime.now(UTC),
    )


class QQPlatform(BasePlatformAdapter):
    MAX_MESSAGE_LENGTH = 4500

    def __init__(
        self,
        config: Any = None,
        *,
        url: str,
        token: str,
        chat_kind: str,
        chat_id: str,
        config_sha: str = "",
        call_timeout: float = 60.0,
        upload_timeout: float = 600.0,
        media_fetcher: MediaFetcher | None = None,
        strip_markdown: bool = True,
    ) -> None:
        platform = Platform("onebot") if Platform is not None else "onebot"
        super().__init__(config, platform)
        self._url = url
        self._token = token
        self._chat_kind = "group" if chat_kind == "group" else "dm"
        self._chat_numeric = str(chat_id)
        self._config_sha = config_sha
        self._call_timeout = call_timeout
        self._upload_timeout = upload_timeout
        self._media = media_fetcher
        self._strip = strip_markdown
        self._rpc = RpcClient()
        self._task: asyncio.Task[None] | None = None
        self._worker: asyncio.Task[None] | None = None
        self._maintenance: asyncio.Task[None] | None = None
        self._inbound: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=256)
        self._stopping = False
        self._backoff = 1.0
        self._self_id = ""

    @property
    def chat_key(self) -> str:
        prefix = "group" if self._chat_kind == "group" else "user"
        return f"{prefix}:{self._chat_numeric}"

    @property
    def chat_kind(self) -> str:
        return self._chat_kind

    @property
    def media(self) -> MediaFetcher | None:
        return self._media

    async def connect(self, *, is_reconnect: bool = False) -> bool:
        """Start the background connection loop. ``is_reconnect`` is honoured by the base contract."""
        if self._task is None or self._task.done():
            self._stopping = False
            self._task = asyncio.create_task(self._run())
        self._ensure_worker()
        self._start_cache_maintenance()
        self._notify("_mark_connected")
        return True

    async def disconnect(self) -> None:
        self._stopping = True
        self._rpc.detach()
        for task in (self._worker, self._task, self._maintenance):
            if task is not None:
                task.cancel()
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001 - shutdown must finish
                    pass
        self._worker = None
        self._task = None
        self._maintenance = None
        self._notify("_mark_disconnected")

    def _start_cache_maintenance(self) -> None:
        if self._maintenance is None or self._maintenance.done():
            self._maintenance = asyncio.create_task(
                self._cache_maintenance(), name="chatbot-cache-maintenance",
            )

    async def _cache_maintenance(self) -> None:
        """Prune the local media cache at startup, then once a day."""
        while True:
            try:
                removed, freed = await asyncio.to_thread(self._prune_cache)
                if removed:
                    logger.info("media cache pruned files=%d bytes=%d", removed, freed)
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001 - maintenance must never take the adapter down
                logger.exception("media cache prune failed")
            await asyncio.sleep(24 * 3600)

    def _prune_cache(self) -> tuple[int, int]:
        if self._media is None:
            return 0, 0
        return self._media.prune()

    def _notify(self, marker_name: str) -> None:
        """Call an optional BasePlatformAdapter status hook (absent in unit-test stubs)."""
        marker = getattr(self, marker_name, None)
        if callable(marker):
            try:
                marker()
            except Exception:  # pragma: no cover - status bookkeeping only
                logger.debug("%s failed", marker_name, exc_info=True)

    async def _run(self) -> None:
        while not self._stopping:
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.ws_connect(
                        self._url,
                        headers={"Authorization": f"Bearer {self._token}"},
                        heartbeat=30,
                    ) as ws:
                        self._rpc.attach(ws)
                        self._backoff = 1.0
                        logger.info("connected to adapter url=%s", self._url)
                        async for message in ws:
                            if message.type == aiohttp.WSMsgType.TEXT:
                                await self._on_frame(message.data)
                            elif message.type in (
                                aiohttp.WSMsgType.ERROR,
                                aiohttp.WSMsgType.CLOSE,
                                aiohttp.WSMsgType.CLOSED,
                            ):
                                break
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("adapter connection failed: %s", exc)
            finally:
                self._rpc.detach()
            if self._stopping:
                break
            await asyncio.sleep(self._backoff)
            self._backoff = min(self._backoff * 2, 30.0)

    async def _on_frame(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("adapter frame is not JSON: %r", raw[:200])
            return
        if not isinstance(payload, dict):
            logger.warning("adapter frame is not an object: %r", raw[:200])
            return
        if "post_type" not in payload and "echo" in payload:
            self._rpc.resolve(payload)
            return

        post_type = payload.get("post_type")
        if post_type == "meta_event":
            if payload.get("meta_event_type") == "adapter_ready":
                self._on_ready(payload)
            return
        if post_type == "message":
            self._enqueue(payload)

    def _enqueue(self, payload: dict[str, Any]) -> None:
        """Hand the frame to the worker so media downloads never block the socket."""
        try:
            self._inbound.put_nowait(payload)
        except asyncio.QueueFull:
            logger.warning("inbound queue full, dropping message")

    def _ensure_worker(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._inbound_worker())

    async def _inbound_worker(self) -> None:
        while True:
            payload = await self._inbound.get()
            try:
                await self._handle_message(payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("failed to process inbound message")

    def _on_ready(self, payload: dict[str, Any]) -> None:
        adapter = payload.get("adapter") or {}
        chat = adapter.get("chat") or {}
        kind = str(chat.get("kind") or "")
        chat_id = str(chat.get("id") or "")
        if kind in ("group", "dm") and chat_id:
            # The adapter owns the binding; adopt it (also covers a config file
            # created after this process started).
            self._chat_kind = kind
            self._chat_numeric = chat_id
        sha = str(adapter.get("config_sha") or "")
        if self._config_sha and sha and sha != self._config_sha:
            # Availability over strictness: log loudly, keep serving.
            logger.error("config mismatch adapter=%s plugin=%s", sha, self._config_sha)
        logger.info("adapter ready version=%s chat=%s", adapter.get("version"), self.chat_key)

    async def _handle_message(self, payload: dict[str, Any]) -> None:
        try:
            event = Event.model_validate(payload)
        except Exception as exc:
            logger.warning("dropping malformed event: %s", exc)
            return
        self._self_id = str(event.self_id or self._self_id)

        media, media_urls, media_types = await self._prepare_media(event)
        reply = await self._reply_context(event)
        text = render_event(event, event.self_id, media)
        if text is None:
            logger.debug("event rendered empty, dropping msg=%s", event.message_id)
            return

        sender = event.sender
        user_name = ""
        if sender is not None:
            user_name = sender.card or sender.nickname or ""
        source = self.build_source(
            chat_id=self.chat_key,
            chat_name=self.chat_key,
            chat_type="group" if self._chat_kind == "group" else "dm",
            user_id=str(event.user_id or ""),
            user_name=user_name,
            message_id=str(event.message_id or ""),
        )
        message_event = build_message_event(
            text=text,
            source=source,
            message_id=str(event.message_id or ""),
            media_urls=media_urls,
            media_types=media_types,
            reply=reply,
            raw=payload,
            internal=bool(event.adapter.internal) if event.adapter else False,
            timestamp=_event_timestamp(event.time),
        )
        await self.handle_message(message_event)

    async def _prepare_media(self, event: Event) -> tuple[list[MediaResult], list[str], list[str]]:
        media_segments = [s for s in segments.event_segments(event) if segments.media_kind(s)]
        if not media_segments:
            return [], [], []
        # Downloads run concurrently; the message is only rendered once they settle.
        results = list(await asyncio.gather(*(self._download(segment) for segment in media_segments)))
        urls = [result.path for result in results if result.path]
        types = [
            segments.media_kind(segment) or ""
            for segment, result in zip(media_segments, results, strict=False)
            if result.path
        ]
        return results, urls, types

    async def _download(self, segment: dict[str, Any]) -> MediaResult:
        kind = segments.media_kind(segment)
        url = str(segments.data_of(segment).get("url") or "")
        if kind is None or not url or self._media is None:
            return MediaResult()
        try:
            path, _content_type, _size = await self._media.fetch_to_cache(
                url, _SUFFIX_BY_KIND.get(kind, ".bin"),
            )
            return MediaResult(path=path)
        except MediaError as exc:
            logger.warning("media download failed kind=%s: %s", kind, exc)
            return MediaResult(failed=True)
        except Exception:
            logger.exception("media download crashed kind=%s", kind)
            return MediaResult(failed=True)

    async def _reply_context(self, event: Event) -> tuple[str, str, str, str] | None:
        reply_id = segments.extract_reply_id(segments.event_segments(event))
        if not reply_id:
            return None
        try:
            data = await self.api("get_msg", {"message_id": reply_id})
        except ChatbotError as exc:
            logger.warning("get_msg failed reply_id=%s: %s", reply_id, exc)
            return None
        if not isinstance(data, dict):
            return None
        quoted = Event.model_validate({**data, "post_type": "message", "self_id": event.self_id})
        body = flatten(segments.event_segments(quoted), event.self_id)
        if not body:
            return None
        sender = quoted.sender
        name = ""
        if sender is not None:
            name = sender.card or sender.nickname or ""
        seq = quoted.real_seq if quoted.real_seq not in (None, "") else quoted.message_id
        prefix = segments.format_sender_prefix(name, quoted.user_id, seq)
        return reply_id, f"{prefix}: {body}", str(quoted.user_id or ""), name

    async def api(self, action: str, params: dict[str, Any], timeout: float | None = None) -> Any:
        try:
            response = await self._rpc.call(action, params, timeout or self._call_timeout)
        except RpcUnavailable as exc:
            raise RpcError(action, str(exc)) from exc
        if str(response.get("status") or "ok") != "ok":
            wording = response.get("wording") or response.get("message") or "failed"
            raise RpcError(
                action,
                str(wording),
                reason=str(response.get("reason") or ""),
                retcode=int(response.get("retcode") or 0),
            )
        return response.get("data")

    async def send(
        self, chat_id: str, content: str, reply_to: str | None = None, metadata: Any = None,
    ) -> SendResult:
        """Abstract-method implementation: text is the only content Hermes routes here."""
        text = to_plain(content) if self._strip else content
        if not text:
            return SendResult(success=False, error="empty message", retryable=False, raw_response={"final": True})
        chunks = self.truncate_message(text, max_length=self.MAX_MESSAGE_LENGTH) or [text]
        message_segments: list[dict[str, Any]] = [segments.text(chunk) for chunk in chunks]
        if reply_to:
            message_segments.insert(0, segments.reply(reply_to))
        return await self._send(message_segments)

    async def send_text(
        self, chat_id: str, text: str, reply_to: str | None = None, metadata: Any = None,
    ) -> SendResult:
        return await self.send(chat_id, text, reply_to=reply_to, metadata=metadata)

    async def send_image(
        self, chat_id: str, image_url: str, caption: str | None = None,
        reply_to: str | None = None, metadata: Any = None,
    ) -> SendResult:
        return await self._send_media(segments.image(image_url), caption, reply_to)

    async def send_image_file(
        self, chat_id: str, image_path: str, caption: str | None = None,
        reply_to: str | None = None, metadata: Any = None, **kwargs: Any,
    ) -> SendResult:
        """Local image file; Hermes routes MEDIA:/path here, not to send_image."""
        return await self._send_media(segments.image(image_path), caption, reply_to)

    async def send_voice(
        self, chat_id: str, audio_path: str, caption: str | None = None,
        reply_to: str | None = None, metadata: Any = None, **kwargs: Any,
    ) -> SendResult:
        return await self._send_media(segments.record(audio_path), caption, reply_to)

    async def send_video(
        self, chat_id: str, video_path: str, caption: str | None = None,
        reply_to: str | None = None, metadata: Any = None, **kwargs: Any,
    ) -> SendResult:
        return await self._send_media(segments.video(video_path), caption, reply_to)

    async def _send_media(
        self, segment: dict[str, Any], caption: str | None, reply_to: str | None,
    ) -> SendResult:
        message_segments: list[dict[str, Any]] = [segment]
        if caption:
            message_segments.append(segments.text(caption))
        if reply_to:
            message_segments.insert(0, segments.reply(reply_to))
        return await self._send(message_segments)

    async def send_document(
        self, chat_id: str, file_path: str, caption: str | None = None,
        file_name: str | None = None, reply_to: str | None = None, metadata: Any = None, **kwargs: Any,
    ) -> SendResult:
        name = file_name or file_path.rsplit("/", 1)[-1]
        # Outbound file segments use ``file`` (path/URL) + ``name`` — not the
        # inbound ``file_id`` shape that ``segments.file`` builds.
        message_segments: list[dict[str, Any]] = [{"type": "file", "data": {"file": file_path, "name": name}}]
        if caption:
            message_segments.append(segments.text(caption))
        if reply_to:
            message_segments.insert(0, segments.reply(reply_to))
        return await self._send(message_segments)

    async def get_chat_info(self, chat_id: str) -> dict[str, Any]:
        """Required by BasePlatformAdapter; used for display names."""
        if chat_id.startswith("group:"):
            try:
                data = await self.api("get_group_info", {"group_id": int(chat_id.split(":", 1)[1])})
            except ChatbotError:
                data = None
            name = str(data.get("group_name") or "") if isinstance(data, dict) else ""
            return {"name": name or chat_id, "type": "group", "chat_id": chat_id}
        try:
            data = await self.api("get_stranger_info", {"user_id": int(chat_id.split(":", 1)[1])})
        except (ChatbotError, ValueError):
            data = None
        name = str(data.get("nickname") or "") if isinstance(data, dict) else ""
        return {"name": name or chat_id, "type": "dm", "chat_id": chat_id}

    async def _send(self, message_segments: list[dict[str, Any]]) -> SendResult:
        # A file segment goes through QQ's upload path and can take minutes.
        has_file = any(segment.get("type") == "file" for segment in message_segments)
        timeout = self._upload_timeout if has_file else self._call_timeout
        try:
            if self._chat_kind == "group":
                data = await self.api(
                    "send_group_msg",
                    {"group_id": self._chat_numeric, "message": message_segments},
                    timeout=timeout,
                )
            else:
                data = await self.api(
                    "send_private_msg",
                    {"user_id": self._chat_numeric, "message": message_segments},
                    timeout=timeout,
                )
        except RpcError as exc:
            final = not exc.retryable
            return SendResult(
                success=False,
                error=str(exc),
                retryable=exc.retryable,
                raw_response={"final": True} if final else None,
            )
        except Exception as exc:  # noqa: BLE001 - reported as a retryable failure
            return SendResult(success=False, error=str(exc), retryable=True)

        message_id = ""
        if isinstance(data, dict):
            message_id = str(data.get("message_id") or "")
        return SendResult(success=True, message_id=message_id)

    def _send_retry_is_final(self, result: SendResult) -> bool:
        raw = result.raw_response
        return isinstance(raw, dict) and bool(raw.get("final"))

    async def _send_plain_fallback(
        self, chat_id: str, content: str, *, reply_to: str | None = None, metadata: Any = None,
    ) -> SendResult:
        # Hermes retries a non-retryable failure as plain text with a banner.
        # For QQ that would be a fourth send of the same content, so refuse.
        return SendResult(
            success=False,
            error="plain-text fallback disabled",
            retryable=False,
            raw_response={"final": True},
        )
