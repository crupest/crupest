from __future__ import annotations

from pathlib import Path

import pytest
from crupest_chatbot_core.config import FeaturesConfig, LimitsConfig
from crupest_chatbot_core.richtext import RichTextError
from crupest_chatbot_plugin.adapter import QQPlatform
from crupest_chatbot_plugin.media import MediaError
from crupest_chatbot_plugin.tools import poke, send_forward, send_message, upload_group_file


class FakeFetcher:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.urls: list[str] = []

    async def fetch_to_cache(self, url: str, suffix_fallback: str = ".bin") -> tuple[str, str, int]:
        self.urls.append(url)
        if self.fail:
            raise MediaError("blocked")
        return "/cache/img.jpg", "image/jpeg", 3


class FakeApi:
    def __init__(self, data: dict | None = None) -> None:
        self.calls: list[tuple[str, dict]] = []
        self.data = data if data is not None else {"message_id": 1}

    async def __call__(self, action: str, params: dict, timeout: float | None = None) -> dict:
        self.calls.append((action, params))
        return self.data


def _platform(
    *, group: bool = True, features: FeaturesConfig | None = None, limits: LimitsConfig | None = None,
) -> QQPlatform:
    return QQPlatform(
        url="ws://x",
        token="t",
        chat_kind="group" if group else "dm",
        chat_id="123" if group else "456",
        features=features,
        limits=limits,
    )


def _remember(platform: QQPlatform, *, real_seq: int, message_id: int, user_id: int = 10001) -> None:
    from crupest_chatbot_core.schema import Event

    platform._remember(Event.model_validate({
        "post_type": "message",
        "message_type": "group",
        "self_id": 1950119910,
        "message_id": message_id,
        "real_seq": real_seq,
        "group_id": 123,
        "user_id": user_id,
        "message": [{"type": "text", "data": {"text": "hi"}}],
    }))


async def test_send_rich_builds_special_segments() -> None:
    platform = _platform()
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    items = [
        {"type": "text", "text": "你好 "},
        {"type": "at", "qq": "10001"},
        {"type": "face", "name": "微笑"},
        {"type": "dice"},
        {"type": "rps"},
    ]
    result = await platform.send_rich(items)
    assert result.success is True
    assert api.calls[0] == (
        "send_group_msg",
        {"group_id": "123", "message": [
            {"type": "text", "data": {"text": "你好 "}},
            {"type": "at", "data": {"qq": "10001"}},
            {"type": "face", "data": {"id": "14"}},
            {"type": "dice", "data": {}},
            {"type": "rps", "data": {}},
        ]},
    )


async def test_send_rich_strips_markdown() -> None:
    platform = _platform()
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    await platform.send_rich([{"type": "text", "text": "**粗体**"}])
    assert api.calls[0][1]["message"] == [{"type": "text", "data": {"text": "粗体"}}]


async def test_send_image_downloads_remote_url_first() -> None:
    platform = _platform()
    fetcher = FakeFetcher()
    platform._media = fetcher  # type: ignore[assignment]
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    result = await platform.send_image("group:123", "https://example.com/a.jpg")
    assert result.success is True
    assert fetcher.urls == ["https://example.com/a.jpg"]
    assert api.calls[0][1]["message"][0] == {"type": "image", "data": {"file": "/cache/img.jpg"}}


async def test_send_image_does_not_forward_url_when_download_fails() -> None:
    platform = _platform()
    platform._media = FakeFetcher(fail=True)  # type: ignore[assignment]
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    result = await platform.send_image("group:123", "https://example.com/a.jpg")
    assert result.success is False
    assert api.calls == []


async def test_send_rich_reply_resolves_seq() -> None:
    platform = _platform()
    _remember(platform, real_seq=7, message_id=42)
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    await platform.send_rich([
        {"type": "reply", "seq": 7},
        {"type": "text", "text": "收到"},
    ])
    assert api.calls[0][1]["message"] == [
        {"type": "reply", "data": {"id": "42"}},
        {"type": "text", "data": {"text": "收到"}},
    ]


async def test_send_rich_error_carries_index() -> None:
    platform = _platform()
    with pytest.raises(RichTextError) as excinfo:
        await platform.send_rich([{"type": "face", "name": "不存在的表情"}])
    assert excinfo.value.index == 0
    assert "segments[1]" in str(excinfo.value)


async def test_send_rich_allows_at_self() -> None:
    platform = _platform()
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    result = await platform.send_rich([{"type": "at", "qq": "1950119910"}])
    assert result.success is True
    assert api.calls[0][1]["message"] == [{"type": "at", "data": {"qq": "1950119910"}}]


async def test_send_rich_rejects_at_all_when_disabled() -> None:
    platform = _platform(features=FeaturesConfig(at_all=False))
    with pytest.raises(RichTextError):
        await platform.send_rich([{"type": "at", "qq": "all"}])


async def test_send_rich_rejects_unknown_reply_seq() -> None:
    platform = _platform()
    with pytest.raises(RichTextError):
        await platform.send_rich([{"type": "reply", "seq": 9}])


async def test_send_rich_rejects_long_text() -> None:
    platform = _platform()
    with pytest.raises(RichTextError):
        await platform.send_rich([{"type": "text", "text": "x" * 4501}])


