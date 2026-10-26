from __future__ import annotations

import json

import pytest
from crupest_chatbot_adapter.policy import Binding
from crupest_chatbot_adapter.relay import PluginLink
from crupest_chatbot_adapter.seq import SeqMap
from crupest_chatbot_adapter.window import Window
from crupest_chatbot_core.errors import REASON_NAPCAT_FAILED, REASON_POLICY_DENIED, TransportError


class FakeNapCat:
    def __init__(self, response: dict | None = None, error: Exception | None = None) -> None:
        self.calls: list[tuple[str, dict, float]] = []
        self.response = response if response is not None else {"status": "ok", "retcode": 0, "data": {"message_id": 1}}
        self.error = error
        self.connected = True

    async def call(self, action: str, params: dict, timeout: float) -> dict:
        self.calls.append((action, params, timeout))
        if self.error is not None:
            raise self.error
        return self.response


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _link(
    napcat: FakeNapCat, window: Window | None = None, seq: SeqMap | None = None, self_id: str = "",
    *, grace: float = 100.0, cooldown: float = 0.0,
) -> PluginLink:
    return PluginLink(
        token="tok",
        path="/hermes",
        napcat=napcat,
        binding=Binding(group_id=123456),
        seq=seq or SeqMap(),
        window=window or Window(300),
        call_timeout=60,
        upload_timeout=600,
        version="0.1.0",
        config_sha="deadbeefdeadbeef",
        self_id_provider=lambda: self_id,
        disconnect_grace=grace,
        notice_cooldown=cooldown,
    )


async def _send(link: PluginLink, payload: dict) -> dict:
    ws = FakeWS()
    await link._on_frame(ws, json.dumps(payload))
    assert len(ws.sent) == 1
    return ws.sent[0]


def test_ready_frame() -> None:
    frame = _link(FakeNapCat()).ready_frame()
    assert frame["post_type"] == "meta_event"
    assert frame["meta_event_type"] == "adapter_ready"
    assert frame["adapter"]["config_sha"] == "deadbeefdeadbeef"
    assert frame["adapter"]["chat"] == {"kind": "group", "id": "123456"}


async def test_action_is_forwarded_and_target_pinned() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    response = await _send(link, {"action": "send_group_msg", "params": {"message": []}, "echo": "e1"})
    assert response == {"status": "ok", "retcode": 0, "data": {"message_id": 1}, "echo": "e1"}
    assert napcat.calls[0][0] == "send_group_msg"
    assert napcat.calls[0][1]["group_id"] == 123456
    assert napcat.calls[0][2] == 60


async def test_upload_uses_long_timeout() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    await _send(link, {"action": "upload_group_file", "params": {"file": "/x", "name": "x"}, "echo": "e"})
    assert napcat.calls[0][2] == 600


async def test_file_segment_uses_upload_timeout() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    message = [{"type": "file", "data": {"file": "/opt/data/share/x"}}]
    await _send(
        link,
        {"action": "send_group_msg", "params": {"group_id": 123456, "message": message}, "echo": "e"},
    )
    assert napcat.calls[0][2] == 600


async def test_unknown_action_is_refused() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    response = await _send(link, {"action": "set_group_ban", "params": {}, "echo": "e"})
    assert response["status"] == "failed"
    assert response["reason"] == REASON_POLICY_DENIED
    assert napcat.calls == []


async def test_target_mismatch_is_refused() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    response = await _send(link, {"action": "send_group_msg", "params": {"group_id": 999, "message": []}, "echo": "e"})
    assert response["status"] == "failed"
    assert napcat.calls == []


async def test_upstream_failure_keeps_napcat_wording() -> None:
    napcat = FakeNapCat(response={"status": "failed", "retcode": 1200, "wording": "Timeout: NTEvent"})
    link = _link(napcat)
    response = await _send(link, {"action": "send_group_msg", "params": {"message": []}, "echo": "e"})
    assert response["status"] == "failed"
    assert response["retcode"] == 1200
    assert response["reason"] == REASON_NAPCAT_FAILED
    assert response["wording"] == "Timeout: NTEvent"


async def test_transport_error_becomes_failure_frame() -> None:
    napcat = FakeNapCat(error=TransportError("gone"))
    link = _link(napcat)
    response = await _send(link, {"action": "send_group_msg", "params": {"message": []}, "echo": "e"})
    assert response["status"] == "failed"
    assert response["reason"] == "not_connected"


