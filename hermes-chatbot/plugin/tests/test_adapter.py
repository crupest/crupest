from __future__ import annotations

import asyncio
import json
import threading
from datetime import datetime
from types import SimpleNamespace

from crupest_chatbot_plugin.adapter import (
    QQPlatform,
    RpcClient,
    RpcError,
    _event_timestamp,
    build_message_event,
)
from crupest_chatbot_plugin.stubs import SendResult


async def test_connect_implements_base_contract() -> None:
    platform = QQPlatform(url="ws://127.0.0.1:1/hermes", token="t", chat_kind="group", chat_id="1")
    assert await platform.connect(is_reconnect=False) is True
    assert platform.is_connected is True
    assert platform._maintenance is not None
    await platform.disconnect()
    assert platform.is_connected is False
    assert platform._maintenance is None


async def test_get_chat_info_group() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="123")

    async def fake_api(action, params, timeout=None):
        return {"group_name": "测试群"}

    platform.api = fake_api  # type: ignore[method-assign]
    info = await platform.get_chat_info("group:123")
    assert info == {"name": "测试群", "type": "group", "chat_id": "group:123"}


async def test_get_chat_info_dm_falls_back() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="dm", chat_id="456")

    async def failing(action, params, timeout=None):
        raise RpcError(action, "boom", reason="napcat_failed")

    platform.api = failing  # type: ignore[method-assign]
    info = await platform.get_chat_info("user:456")
    assert info == {"name": "user:456", "type": "dm", "chat_id": "user:456"}


async def test_send_document_uses_file_name() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 3}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send_document("group:1", "/tmp/a.bin", file_name="报告.pdf")
    assert result.success is True
    assert sent[0]["message"][0]["data"]["file"] == "/tmp/a.bin"
    assert sent[0]["message"][0]["data"]["name"] == "报告.pdf"


async def test_send_image_file_uses_local_path() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 4}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send_image_file("group:1", "/opt/data/share/media/a.jpg", caption="看图")
    assert result.success is True
    assert sent[0]["message"][0] == {"type": "image", "data": {"file": "/opt/data/share/media/a.jpg"}}
    assert sent[0]["message"][1]["data"]["text"] == "看图"


async def test_send_voice_builds_record_segment() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 5}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send_voice("group:1", "/opt/data/share/a.amr")
    assert result.success is True
    assert sent[0]["message"][0] == {"type": "record", "data": {"file": "/opt/data/share/a.amr"}}


async def test_send_video_builds_video_segment() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 6}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send_video("group:1", "/opt/data/share/a.mp4", caption="视频")
    assert result.success is True
    assert sent[0]["message"][0] == {"type": "video", "data": {"file": "/opt/data/share/a.mp4"}}
    assert sent[0]["message"][1]["data"]["text"] == "视频"


async def test_send_method_is_the_text_path() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 1}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send("group:1", "**hi**")
    assert result.success is True
    assert sent[0]["message"][0]["data"]["text"] == "hi"


async def test_inbound_message_is_queued_then_processed() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="123")
    captured = []

    async def capture(event):
        captured.append(event)

    platform.handler = capture
    frame = {
        "post_type": "message",
        "message_type": "group",
        "self_id": 1,
        "group_id": 123,
        "user_id": 2,
        "message_id": 9,
        "message": [{"type": "text", "data": {"text": "hi"}}],
    }
    await platform._on_frame(json.dumps(frame))
    assert platform._inbound.qsize() == 1
    platform._ensure_worker()
    for _ in range(100):
        if captured:
            break
        await asyncio.sleep(0)
    await platform.disconnect()
    assert len(captured) == 1
    assert captured[0].text == "[2(2)#9] hi"


async def test_inbound_queue_overflow_drops(caplog) -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    platform._inbound = asyncio.Queue(maxsize=1)
    platform._enqueue({"a": 1})
    platform._enqueue({"a": 2})
    assert platform._inbound.qsize() == 1


class FakeWS:
    def __init__(self) -> None:
        self.sent: list[dict] = []

    async def send_json(self, payload: dict) -> None:
        self.sent.append(payload)


def test_build_message_event_maps_fields() -> None:
    source = SimpleNamespace(chat_id="group:1")
    event = build_message_event(
        text="[张三(1)#2] 你好",
        source=source,
        message_id="42",
        media_urls=["/cache/a.jpg"],
        media_types=["image"],
        reply=("7", "[李四(2)#3]: 在", "2", "李四"),
        raw={"post_type": "message"},
        internal=True,
    )
    assert event.text == "[张三(1)#2] 你好"
    assert event.source is source
    assert event.message_id == "42"
    assert event.media_urls == ["/cache/a.jpg"]
    assert event.reply_to_message_id == "7"
    assert event.reply_to_author_name == "李四"
    assert event.internal is True


