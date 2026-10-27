"""Service wiring: gate inbound events, expose both WebSocket endpoints."""
from __future__ import annotations

import asyncio
import logging

from aiohttp import web
from crupest_chatbot_core import __version__
from crupest_chatbot_core.config import Config, Secrets
from crupest_chatbot_core.logging import preview
from crupest_chatbot_core.notice import render_notice
from crupest_chatbot_core.schema import Event

from . import policy
from .napcat import NapCatLink
from .policy import Binding
from .relay import PluginLink
from .seq import SeqMap
from .window import Window

logger = logging.getLogger(__name__)


class AdapterService:
    def __init__(self, config: Config, secrets: Secrets) -> None:
        self._config = config
        self._binding = Binding(group_id=config.chat.group_id, user_id=config.chat.user_id)
        self._window = Window(config.chat.active_window_seconds)
        self._seq = SeqMap()
        self._self_id = ""
        self._napcat = NapCatLink(
            token=secrets.onebot_ws_token,
            path=config.adapter.onebot_path,
            on_event=self._on_event,
            queue_size=config.adapter.queue_size,
        )
        self._plugin = PluginLink(
            token=secrets.plugin_ws_token,
            path=config.adapter.plugin_path,
            napcat=self._napcat,
            binding=self._binding,
            seq=self._seq,
            window=self._window,
            call_timeout=config.adapter.call_timeout_seconds,
            upload_timeout=config.adapter.upload_timeout_seconds,
            version=__version__,
            config_sha=config.sha,
            self_id_provider=lambda: self._self_id,
            features=config.features,
            limits=config.limits,
        )

    @property
    def binding(self) -> Binding:
        return self._binding

    async def _on_event(self, event: Event) -> None:
        # Record before filtering: the model may react to an older message it
        # only saw through read_history.
        self._seq.record_event(event)
        if event.self_id not in (None, ""):
            # Needed by set_group_card, which may only ever target the bot itself.
            self._self_id = str(event.self_id)

        decision = policy.decide_event(event, self._binding, self._window, self._config.notify)
        message_id = event.message_id if event.message_id is not None else event.real_seq
        if not decision.forward:
            logger.debug(
                "event dropped reason=%s post_type=%s msg=%s preview=%s",
                decision.reason, event.post_type, message_id,
                preview(self._event_text(event), self._config.logging.message_preview_chars),
            )
            return

        if event.post_type == "notice":
            synthetic = render_notice(event, event.self_id, self._binding.group_id)
            if synthetic is None:
                logger.debug("notice not rendered notice_type=%s sub_type=%s", event.notice_type, event.sub_type)
                return
            event = Event.model_validate(synthetic)

        logger.info(
            "event forwarded reason=%s chat=%s msg=%s preview=%s",
            decision.reason, self._binding.chat_id, message_id,
            preview(self._event_text(event), self._config.logging.message_preview_chars),
        )
        await self._plugin.send_event(event)

    @staticmethod
    def _event_text(event: Event) -> str:
        from crupest_chatbot_core import segments

        return "".join(
            str(segments.data_of(segment).get("text", ""))
            for segment in segments.event_segments(event)
            if segment.get("type") == "text"
        )

    def build_apps(self) -> list[tuple[web.Application, int]]:
        napcat_app = web.Application()
        napcat_app.router.add_get(self._napcat.path, self._napcat.handle_ws)
        plugin_app = web.Application()
        plugin_app.router.add_get(self._plugin.path, self._plugin.handle_ws)
        return [
            (napcat_app, self._config.adapter.onebot_port),
            (plugin_app, self._config.adapter.plugin_port),
        ]

    async def run(self) -> None:
        runners: list[web.AppRunner] = []
        try:
            for app, port in self.build_apps():
                runner = web.AppRunner(app)
                await runner.setup()
                await web.TCPSite(runner, "0.0.0.0", port).start()
                runners.append(runner)
                logger.info("listening on 0.0.0.0:%d", port)
            logger.info("adapter ready chat=%s config_sha=%s", self._binding.chat_id, self._config.sha)
            await asyncio.Event().wait()
        finally:
            for runner in runners:
                await runner.cleanup()
            await self._napcat.stop()