async def test_success_touches_window() -> None:
    clock = Clock()
    window = Window(300, clock=clock)
    link = _link(FakeNapCat(), window=window)
    assert window.active() is False
    await _send(link, {"action": "send_group_msg", "params": {"message": []}, "echo": "e"})
    assert window.active() is True


async def test_failure_does_not_touch_window() -> None:
    window = Window(300, clock=Clock())
    napcat = FakeNapCat(response={"status": "failed", "retcode": 1})
    link = _link(napcat, window=window)
    await _send(link, {"action": "send_group_msg", "params": {"message": []}, "echo": "e"})
    assert window.active() is False


async def test_read_action_does_not_touch_window() -> None:
    window = Window(300, clock=Clock())
    link = _link(FakeNapCat(), window=window)
    await _send(link, {"action": "get_login_info", "params": {}, "echo": "e"})
    assert window.active() is False


async def test_seq_is_translated() -> None:
    seq = SeqMap()
    seq.record(8821, 4512)
    napcat = FakeNapCat()
    link = _link(napcat, seq=seq)
    await _send(link, {
        "action": "set_msg_emoji_like",
        "params": {"real_seq": 8821, "emoji_id": "124"},
        "echo": "e",
    })
    assert napcat.calls[0][1] == {"message_id": "4512", "emoji_id": "124"}


async def test_invalid_json_is_ignored() -> None:
    link = _link(FakeNapCat())
    ws = FakeWS()
    await link._on_frame(ws, "{not json")
    assert ws.sent == []


async def test_frame_without_action_is_ignored() -> None:
    link = _link(FakeNapCat())
    ws = FakeWS()
    await link._on_frame(ws, json.dumps({"hello": 1}))
    assert ws.sent == []


async def test_send_event_without_connection_returns_false() -> None:
    link = _link(FakeNapCat())
    from adapter_helpers import make_event

    assert await link.send_event(make_event()) is False


async def test_send_event_writes_frame() -> None:
    link = _link(FakeNapCat())
    ws = FakeWS()
    link._ws = ws
    from adapter_helpers import make_event

    assert await link.send_event(make_event()) is True
    assert ws.sent[0]["post_type"] == "message"
    assert "message_id" in ws.sent[0]


@pytest.mark.parametrize("action", ["send_private_msg", "upload_private_file"])
async def test_private_actions_on_group_binding_are_refused(action: str) -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    response = await _send(link, {"action": action, "params": {"user_id": 1}, "echo": "e"})
    assert response["status"] == "failed"
    assert napcat.calls == []


async def test_set_group_card_targets_self_only() -> None:
    napcat = FakeNapCat()
    link = _link(napcat, self_id="1950119910")
    response = await _send(link, {"action": "set_group_card", "params": {"card": "派蒙"}, "echo": "e"})
    assert response["status"] == "ok"
    assert napcat.calls[0][1] == {"card": "派蒙", "group_id": 123456, "user_id": "1950119910"}


async def test_set_group_card_without_self_id_is_refused() -> None:
    napcat = FakeNapCat()
    link = _link(napcat)
    response = await _send(link, {"action": "set_group_card", "params": {"card": "x"}, "echo": "e"})
    assert response["status"] == "failed"
    assert napcat.calls == []


async def test_disconnect_notice_notifies_bound_group() -> None:
    napcat = FakeNapCat()
    link = _link(napcat, grace=0, cooldown=0)
    await link._notify_disconnect()
    action, params, _ = napcat.calls[-1]
    assert action == "send_group_msg"
    assert params["group_id"] == 123456
    assert params["message"] == [
        {"type": "text", "data": {"text": "Hermes gateway disconnected. Please check server state."}},
    ]


async def test_disconnect_notice_skipped_when_reconnected() -> None:
    napcat = FakeNapCat()
    link = _link(napcat, grace=0, cooldown=0)
    link._ws = FakeWS()  # property reports connected
    await link._notify_disconnect()
    assert napcat.calls == []


async def test_disconnect_notice_respects_cooldown() -> None:
    napcat = FakeNapCat()
    link = _link(napcat, grace=0, cooldown=3600)
    await link._notify_disconnect()
    await link._notify_disconnect()
    assert len(napcat.calls) == 1


async def test_first_disconnect_notice_is_not_blocked_by_small_uptime(monkeypatch) -> None:
    napcat = FakeNapCat()
    link = _link(napcat, grace=0, cooldown=3600)
    monkeypatch.setattr("time.monotonic", lambda: 1.0)
    await link._notify_disconnect()
    assert len(napcat.calls) == 1
