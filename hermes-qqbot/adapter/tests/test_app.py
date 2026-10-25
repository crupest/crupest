from __future__ import annotations

from adapter_helpers import SELF_ID, make_event
from crupest_qqbot_adapter.app import AdapterService
from crupest_qqbot_core.config import ChatConfig, Config, NotifyConfig, Secrets
from crupest_qqbot_core.schema import Event


class FakePlugin:
    def __init__(self) -> None:
        self.events: list[Event] = []

    async def send_event(self, event: Event) -> bool:
        self.events.append(event)
        return True


def _service(notify: NotifyConfig | None = None) -> AdapterService:
    config = Config(chat=ChatConfig(group_id=123456), notify=notify or NotifyConfig())
    service = AdapterService(config, Secrets(onebot_ws_token="a", plugin_ws_token="b"))
    service._plugin = FakePlugin()  # type: ignore[assignment]
    return service


async def test_mention_is_forwarded() -> None:
    service = _service()
    await service._on_event(make_event())
    assert len(service._plugin.events) == 1  # type: ignore[attr-defined]
    assert service._plugin.events[0].message_id == 1234  # type: ignore[attr-defined]


async def test_plain_group_message_is_dropped() -> None:
    service = _service()
    event = make_event(message=[{"type": "text", "data": {"text": "闲聊"}}])
    await service._on_event(event)
    assert service._plugin.events == []  # type: ignore[attr-defined]


async def test_other_group_is_dropped() -> None:
    service = _service()
    await service._on_event(make_event(group_id=999))
    assert service._plugin.events == []  # type: ignore[attr-defined]


async def test_poke_becomes_internal_event() -> None:
    service = _service(NotifyConfig(poke=True))
    event = make_event(post_type="notice", notice_type="notify", sub_type="poke", target_id=SELF_ID)
    await service._on_event(event)
    forwarded = service._plugin.events[0]  # type: ignore[attr-defined]
    assert forwarded.post_type == "message"
    assert forwarded.adapter is not None
    assert forwarded.adapter.internal is True
    assert forwarded.adapter.origin == "poke"


async def test_notice_switch_off_is_dropped() -> None:
    service = _service()
    event = make_event(post_type="notice", notice_type="notify", sub_type="poke", target_id=SELF_ID)
    await service._on_event(event)
    assert service._plugin.events == []  # type: ignore[attr-defined]


async def test_seq_is_recorded_before_filtering() -> None:
    service = _service()
    event = make_event(message=[{"type": "text", "data": {"text": "闲聊"}}])
    await service._on_event(event)
    assert service._seq.resolve(8821) == "1234"


def test_build_apps_exposes_both_paths() -> None:
    config = Config(chat=ChatConfig(group_id=123456))
    service = AdapterService(config, Secrets(onebot_ws_token="a", plugin_ws_token="b"))
    apps = service.build_apps()
    assert len(apps) == 2
    paths = {route.resource.canonical for app, _ in apps for route in app.router.routes()}
    assert "/onebot" in paths
    assert "/hermes" in paths