async def test_caption_is_plain_text() -> None:
    platform = _platform()
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    await platform.send_image_file("group:123", "/tmp/a.jpg", caption="看图")
    assert api.calls[0][1]["message"] == [
        {"type": "image", "data": {"file": "/tmp/a.jpg"}},
        {"type": "text", "data": {"text": "看图"}},
    ]


async def test_send_message_tool_returns_json() -> None:
    import json

    platform = _platform()
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]

    ok = json.loads(await send_message(platform, {"segments": [{"type": "text", "text": "hi"}]}))
    assert ok["ok"] is True

    failed = json.loads(await send_message(platform, {"segments": [{"type": "face", "name": "无"}]}))
    assert failed["ok"] is False
    assert "segments[1]" in failed["error"]
    assert "hint" in failed


async def test_forward_uses_seen_message_ids() -> None:
    platform = _platform()
    _remember(platform, real_seq=7, message_id=42)
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    result = await platform.send_forward([7])
    assert result.success is True
    assert api.calls[0] == (
        "send_group_forward_msg",
        {"group_id": "123", "messages": [{"type": "node", "data": {"id": "42"}}]},
    )


async def test_forward_rejects_unknown_seq() -> None:
    platform = _platform()
    result = await platform.send_forward([7])
    assert result.success is False
    assert "找不到消息序号" in (result.error or "")


async def test_forward_in_dm_uses_private_action() -> None:
    platform = _platform(group=False)
    _remember(platform, real_seq=7, message_id=42)
    api = FakeApi()
    platform.api = api  # type: ignore[method-assign]
    await platform.send_forward([7])
    assert api.calls[0][0] == "send_private_forward_msg"
    assert api.calls[0][1]["user_id"] == "456"


async def test_poke_targets_last_speaker() -> None:
    platform = _platform()
    _remember(platform, real_seq=7, message_id=42)
    api = FakeApi(data=None)  # type: ignore[arg-type]
    platform.api = api  # type: ignore[method-assign]
    result = await platform.poke()
    assert result.success is True
    assert api.calls[0] == ("send_poke", {"user_id": "10001", "group_id": "123"})


async def test_poke_targets_explicit_qq() -> None:
    platform = _platform()
    api = FakeApi(data=None)  # type: ignore[arg-type]
    platform.api = api  # type: ignore[method-assign]
    result = await platform.poke("20002")
    assert result.success is True
    assert api.calls[0] == ("send_poke", {"user_id": "20002", "group_id": "123"})


async def test_poke_without_speaker_fails() -> None:
    platform = _platform()
    assert (await platform.poke()).success is False


async def test_upload_confines_path_to_share_dir(tmp_path: Path) -> None:
    share = tmp_path / "share"
    share.mkdir()
    target = share / "a.txt"
    target.write_text("x", encoding="utf-8")
    platform = _platform(limits=LimitsConfig(upload_dir=str(share)))
    api = FakeApi({"file_id": "fid"})
    platform.api = api  # type: ignore[method-assign]
    result = await platform.upload_group_file(str(target))
    assert result.success is True
    assert api.calls[0][0] == "upload_group_file"
    assert api.calls[0][1]["file"] == str(target.resolve())


async def test_upload_accepts_path_relative_to_share_dir(tmp_path: Path) -> None:
    share = tmp_path / "share"
    share.mkdir()
    (share / "a.txt").write_text("x", encoding="utf-8")
    platform = _platform(limits=LimitsConfig(upload_dir=str(share)))
    api = FakeApi({"file_id": "fid"})
    platform.api = api  # type: ignore[method-assign]
    result = await platform.upload_group_file("a.txt")
    assert result.success is True
    assert api.calls[0][1]["file"] == str((share / "a.txt").resolve())


async def test_upload_rejects_outside_path(tmp_path: Path) -> None:
    share = tmp_path / "share"
    share.mkdir()
    outside = tmp_path / "b.txt"
    outside.write_text("x", encoding="utf-8")
    platform = _platform(limits=LimitsConfig(upload_dir=str(share)))
    result = await platform.upload_group_file(str(outside))
    assert result.success is False
    assert "只能上传" in (result.error or "")


async def test_upload_rejects_large_file(tmp_path: Path) -> None:
    target = tmp_path / "big.bin"
    target.write_bytes(b"x" * 10)
    platform = _platform(limits=LimitsConfig(upload_dir=str(tmp_path), upload_max_bytes=5))
    assert (await platform.upload_group_file(str(target))).success is False


async def test_tool_wrappers(tmp_path: Path) -> None:
    platform = _platform()
    _remember(platform, real_seq=7, message_id=42)
    api = FakeApi(data=None)  # type: ignore[arg-type]
    platform.api = api  # type: ignore[method-assign]

    assert await poke(platform, {}) == "ok"
    assert await poke(platform, {"user_id": 20002}) == "ok"
    assert (await poke(platform, {"user_id": "abc"})).startswith("错误:")
    assert await send_forward(platform, {"real_seqs": [7]}) == "ok"
    assert await send_forward(platform, {"real_seqs": ["7"]}) == "ok"
    assert (await send_forward(platform, {"real_seqs": []})).startswith("错误:")
    assert (await upload_group_file(platform, {})).startswith("错误:")


def test_tool_specs_are_registered() -> None:
    from crupest_chatbot_plugin.tools import TOOL_SPECS

    names = {spec["name"] for spec in TOOL_SPECS}
    assert {"chatbot_send_message", "chatbot_poke", "chatbot_send_forward", "chatbot_upload_group_file"} <= names
