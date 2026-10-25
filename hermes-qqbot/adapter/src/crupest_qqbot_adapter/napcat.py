"""The NapCat side: an inbound reverse-WebSocket plus a request/response client.

One connection only.  Frames are classified *synchronously* on the receive
path — a response resolves its future immediately, everything else is queued
for the single ordered worker.  That ordering is what stops an event handler
from waiting on a response that is stuck behind itself in the queue.
"""
from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import uuid
from typing import Any

from aiohttp import WSMsgType, web
from crupest_qqbot_core.errors import SchemaError, TransportError, UpstreamTimeout
from crupest_qqbot_core.schema import Event, parse_frame

logger = logging.getLogger(__name__)


def presented_token(request: Any) -> str:
    query = getattr(request, "query", None) or {}
    token = str(query.get("access_token") or query.get("token") or "")
    if token:
        return token
    headers = getattr(request, "headers", None) or {}
    authorization = str(headers.get("Authorization") or "")
    if authorization.lower().startswith("bearer "):
        return authorization[7:].strip()
    return ""


def token_matches(presented: str, expected: str) -> bool:
    if not expected:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


class NapCatLink:
    def __init__(
        self,
        *,
        token: str,
        path: str,
        on_event: Any,
        queue_size: int = 1024,
        heartbeat: float = 30.0,
    ) -> None:
        self._token = token
        self._path = path
        self._on_event = on_event
        self._heartbeat = heartbeat
        self._queue: asyncio.Queue[Event] = asyncio.Queue(maxsize=queue_size)
        self._worker: asyncio.Task[None] | None = None
        self._ws: web.WebSocketResponse | None = None
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}
        self._closed = False

    @property
    def path(self) -> str:
        return self._path

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    async def handle_ws(self, request: Any) -> web.StreamResponse:
        if not token_matches(presented_token(request), self._token):
            logger.warning("OneBot WS unauthorized remote=%s", getattr(request, "remote", "?"))
            return web.json_response({"error": "unauthorized"}, status=401)

        ws = web.WebSocketResponse(heartbeat=self._heartbeat)
        await ws.prepare(request)
        if self._ws is not None and not self._ws.closed:
            logger.warning("OneBot WS: new connection replaces the active one")
            with contextlib.suppress(Exception):
                await self._ws.close()
        self._ws = ws
        self._ensure_worker()
        logger.info("OneBot WS connected remote=%s", getattr(request, "remote", "?"))

        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    self._accept(message.data)
                elif message.type in (WSMsgType.ERROR, WSMsgType.CLOSE, WSMsgType.CLOSED):
                    break
        finally:
            if self._ws is ws:
                self._ws = None
                self._fail_pending("NapCat 连接已断开")
            logger.info("OneBot WS disconnected code=%s", ws.close_code)
        return ws

    def _accept(self, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("OneBot frame is not JSON: %r", raw[:200])
            return

        if isinstance(payload, dict):
            echo = payload.get("echo")
            if echo is not None and "post_type" not in payload and str(echo) in self._pending:
                self._resolve(str(echo), payload)
                return

        try:
            frame = parse_frame(raw)
        except SchemaError as exc:
            logger.warning("OneBot frame dropped: %s path=%s raw=%r", exc.kind, exc.path, exc.raw_excerpt)
            return

        if isinstance(frame, Event):
            self._dispatch(frame)
        else:
            logger.debug("unexpected response frame echo=%s", frame.echo)

    def _resolve(self, echo: str, payload: dict[str, Any]) -> None:
        future = self._pending.pop(echo, None)
        if future is not None and not future.done():
            future.set_result(payload)

    def _dispatch(self, event: Event) -> None:
        try:
            self._queue.put_nowait(event)
        except asyncio.QueueFull:
            logger.warning("event queue full, dropping event post_type=%s", event.post_type)

    def _ensure_worker(self) -> None:
        if self._worker is None or self._worker.done():
            self._worker = asyncio.create_task(self._worker_loop())

    async def _worker_loop(self) -> None:
        while not self._closed:
            event = await self._queue.get()
            try:
                await self._on_event(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("event handler failed post_type=%s", event.post_type)

    async def call(self, action: str, params: dict[str, Any], timeout: float) -> dict[str, Any]:
        ws = self._ws
        if ws is None or ws.closed:
            raise TransportError("NapCat 未连接")
        echo = uuid.uuid4().hex
        future: asyncio.Future[dict[str, Any]] = asyncio.get_running_loop().create_future()
        self._pending[echo] = future
        logger.debug("call action=%s echo=%s", action, echo)
        try:
            await ws.send_json({"action": action, "params": params, "echo": echo})
        except Exception as exc:
            self._pending.pop(echo, None)
            raise TransportError(f"{action}: 发送失败 {exc}") from exc
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except TimeoutError:
            raise UpstreamTimeout(action, timeout) from None
        finally:
            self._pending.pop(echo, None)

    def _fail_pending(self, reason: str) -> None:
        pending, self._pending = self._pending, {}
        for future in pending.values():
            if not future.done():
                future.set_exception(TransportError(reason))

    async def stop(self) -> None:
        self._closed = True
        self._fail_pending("NapCat 连接已关闭")
        if self._worker is not None:
            self._worker.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._worker
            self._worker = None
        if self._ws is not None and not self._ws.closed:
            with contextlib.suppress(Exception):
                await self._ws.close()