def test_rpc_resolve_crosses_event_loops() -> None:
    rpc = RpcClient()
    loop = asyncio.new_event_loop()
    ready = threading.Event()
    result: dict = {}

    def worker() -> None:
        asyncio.set_event_loop(loop)

        async def main() -> None:
            future = loop.create_future()
            rpc._pending["q1"] = future
            ready.set()
            result["payload"] = await asyncio.wait_for(future, 2)

        loop.run_until_complete(main())
        loop.close()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    assert ready.wait(1)
    rpc.resolve({"echo": "q1", "status": "ok", "data": {"x": 1}})
    thread.join(2)
    assert not thread.is_alive()
    assert result["payload"]["data"] == {"x": 1}


def test_event_timestamp_handles_invalid_values() -> None:
    assert _event_timestamp(0) is None
    assert _event_timestamp(1e30) is None
    normal = _event_timestamp(1700000000)
    assert normal is not None
    assert normal.tzinfo is not None


def test_build_message_event_uses_given_timestamp() -> None:
    moment = datetime(2026, 10, 26, 12, 0, 0)
    event = build_message_event(
        text="x",
        source=None,
        message_id="1",
        media_urls=[],
        media_types=[],
        reply=None,
        raw={},
        timestamp=moment,
    )
    assert event.timestamp == moment


def test_build_message_event_without_reply() -> None:
    event = build_message_event(
        text="x", source=None, message_id="", media_urls=[], media_types=[], reply=None, raw={},
    )
    assert event.reply_to_message_id is None
    assert event.reply_to_text is None


def test_plain_fallback_is_disabled() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    result = __import__("asyncio").run(platform._send_plain_fallback("group:1", "hi"))
    assert isinstance(result, SendResult)
    assert result.success is False
    assert result.retryable is False
    assert platform._send_retry_is_final(result) is True


def test_send_retry_is_final_reads_raw_flag() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    assert platform._send_retry_is_final(SendResult(success=False)) is False
    assert platform._send_retry_is_final(SendResult(success=False, raw_response={"final": True})) is True


def test_chat_key() -> None:
    group = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="123")
    dm = QQPlatform(url="ws://x", token="t", chat_kind="dm", chat_id="456")
    assert group.chat_key == "group:123"
    assert dm.chat_key == "user:456"
    assert group.chat_kind == "group"
    assert dm.chat_kind == "dm"


def test_max_message_length_is_qq_limit() -> None:
    assert QQPlatform.MAX_MESSAGE_LENGTH == 4500


async def test_send_text_builds_group_frame() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="123")
    calls: list[tuple[str, dict, float | None]] = []

    async def fake_api(action, params, timeout=None):
        calls.append((action, params, timeout))
        return {"message_id": 9}

    platform.api = fake_api  # type: ignore[method-assign]
    result = await platform.send_text("group:123", "你好", reply_to="5")
    assert result.success is True
    assert result.message_id == "9"
    action, params, _ = calls[0]
    assert action == "send_group_msg"
    assert params["group_id"] == "123"
    assert params["message"][0] == {"type": "reply", "data": {"id": "5"}}
    assert params["message"][1] == {"type": "text", "data": {"text": "你好"}}


async def test_send_text_dm_uses_private() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="dm", chat_id="456")
    calls: list[tuple[str, dict]] = []

    async def fake_api(action, params, timeout=None):
        calls.append((action, params))
        return {"message_id": 1}

    platform.api = fake_api  # type: ignore[method-assign]
    await platform.send_text("user:456", "hi")
    assert calls[0][0] == "send_private_msg"
    assert calls[0][1]["user_id"] == "456"


async def test_send_text_strips_markdown() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 1}

    platform.api = fake_api  # type: ignore[method-assign]
    await platform.send_text("group:1", "**粗体**")
    assert sent[0]["message"][0]["data"]["text"] == "粗体"


async def test_send_text_splits_long_content() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    sent: list[dict] = []

    async def fake_api(action, params, timeout=None):
        sent.append(params)
        return {"message_id": 1}

    platform.api = fake_api  # type: ignore[method-assign]
    await platform.send_text("group:1", "x" * 4600)
    assert len(sent[0]["message"]) == 2


async def test_send_text_rejects_empty() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")
    result = await platform.send_text("group:1", "")
    assert result.success is False
    assert result.retryable is False


