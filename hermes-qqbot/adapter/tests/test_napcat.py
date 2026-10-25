from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace

import pytest
from adapter_helpers import make_event
from crupest_qqbot_adapter.napcat import NapCatLink, presented_token, token_matches
from crupest_qqbot_core.errors import TransportError, UpstreamTimeout


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []
        self.closed = False
        self.close_code: int | None = None

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)

    async def close(self) -> None:
        self.closed = True


async def _wait_for_sent(ws: FakeWS, count: int = 1) -> None:
    for _ in range(50):
        if len(ws.sent) >= count:
            return
        await asyncio.sleep(0)
    raise AssertionError("call never sent a frame")


def _link(on_event=None, queue_size: int = 1024) -> NapCatLink:
    async def default_handler(event) -> None:
        return None

    return NapCatLink(token="tok", path="/onebot", on_event=on_event or default_handler, queue_size=queue_size)


def test_presented_token_query_and_header() -> None:
    assert presented_token(SimpleNamespace(query={"access_token": "a"}, headers={})) == "a"
    assert presented_token(SimpleNamespace(query={"token": "b"}, headers={})) == "b"
    assert presented_token(SimpleNamespace(query={}, headers={"Authorization": "Bearer c"})) == "c"
    assert presented_token(SimpleNamespace(query={}, headers={})) == ""


def test_token_matches() -> None:
    assert token_matches("abc", "abc") is True
    assert token_matches("abc", "abd") is False
    assert token_matches("", "") is False


async def test_call_roundtrip() -> None:
    link = _link()
    ws = FakeWS()
    link._ws = ws
    task = asyncio.create_task(link.call("send_group_msg", {"group_id": 1}, 1.0))
    await _wait_for_sent(ws)
    echo = ws.sent[0]["echo"]
    link._accept(json.dumps({"status": "ok", "retcode": 0, "data": {"message_id": 5}, "echo": echo}))
    response = await task
    assert response["data"]["message_id"] == 5
    assert ws.sent[0]["action"] == "send_group_msg"


async def test_call_without_connection() -> None:
    link = _link()
    with pytest.raises(TransportError):
        await link.call("get_login_info", {}, 1.0)


async def test_call_timeout() -> None:
    link = _link()
    ws = FakeWS()
    link._ws = ws
    with pytest.raises(UpstreamTimeout):
        await link.call("get_login_info", {}, 0.01)


async def test_disconnect_fails_pending() -> None:
    link = _link()
    ws = FakeWS()
    link._ws = ws
    task = asyncio.create_task(link.call("get_login_info", {}, 5.0))
    await _wait_for_sent(ws)
    link._fail_pending("gone")
    with pytest.raises(TransportError):
        await task


async def test_bad_json_is_ignored() -> None:
    link = _link()
    link._accept("{not json")
    link._accept("[1,2]")


async def test_event_is_dispatched_in_order() -> None:
    received: list[int] = []

    async def on_event(event) -> None:
        received.append(event.real_seq)

    link = _link(on_event)
    link._ensure_worker()
    for seq in (1, 2, 3):
        link._accept(json.dumps({
            "post_type": "message",
            "message_type": "group",
            "self_id": 1,
            "group_id": 2,
            "user_id": 3,
            "message_id": seq,
            "real_seq": seq,
            "message": [{"type": "text", "data": {"text": "x"}}],
        }))
    for _ in range(50):
        if len(received) == 3:
            break
        await asyncio.sleep(0)
    await link.stop()
    assert received == [1, 2, 3]


async def test_handler_exception_does_not_kill_worker() -> None:
    calls: list[int] = []

    async def on_event(event) -> None:
        calls.append(event.real_seq)
        if event.real_seq == 1:
            raise RuntimeError("boom")

    link = _link(on_event)
    link._ensure_worker()
    for seq in (1, 2):
        link._accept(json.dumps({
            "post_type": "message",
            "message_type": "group",
            "self_id": 1,
            "group_id": 2,
            "user_id": 3,
            "message_id": seq,
            "real_seq": seq,
            "message": [],
        }))
    for _ in range(50):
        if len(calls) == 2:
            break
        await asyncio.sleep(0)
    await link.stop()
    assert calls == [1, 2]


def test_queue_overflow_is_dropped(caplog) -> None:
    link = _link(queue_size=1)
    link._dispatch(make_event())
    link._dispatch(make_event())
    assert link._queue.qsize() == 1
