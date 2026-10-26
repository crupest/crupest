"""The plugin side: a WebSocket server the Hermes plugin dials into.

The wire is plain OneBot 11: the plugin sends ``{action, params, echo}`` and
gets ``{status, retcode, reason?, wording?, data?, echo}`` back.  Every failure
is a response frame — nothing is raised at the connection layer.
"""
from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import time
from typing import Any

from aiohttp import WSMsgType, web
from crupest_chatbot_core import errors
from crupest_chatbot_core.schema import Event

from . import policy
from .policy import Binding
from .seq import SeqMap
from .window import Window

logger = logging.getLogger(__name__)

#: Sent to the bound chat when Hermes stays disconnected.
DISCONNECT_NOTICE = "Hermes gateway disconnected. Please check server state."


def _uses_upload_timeout(action: str, params: dict[str, Any]) -> bool:
    """File uploads run through NapCat's slow path, even when sent as a message segment."""
    if action in policy.UPLOAD_ACTIONS:
        return True
    if action not in policy.MESSAGE_ACTIONS:
        return False
    message = params.get("message")
    return isinstance(message, list) and any(
        isinstance(segment, dict) and segment.get("type") == "file" for segment in message
    )


class PluginLink:
    def __init__(
        self,
        *,
        token: str,
        path: str,
        napcat: Any,
        binding: Binding,
        seq: SeqMap,
        window: Window,
        call_timeout: float,
        upload_timeout: float,
        version: str,
        config_sha: str,
        self_id_provider: Any = None,
        heartbeat: float = 30.0,
        disconnect_grace: float = 30.0,
        notice_cooldown: float = 600.0,
    ) -> None:
        self._token = token
        self._path = path
        self._napcat = napcat
        self._binding = binding
        self._seq = seq
        self._window = window
        self._call_timeout = call_timeout
        self._upload_timeout = upload_timeout
        self._version = version
        self._config_sha = config_sha
        self._self_id_provider = self_id_provider
        self._heartbeat = heartbeat
        self._ws: web.WebSocketResponse | None = None
        self._disconnect_grace = disconnect_grace
        self._notice_cooldown = notice_cooldown
        self._last_notice: float | None = None
        self._notice_task: asyncio.Task[None] | None = None

    @property
    def path(self) -> str:
        return self._path

    @property
    def connected(self) -> bool:
        return self._ws is not None and not self._ws.closed

    def ready_frame(self) -> dict[str, Any]:
        return {
            "post_type": "meta_event",
            "meta_event_type": "adapter_ready",
            "adapter": {
                "version": self._version,
                "config_sha": self._config_sha,
                "chat": {"kind": self._binding.kind, "id": str(self._binding.group_id or self._binding.user_id)},
            },
        }

    async def handle_ws(self, request: Any) -> web.StreamResponse:
        from .napcat import presented_token, token_matches

        if not token_matches(presented_token(request), self._token):
            logger.warning("plugin WS unauthorized remote=%s", getattr(request, "remote", "?"))
            return web.json_response({"error": "unauthorized"}, status=401)

        ws = web.WebSocketResponse(heartbeat=self._heartbeat)
        await ws.prepare(request)
        if self._ws is not None and not self._ws.closed:
            logger.warning("plugin WS: new connection replaces the active one")
            with contextlib.suppress(Exception):
                await self._ws.close()
        self._ws = ws
        logger.info("plugin WS connected remote=%s", getattr(request, "remote", "?"))
        await self._send(ws, self.ready_frame())

        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    await self._on_frame(ws, message.data)
                elif message.type in (WSMsgType.ERROR, WSMsgType.CLOSE, WSMsgType.CLOSED):
                    break
        finally:
            # Only the active connection may clear it; a newer one may have
            # replaced us while the old socket was still closing.
            if self._ws is ws:
                self._ws = None
            self._schedule_disconnect_notice()
            logger.info("plugin WS disconnected code=%s", ws.close_code)
        return ws

    def _schedule_disconnect_notice(self) -> None:
        if self._notice_task is not None and not self._notice_task.done():
            self._notice_task.cancel()
        self._notice_task = asyncio.create_task(
            self._notify_disconnect(), name="chatbot-disconnect-notice",
        )

    async def _notify_disconnect(self) -> None:
        """Tell the bound chat when Hermes stays gone, with a grace period."""
        await asyncio.sleep(self._disconnect_grace)
        if self.connected or not self._napcat.connected:
            return
        now = time.monotonic()
        if self._last_notice is not None and now - self._last_notice < self._notice_cooldown:
            return
        if self._binding.group_id is not None:
            action: str = "send_group_msg"
            params: dict[str, Any] = {"group_id": self._binding.group_id}
        elif self._binding.user_id is not None:
            action = "send_private_msg"
            params = {"user_id": self._binding.user_id}
        else:
            return
        params["message"] = [{"type": "text", "data": {"text": DISCONNECT_NOTICE}}]
        try:
            await self._napcat.call(action, params, 10.0)
        except Exception as exc:  # noqa: BLE001 - notification is best effort
            logger.warning("disconnect notice failed: %s", exc)
            return
        self._last_notice = now
        logger.info("sent disconnect notice chat=%s", self._binding.chat_id)

    async def send_event(self, event: Event) -> bool:
        ws = self._ws
        if ws is None or ws.closed:
            logger.debug("no plugin connection, dropping post_type=%s", event.post_type)
            return False
        try:
            await ws.send_json(event.model_dump(mode="json", exclude_none=True))
            return True
        except Exception as exc:
            logger.warning("send_event failed: %s", exc)
            return False

    async def _on_frame(self, ws: Any, raw: str) -> None:
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            logger.warning("plugin frame is not JSON: %r", raw[:200])
            return
        if not isinstance(payload, dict):
            logger.warning("plugin frame is not an object: %r", raw[:200])
            return

        action = payload.get("action")
        if not isinstance(action, str) or not action:
            logger.debug("plugin frame without action: %r", raw[:200])
            return
        echo = str(payload.get("echo") or "")
        params = payload.get("params")
        if not isinstance(params, dict):
            params = {}

        response = await self._execute(action, params, echo)
        await self._send(ws, response)

    async def _execute(self, action: str, params: dict[str, Any], echo: str) -> dict[str, Any]:
        try:
            self_id = str(self._self_id_provider() or "") if self._self_id_provider else ""
            prepared = policy.authorize(action, params, self._binding, self_id=self_id)
            prepared = self._seq.apply(action, prepared)
            timeout = self._upload_timeout if _uses_upload_timeout(action, prepared) else self._call_timeout
            upstream = await self._napcat.call(action, prepared, timeout)
        except errors.ChatbotError as exc:
            logger.warning("action failed action=%s echo=%s reason=%s", action, echo, exc.reason)
            return exc.to_response(echo)
        except Exception as exc:  # noqa: BLE001 - last line of defence, still reported
            logger.exception("action crashed action=%s echo=%s", action, echo)
            return errors.TransportError(f"{action}: {exc}").to_response(echo)

        status = str(upstream.get("status") or "ok")
        retcode = int(upstream.get("retcode") or 0)
        if status != "ok" or retcode != 0:
            wording = upstream.get("wording") or upstream.get("message") or f"{action} 失败 (retcode={retcode})"
            logger.warning("upstream failed action=%s retcode=%s wording=%s", action, retcode, wording)
            return {
                "status": "failed",
                "retcode": retcode or errors.RETCODE_TRANSPORT,
                "reason": errors.REASON_NAPCAT_FAILED,
                "wording": str(wording),
                "data": upstream.get("data"),
                "echo": echo,
            }

        if action in policy.WINDOW_ACTIONS:
            self._window.touch()
        return {"status": "ok", "retcode": errors.RETCODE_OK, "data": upstream.get("data"), "echo": echo}

    async def _send(self, ws: Any, payload: dict[str, Any]) -> None:
        try:
            await ws.send_json(payload)
        except Exception as exc:
            logger.warning("plugin send failed: %s", exc)
