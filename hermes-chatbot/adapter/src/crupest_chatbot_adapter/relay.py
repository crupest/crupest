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
from crupest_chatbot_core.config import FeaturesConfig, LimitsConfig
from crupest_chatbot_core.ratelimit import Cooldowns
from crupest_chatbot_core.schema import Event

from . import policy
from .policy import Binding, Context
from .seq import SeqMap
from .window import Window

logger = logging.getLogger(__name__)

#: Sent to the bound chat when Hermes stays disconnected.
DISCONNECT_NOTICE = "Hermes gateway disconnected. Please check server state."

_COOLDOWN_KEYS = {
    "send_poke": "poke",
    "upload_group_file": "upload",
    "upload_private_file": "upload",
    "send_group_forward_msg": "forward",
    "send_private_forward_msg": "forward",
}


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


def _has_at_all(params: dict[str, Any]) -> bool:
    message = params.get("message")
    if not isinstance(message, list):
        return False
    return any(
        isinstance(segment, dict)
        and segment.get("type") == "at"
        and str((segment.get("data") or {}).get("qq") or "") == "all"
        for segment in message
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
        features: FeaturesConfig | None = None,
        limits: LimitsConfig | None = None,
        clock: Any = None,
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
        self._features = features or FeaturesConfig()
        self._limits = limits or LimitsConfig()
        self._context = Context()
        self._clock = clock or time.monotonic
        self._role_cache: tuple[float, str] | None = None
        windows: dict[str, float] = {
            "poke": self._limits.poke_cooldown_seconds,
            "at_all": self._limits.at_all_cooldown_seconds,
            "forward": self._limits.forward_cooldown_seconds,
            "upload": self._limits.upload_cooldown_seconds,
        }
        self._cooldowns = Cooldowns(windows, clock=self._clock)

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
        if event.post_type == "message":
            self._remember(event)
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

    def _remember(self, event: Event) -> None:
        """Track the bot's own id for actions that need it."""
        self._context = Context(
            self_id=str(event.self_id or self._context.self_id),
        )

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
            prepared = policy.authorize(
                action, params, self._binding, self_id=self_id,
                context=self._context, features=self._features, limits=self._limits,
            )
            if action in policy.UPLOAD_ACTIONS:
                policy.check_upload(action, prepared, self._limits)
            if action in policy.FORWARD_ACTIONS:
                self._check_forward_ids(action, prepared)
            self._check_cooldown(action, prepared)
            if _has_at_all(prepared):
                await self._check_at_all_role(action)
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
        logger.info(
            "action ok action=%s echo=%s segments=%s",
            action, echo, self._segment_kinds(prepared),
        )
        return {"status": "ok", "retcode": errors.RETCODE_OK, "data": upstream.get("data"), "echo": echo}

    def _check_forward_ids(self, action: str, prepared: dict[str, Any]) -> None:
        """Only messages the adapter has seen may be forwarded (no synthetic nodes)."""
        for node in prepared.get("messages") or []:
            message_id = str((node.get("data") or {}).get("id") or "")
            if not self._seq.known(message_id):
                raise errors.PolicyError(
                    action, errors.REASON_POLICY_DENIED, "只能转发适配器收到过的消息",
                )

    def _check_cooldown(self, action: str, prepared: dict[str, Any]) -> None:
        key = _COOLDOWN_KEYS.get(action)
        if key is not None and not self._cooldowns.allow(key):
            raise errors.PolicyError(action, errors.REASON_POLICY_DENIED, "操作太频繁，稍后再试")
        if _has_at_all(prepared) and not self._cooldowns.allow("at_all"):
            raise errors.PolicyError(action, errors.REASON_POLICY_DENIED, "@全体太频繁，稍后再试")

    async def _check_at_all_role(self, action: str) -> None:
        """Refuse @all before sending when the bot is not owner/admin.

        NapCat reports a generic timeout for this case and may already have sent
        the message, so checking the role first is the only way to avoid both a
        misleading error and a duplicate on Hermes' retry.
        """
        group_id = self._binding.group_id
        self_id = str(self._self_id_provider() or "") if self._self_id_provider else ""
        if group_id is None or not self_id:
            raise errors.PolicyError(
                action, errors.REASON_POLICY_DENIED, "无法确认群管理员身份，暂时不能 @全体",
            )
        now = self._clock()
        if self._role_cache is not None and now - self._role_cache[0] < 60.0:
            role = self._role_cache[1]
        else:
            response = await self._napcat.call(
                "get_group_member_info",
                {"group_id": group_id, "user_id": self_id, "no_cache": False},
                self._call_timeout,
            )
            status = str(response.get("status") or "ok")
            retcode = int(response.get("retcode") or 0)
            data = response.get("data")
            if status != "ok" or retcode != 0 or not isinstance(data, dict):
                raise errors.PolicyError(
                    action, errors.REASON_POLICY_DENIED, "无法确认群管理员身份，暂时不能 @全体",
                )
            role = str(data.get("role") or "")
            self._role_cache = (now, role)
        if role not in ("owner", "admin"):
            raise errors.PolicyError(
                action, errors.REASON_POLICY_DENIED, "当前账号不是群管理员，不能 @全体",
            )

    @staticmethod
    def _segment_kinds(prepared: dict[str, Any]) -> list[str]:
        message = prepared.get("message")
        if not isinstance(message, list):
            return []
        return [str(segment.get("type") or "?") for segment in message if isinstance(segment, dict)]

    async def _send(self, ws: Any, payload: dict[str, Any]) -> None:
        try:
            await ws.send_json(payload)
        except Exception as exc:
            logger.warning("plugin send failed: %s", exc)
