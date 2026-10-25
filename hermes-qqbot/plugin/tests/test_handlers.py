from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from crupest_qqbot_core.errors import QQBotError
from crupest_qqbot_plugin.adapter import QQPlatform
from crupest_qqbot_plugin.media import MediaError
from crupest_qqbot_plugin.tools import fetch_media


class FakeFetcher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.fetched: list[str] = []

    async def fetch(self, url: str) -> tuple[bytes, str]:
        self.fetched.append(url)
        if self.fail:
            raise MediaError("boom")
        return b"abc", "image/jpeg"

    def save(self, data: bytes, suffix: str = ".bin") -> str:
        return f"/cache/out{suffix}"


def _platform(*, group: bool = True) -> QQPlatform:
    return QQPlatform(
        url="ws://x",
        token="t",
        chat_kind="group" if group else "dm",
        chat_id="123" if group else "456",
        media_fetcher=FakeFetcher(),
    )


def _message_event(**overrides):
    payload = {
        "post_type": "message",
        "message_type": "group",
        "self_id": 1950119910,
        "message_id": 42,
        "real_seq": 7,
        "group_id": 123,
        "user_id": 10001,
        "message": [
            {"type": "reply", "data": {"id": "5"}},
            {"type": "at", "data": {"qq": "1950119910"}},
            {"type": "text", "data": {"text": " 看看这个"}},
        ],
        "sender": {"user_id": 10001, "nickname": "张三"},
    }
    payload.update(overrides)
    return payload


async def test_handle_message_builds_event() -> None:
    platform = _platform()
    captured = []

    async def fake_api(action, params, timeout=None):
        if action == "get_msg":
            return {
                "message_id": 5,
                "real_seq": 3,
                "user_id": 2,
                "sender": {"nickname": "李四"},
                "message": [{"type": "text", "data": {"text": "在"}}],
            }
        raise AssertionError(action)

    platform.api = fake_api  # type: ignore[method-assign]

    async def capture(event):
        captured.append(event)

    platform.handler = capture
    await platform._handle_message(_message_event())

    assert len(captured) == 1
    event = captured[0]
    assert event.text == "[张三(10001)#7] [@self] 看看这个"
    assert event.source.chat_id == "group:123"
    assert event.reply_to_message_id == "5"
    assert event.reply_to_text == "[李四(2)#3]: 在"
    assert event.reply_to_author_name == "李四"
    assert event.message_id == "42"


async def test_handle_message_of_dm() -> None:
    platform = _platform(group=False)
    captured = []

    async def capture(event):
        captured.append(event)

    platform.handler = capture

    async def fake_api(action, params, timeout=None):
        return {}

    platform.api = fake_api  # type: ignore[method-assign]
    await platform._handle_message(_message_event(message_type="private", group_id=None, user_id=456, message=[
        {"type": "text", "data": {"text": "在吗"}},
    ]))
    assert captured[0].text == "在吗"
    assert captured[0].source.chat_id == "user:456"


async def test_reply_context_failure_is_soft() -> None:
    platform = _platform()

    async def failing(action, params, timeout=None):
        raise QQBotError("nope")

    platform.api = failing  # type: ignore[method-assign]
    from crupest_qqbot_core.schema import Event

    assert await platform._reply_context(Event.model_validate(_message_event())) is None


async def test_prepare_media_downloads_and_reports() -> None:
    platform = _platform()
    platform._media = FakeFetcher()  # type: ignore[assignment]
    from crupest_qqbot_core.schema import Event

    event = Event.model_validate(_message_event(message=[
        {"type": "image", "data": {"file": "a.jpg", "url": "https://example.com/a.jpg"}},
        {"type": "image", "data": {"file": "b.jpg"}},
    ]))
    results, urls, types = await platform._prepare_media(event)
    assert urls == ["/cache/out.jpg"]
    assert types == ["image"]
    assert results[0].path == "/cache/out.jpg"
    assert results[1].cache == "none"


async def test_prepare_media_marks_failure() -> None:
    platform = _platform()
    platform._media = FakeFetcher(fail=True)  # type: ignore[assignment]
    from crupest_qqbot_core.schema import Event

    event = Event.model_validate(_message_event(message=[
        {"type": "image", "data": {"file": "a.jpg", "url": "https://example.com/a.jpg"}},
    ]))
    results, urls, _ = await platform._prepare_media(event)
    assert urls == []
    assert results[0].cache == "failed"


async def test_fetch_media_returns_local_path() -> None:
    class Platform:
        async def api(self, action, params):
            assert action == "get_file"
            return {"url": "https://example.com/f.pdf", "file_name": "f.pdf"}

    result = json.loads(await fetch_media(Platform(), {"id": "fid"}, FakeFetcher()))
    assert result["path"] == "/cache/out.jpg"
    assert result["name"] == "f.pdf"


async def test_fetch_media_tries_get_image_second() -> None:
    calls: list[str] = []

    class Platform:
        async def api(self, action, params):
            calls.append(action)
            if action == "get_file":
                raise QQBotError("not a file")
            return {"url": "https://example.com/a.jpg"}

    await fetch_media(Platform(), {"id": "a.jpg"}, FakeFetcher())
    assert calls == ["get_file", "get_image"]


async def test_fetch_media_without_url_is_explicit() -> None:
    class Platform:
        async def api(self, action, params):
            return {}

    result = await fetch_media(Platform(), {"id": "x"}, FakeFetcher())
    assert result.startswith("错误:")
    assert "重发" in result


async def test_fetch_media_requires_id() -> None:
    class Platform:
        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await fetch_media(Platform(), {}, FakeFetcher())).startswith("错误:")


async def test_fetch_media_download_failure() -> None:
    class Platform:
        async def api(self, action, params):
            return {"url": "https://example.com/a.jpg"}

    result = await fetch_media(Platform(), {"id": "a.jpg"}, FakeFetcher(fail=True))
    assert result.startswith("错误:")


@pytest.mark.parametrize("chat_kind", ["group", "dm"])
def test_platform_chat_key_matches_binding(chat_kind: str) -> None:
    platform = QQPlatform(url="ws://x", token="t", chat_kind=chat_kind, chat_id="9")
    expected = "group:9" if chat_kind == "group" else "user:9"
    assert platform.chat_key == expected


def test_build_source_is_used_for_identity() -> None:
    platform = _platform()
    source = platform.build_source(chat_id="group:1", chat_type="group")
    assert isinstance(source, SimpleNamespace)
    assert source.chat_id == "group:1"
