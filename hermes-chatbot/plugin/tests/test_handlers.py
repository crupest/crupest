from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from crupest_chatbot_core.errors import ChatbotError
from crupest_chatbot_plugin.adapter import QQPlatform
from crupest_chatbot_plugin.media import MediaError
from crupest_chatbot_plugin.tools import (
    fetch_group_file,
    fetch_media,
    get_group_file_system_info,
    get_group_file_url,
    get_group_info,
    get_group_member,
    get_login_info,
    get_user_info,
    list_group_files,
    list_group_members,
    read_forward,
    read_history,
    transcribe_voice,
)


class FakeFetcher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.fetched: list[str] = []

    async def fetch_to_cache(self, url: str, suffix_fallback: str = ".bin") -> tuple[str, str, int]:
        self.fetched.append(url)
        if self.fail:
            raise MediaError("boom")
        return "/cache/out.jpg", "image/jpeg", 3


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
    assert event.text == "[张三(10001)#7] [[@self]] 看看这个"
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
        raise ChatbotError("nope")

    platform.api = failing  # type: ignore[method-assign]
    from crupest_chatbot_core.schema import Event

    assert await platform._reply_context(Event.model_validate(_message_event())) is None


async def test_prepare_media_downloads_and_reports() -> None:
    platform = _platform()
    platform._media = FakeFetcher()  # type: ignore[assignment]
    from crupest_chatbot_core.schema import Event

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
    from crupest_chatbot_core.schema import Event

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
                raise ChatbotError("not a file")
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


async def test_list_group_members_truncates() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_member_list"
            return [{"user_id": i} for i in range(5)]

    result = json.loads(await list_group_members(Platform(), {"limit": 2}))
    assert [member["user_id"] for member in result] == [0, 1]


async def test_list_group_members_zero_returns_all() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            return [{"user_id": i} for i in range(5)]

    result = json.loads(await list_group_members(Platform(), {"limit": 0}))
    assert len(result) == 5


async def test_group_tools_reject_dm() -> None:
    class Platform:
        chat_kind = "dm"

        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await list_group_members(Platform(), {})).startswith("错误:")
    assert (await get_group_member(Platform(), {"user_id": 1})).startswith("错误:")
    assert (await get_group_info(Platform(), {})).startswith("错误:")


async def test_get_group_member_passes_user_id_and_cache_flag() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_member_info"
            assert params == {"user_id": 42, "no_cache": True}
            return {"user_id": 42, "card": "派蒙"}

    result = json.loads(await get_group_member(Platform(), {"user_id": 42, "no_cache": True}))
    assert result["card"] == "派蒙"


async def test_get_group_member_requires_user_id() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await get_group_member(Platform(), {})).startswith("错误:")


async def test_get_group_info_uses_pinned_action() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_info"
            assert params == {}
            return {"group_name": "测试群"}

    result = json.loads(await get_group_info(Platform(), {}))
    assert result["group_name"] == "测试群"


async def test_get_user_info_works_in_dm_and_group() -> None:
    class Platform:
        chat_kind = "dm"

        async def api(self, action, params):
            assert action == "get_stranger_info"
            assert params == {"user_id": 7, "no_cache": False}
            return {"user_id": 7, "nickname": "路人"}

    result = json.loads(await get_user_info(Platform(), {"user_id": 7}))
    assert result["nickname"] == "路人"


async def test_get_login_info_returns_self() -> None:
    class Platform:
        async def api(self, action, params):
            assert action == "get_login_info"
            return {"user_id": 1950119910, "nickname": "派蒙"}

    result = json.loads(await get_login_info(Platform(), {}))
    assert result["user_id"] == 1950119910


async def test_read_history_uses_friend_action_in_dm() -> None:
    class Platform:
        chat_kind = "dm"

        async def api(self, action, params):
            assert action == "get_friend_msg_history"
            assert params == {"count": 5, "message_seq": 0}
            return {"messages": []}

    assert json.loads(await read_history(Platform(), {"count": 5})) == {"messages": []}