async def test_send_failure_is_retryable() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")

    async def failing(action, params, timeout=None):
        raise RpcError(action, "NapCat 超时", reason="napcat_timeout")

    platform.api = failing  # type: ignore[method-assign]
    result = await platform.send_text("group:1", "hi")
    assert result.success is False
    assert result.retryable is True


async def test_policy_failure_is_final() -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind="group", chat_id="1")

    async def denied(action, params, timeout=None):
        raise RpcError(action, "not allowed", reason="target_mismatch")

    platform.api = denied  # type: ignore[method-assign]
    result = await platform.send_text("group:1", "hi")
    assert result.success is False
    assert result.retryable is False
    assert platform._send_retry_is_final(result) is True


async def test_react_translates_real_seq() -> None:
    from crupest_chatbot_plugin.tools import react

    calls: list[tuple[str, dict]] = []

    class FakePlatform:
        async def api(self, action, params):
            calls.append((action, params))
            return None

    assert await react(FakePlatform(), {"real_seq": 8, "emoji_id": 124}) == "ok"
    assert calls[0] == ("set_msg_emoji_like", {"real_seq": 8, "emoji_id": "124"})


async def test_react_accepts_friendly_alias() -> None:
    from crupest_chatbot_plugin.tools import react

    calls: list[tuple[str, dict]] = []

    class FakePlatform:
        async def api(self, action, params):
            calls.append((action, params))
            return None

    assert await react(FakePlatform(), {"real_seq": 8, "emoji_id": "👌"}) == "ok"
    assert calls[0][1]["emoji_id"] == "124"


async def test_react_reports_errors() -> None:
    from crupest_chatbot_plugin.tools import react

    class FakePlatform:
        async def api(self, action, params):
            raise RpcError(action, "boom", reason="napcat_failed")

    result = await react(FakePlatform(), {"real_seq": 8, "emoji_id": "124"})
    assert result.startswith("错误:")


async def test_read_history_returns_raw_json() -> None:
    from crupest_chatbot_plugin.tools import read_history

    class FakePlatform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_msg_history"
            return {"messages": [{"message_id": 1}]}

    result = await read_history(FakePlatform(), {"count": 5})
    assert '"message_id": 1' in result


async def test_read_history_uses_friend_action_in_dm() -> None:
    from crupest_chatbot_plugin.tools import read_history

    class FakePlatform:
        chat_kind = "dm"

        async def api(self, action, params):
            assert action == "get_friend_msg_history"
            return {"messages": [{"message_id": 2}]}

    result = await read_history(FakePlatform(), {"count": 1})
    assert '"message_id": 2' in result


async def test_set_nickname_calls_profile() -> None:
    from crupest_chatbot_plugin.tools import set_nickname

    calls: list[tuple[str, dict]] = []

    class FakePlatform:
        async def api(self, action, params):
            calls.append((action, params))
            return None

    assert await set_nickname(FakePlatform(), {"nickname": "派蒙"}) == "ok"
    assert calls[0] == ("set_qq_profile", {"nickname": "派蒙"})


async def test_set_nickname_rejects_blank() -> None:
    from crupest_chatbot_plugin.tools import set_nickname

    class FakePlatform:
        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await set_nickname(FakePlatform(), {"nickname": "  "})).startswith("错误:")


async def test_set_avatar_calls_avatar() -> None:
    from crupest_chatbot_plugin.tools import set_avatar

    calls: list[tuple[str, dict]] = []

    class FakePlatform:
        async def api(self, action, params):
            calls.append((action, params))
            return None

    assert await set_avatar(FakePlatform(), {"file": "https://x/a.png"}) == "ok"
    assert calls[0] == ("set_qq_avatar", {"file": "https://x/a.png"})


async def test_set_group_card_calls_card() -> None:
    from crupest_chatbot_plugin.tools import set_group_card

    calls: list[tuple[str, dict]] = []

    class FakePlatform:
        async def api(self, action, params):
            calls.append((action, params))
            return None

    assert await set_group_card(FakePlatform(), {"card": "派蒙"}) == "ok"
    assert calls[0] == ("set_group_card", {"card": "派蒙"})


async def test_identity_tool_reports_errors() -> None:
    from crupest_chatbot_plugin.tools import set_group_card

    class FakePlatform:
        async def api(self, action, params):
            raise RpcError(action, "not allowed", reason="target_mismatch")

    assert (await set_group_card(FakePlatform(), {"card": "x"})).startswith("错误:")
