from __future__ import annotations

import asyncio
import json

import pytest
from crupest_qqbot_plugin.adapter import RpcClient, RpcUnavailable


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


async def _wait_for_sent(ws: FakeWS, count: int = 1) -> None:
    for _ in range(50):
        if len(ws.sent) >= count:
            return
        await asyncio.sleep(0)
    raise AssertionError("rpc never sent a frame")


async def test_call_roundtrip() -> None:
    rpc = RpcClient()
    ws = FakeWS()
    rpc.attach(ws)
    task = asyncio.create_task(rpc.call("get_login_info", {}, 1.0))
    await _wait_for_sent(ws)
    echo = ws.sent[0]["echo"]
    rpc.resolve({"status": "ok", "retcode": 0, "data": {"user_id": 1}, "echo": echo})
    response = await task
    assert response["data"]["user_id"] == 1


async def test_call_without_connection() -> None:
    with pytest.raises(RpcUnavailable):
        await RpcClient().call("get_login_info", {}, 1.0)


async def test_call_timeout() -> None:
    rpc = RpcClient()
    rpc.attach(FakeWS())
    with pytest.raises(RpcUnavailable):
        await rpc.call("get_login_info", {}, 0.01)


async def test_detach_fails_pending() -> None:
    rpc = RpcClient()
    ws = FakeWS()
    rpc.attach(ws)
    task = asyncio.create_task(rpc.call("get_login_info", {}, 5.0))
    await _wait_for_sent(ws)
    rpc.detach()
    with pytest.raises(RpcUnavailable):
        await task


async def test_unknown_echo_is_ignored() -> None:
    rpc = RpcClient()
    rpc.resolve({"echo": "nope", "status": "ok"})
    assert rpc.connected is False


async def test_send_failure_raises() -> None:
    class Broken:
        async def send_json(self, payload):
            raise RuntimeError("closed")

    rpc = RpcClient()
    rpc.attach(Broken())
    with pytest.raises(RpcUnavailable):
        await rpc.call("get_login_info", {}, 1.0)


def test_echo_is_unique_per_call() -> None:
    rpc = RpcClient()
    ws = FakeWS()
    rpc.attach(ws)

    async def run() -> None:
        first = asyncio.create_task(rpc.call("a", {}, 0.01))
        second = asyncio.create_task(rpc.call("b", {}, 0.01))
        await _wait_for_sent(ws, 2)
        for task in (first, second):
            task.cancel()
        for task in (first, second):
            with pytest.raises(asyncio.CancelledError):
                await task

    asyncio.run(run())
    echoes = {frame["echo"] for frame in ws.sent}
    assert len(echoes) == 2


def test_payload_is_json_serialisable() -> None:
    rpc = RpcClient()
    ws = FakeWS()
    rpc.attach(ws)

    async def run() -> None:
        task = asyncio.create_task(rpc.call("a", {"k": "值"}, 0.01))
        await _wait_for_sent(ws)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

    asyncio.run(run())
    assert json.loads(json.dumps(ws.sent[0], ensure_ascii=False))["params"] == {"k": "值"}