async def test_transcribe_voice_by_real_seq() -> None:
    class Platform:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def api(self, action, params):
            self.calls.append((action, params))
            if action == "get_msg":
                return {}
            assert action == "fetch_ptt_text"
            assert params == {"real_seq": 3}
            return {"text": "你好"}

    platform = Platform()
    assert await transcribe_voice(platform, {"real_seq": 3}) == "你好"
    assert [action for action, _ in platform.calls] == ["get_msg", "fetch_ptt_text"]


async def test_transcribe_voice_by_message_id() -> None:
    class Platform:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        async def api(self, action, params):
            self.calls.append((action, params))
            if action == "get_msg":
                return {}
            assert action == "fetch_ptt_text"
            assert params == {"message_id": "42"}
            return {"text": "收到"}

    platform = Platform()
    assert await transcribe_voice(platform, {"message_id": "42"}) == "收到"
    assert [action for action, _ in platform.calls] == ["get_msg", "fetch_ptt_text"]


async def test_transcribe_voice_retries_once(monkeypatch) -> None:
    async def fake_sleep(_seconds: float) -> None:
        return None

    monkeypatch.setattr("crupest_chatbot_plugin.tools.asyncio.sleep", fake_sleep)
    calls: list[str] = []

    class Platform:
        async def api(self, action, params):
            calls.append(action)
            if action == "get_msg":
                return {}
            if calls.count("fetch_ptt_text") == 1:
                raise ChatbotError("boom")
            return {"text": "重试成功"}

    assert await transcribe_voice(Platform(), {"real_seq": 3}) == "重试成功"
    assert calls.count("fetch_ptt_text") == 2


async def test_transcribe_voice_requires_an_id() -> None:
    class Platform:
        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await transcribe_voice(Platform(), {})).startswith("错误:")


async def test_read_forward_passes_id() -> None:
    class Platform:
        async def api(self, action, params):
            assert action == "get_forward_msg"
            assert params == {"id": "abc"}
            return {"messages": [{"message_id": 1}]}

    result = json.loads(await read_forward(Platform(), {"id": "abc"}))
    assert result["messages"][0]["message_id"] == 1


async def test_list_group_files_root_and_folder() -> None:
    calls = []

    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            calls.append((action, params))
            return {"files": []}

    await list_group_files(Platform(), {})
    await list_group_files(Platform(), {"folder_id": "f1", "count": 10})
    assert calls == [
        ("get_group_root_files", {"file_count": 50}),
        ("get_group_files_by_folder", {"folder_id": "f1", "file_count": 10}),
    ]


async def test_list_group_files_rejects_dm() -> None:
    class Platform:
        chat_kind = "dm"

        async def api(self, action, params):
            raise AssertionError("must not call")

    assert (await list_group_files(Platform(), {})).startswith("错误:")


async def test_get_group_file_url_passes_file_id() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_file_url"
            assert params == {"file_id": "fid"}
            return {"url": "https://example.com/f.bin"}

    result = json.loads(await get_group_file_url(Platform(), {"file_id": "fid"}))
    assert result["url"] == "https://example.com/f.bin"


async def test_fetch_group_file_downloads_to_cache() -> None:
    class Platform:
        chat_kind = "group"
        _media = FakeFetcher()

        async def api(self, action, params):
            assert action == "get_group_file_url"
            return {"url": "https://example.com/f.bin"}

    result = json.loads(await fetch_group_file(Platform(), {"file_id": "fid"}))
    assert result["path"] == "/cache/out.jpg"
    assert result["size"] == 3


async def test_fetch_group_file_without_url_errors() -> None:
    class Platform:
        chat_kind = "group"
        _media = FakeFetcher()

        async def api(self, action, params):
            return {}

    assert (await fetch_group_file(Platform(), {"file_id": "fid"})).startswith("错误:")


async def test_get_group_file_system_info() -> None:
    class Platform:
        chat_kind = "group"

        async def api(self, action, params):
            assert action == "get_group_file_system_info"
            assert params == {}
            return {"file_count": 1, "used_space": 2}

    result = json.loads(await get_group_file_system_info(Platform(), {}))
    assert result["file_count"] == 1


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
