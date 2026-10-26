from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from crupest_chatbot_plugin import build_platform, current_platform, register
from crupest_chatbot_plugin.adapter import QQPlatform


class FakeCtx:
    def __init__(self) -> None:
        self.platform_kwargs: dict | None = None
        self.tools: list[dict] = []

    def register_platform(self, **kwargs) -> None:
        self.platform_kwargs = kwargs

    def register_tool(self, **kwargs) -> None:
        self.tools.append(kwargs)


CONFIG = """
[chat]
group_id = 123456

[plugin]
media_max_bytes = 1024
"""


@pytest.fixture
def config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "config.toml"
    path.write_text(CONFIG, encoding="utf-8")
    monkeypatch.setenv("CHATBOT_CONFIG", str(path))
    monkeypatch.setenv("CHATBOT_ADAPTER_URL", "ws://adapter:18810/hermes")
    monkeypatch.setenv("CHATBOT_ADAPTER_TOKEN", "tok")
    monkeypatch.setenv("CHATBOT_CACHE_DIR", str(tmp_path / "cache"))
    return path


def test_register_uses_real_platform_api(config_path: Path) -> None:
    ctx = FakeCtx()
    register(ctx)

    assert ctx.platform_kwargs is not None
    kwargs = ctx.platform_kwargs
    assert kwargs["name"] == "onebot"
    assert callable(kwargs["adapter_factory"])
    assert kwargs["check_fn"]() is True
    assert kwargs["validate_config"](None) is True
    assert kwargs["max_message_length"] == 4500
    assert "CHATBOT_CONFIG" in kwargs["required_env"]
    assert kwargs["cron_deliver_env_var"] == "CHATBOT_HOME_CHANNEL"
    assert kwargs["platform_hint"]


def test_register_declares_all_tools(config_path: Path) -> None:
    ctx = FakeCtx()
    register(ctx)
    assert sorted(tool["name"] for tool in ctx.tools) == [
        "chatbot_fetch_group_file",
        "chatbot_fetch_media",
        "chatbot_get_group_file_system_info",
        "chatbot_get_group_file_url",
        "chatbot_get_group_info",
        "chatbot_get_group_member",
        "chatbot_get_login_info",
        "chatbot_get_user_info",
        "chatbot_list_group_files",
        "chatbot_list_group_members",
        "chatbot_react",
        "chatbot_read_forward",
        "chatbot_read_history",
        "chatbot_set_avatar",
        "chatbot_set_group_card",
        "chatbot_set_nickname",
        "chatbot_transcribe_voice",
    ]
    for tool in ctx.tools:
        assert callable(tool["handler"])
        assert tool["toolset"] == "chatbot"
        assert tool["is_async"] is True
        assert tool["schema"]["name"] == tool["name"]
        assert tool["schema"]["parameters"]["type"] == "object"


async def test_tool_without_platform_reports_error(config_path: Path) -> None:
    ctx = FakeCtx()
    register(ctx)
    handler = next(tool["handler"] for tool in ctx.tools if tool["name"] == "chatbot_react")
    assert (await handler({"real_seq": 1, "emoji_id": "1"})).startswith("错误:")


def test_adapter_factory_builds_platform(config_path: Path) -> None:
    ctx = FakeCtx()
    register(ctx)
    platform = ctx.platform_kwargs["adapter_factory"](SimpleNamespace(extra={}))
    assert isinstance(platform, QQPlatform)
    assert platform.chat_key == "group:123456"
    assert platform.media is not None
    assert current_platform() is platform


def test_extra_overrides_default_url(config_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CHATBOT_ADAPTER_URL")
    monkeypatch.delenv("CHATBOT_ADAPTER_TOKEN")
    platform = build_platform(SimpleNamespace(extra={"url": "ws://from-extra"}, token="t2"))
    assert platform._url == "ws://from-extra"
    assert platform._token == "t2"


def test_env_wins_over_extra(config_path: Path) -> None:
    platform = build_platform(SimpleNamespace(extra={"url": "ws://from-extra"}, token="t2"))
    assert platform._url == "ws://adapter:18810/hermes"
    assert platform._token == "tok"


def test_register_without_hook_is_safe() -> None:
    class Empty:
        pass

    register(Empty())  # must not raise
