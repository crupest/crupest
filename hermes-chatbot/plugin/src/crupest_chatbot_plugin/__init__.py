"""Hermes plugin entry point."""
from __future__ import annotations

import logging
import os
from typing import Any

from crupest_chatbot_core.config import load_config

from .adapter import QQPlatform
from .media import MediaFetcher
from .tools import register_tools

logger = logging.getLogger(__name__)

PLATFORM_NAME = "onebot"
DEFAULT_CONFIG_PATH = "/opt/chatbot/config.toml"
DEFAULT_ADAPTER_URL = "ws://127.0.0.1:18810/hermes"

_current: QQPlatform | None = None


def current_platform() -> QQPlatform | None:
    """The adapter instance Hermes built, for tools that need it."""
    return _current


def check_requirements() -> bool:
    """Passive probe: the plugin's dependencies are installed with the plugin."""
    return True


def validate_config(config: Any) -> bool:
    """Everything we need lives in the shared TOML/env, not in the platform block."""
    return True


def build_platform(config: Any = None) -> QQPlatform:
    """Build the adapter from the shared config + env. Called by the registry factory."""
    global _current
    config_path = os.environ.get("CHATBOT_CONFIG", DEFAULT_CONFIG_PATH)
    # The adapter may still be creating the file on first boot; without it the
    # binding arrives in adapter_ready and the media settings use defaults.
    has_config = os.path.exists(config_path)
    shared = load_config(config_path, require_chat=False)

    if shared.chat.group_id:
        chat_kind, chat_id = "group", str(shared.chat.group_id)
    elif shared.chat.user_id:
        chat_kind, chat_id = "dm", str(shared.chat.user_id)
    else:
        home = os.environ.get("CHATBOT_HOME_CHANNEL", "")
        prefix, _, value = home.partition(":")
        chat_kind, chat_id = ("group" if prefix == "group" else "dm"), value

    cache_dir = os.environ.get("CHATBOT_CACHE_DIR") or shared.plugin.cache_dir
    fetcher = MediaFetcher(max_bytes=shared.plugin.media_max_bytes, cache_dir=cache_dir)

    extra = getattr(config, "extra", None) or {}
    url = os.environ.get("CHATBOT_ADAPTER_URL") or str(extra.get("url") or DEFAULT_ADAPTER_URL)
    token = (
        os.environ.get("CHATBOT_ADAPTER_TOKEN")
        or str(extra.get("token") or "")
        or str(getattr(config, "token", "") or "")
    )

    margin = shared.plugin.rpc_timeout_margin_seconds
    platform = QQPlatform(
        config,
        url=url,
        token=token,
        chat_kind=chat_kind,
        chat_id=chat_id,
        config_sha=shared.sha if has_config else "",
        call_timeout=shared.adapter.call_timeout_seconds + margin,
        upload_timeout=shared.adapter.upload_timeout_seconds + margin * 2,
        media_fetcher=fetcher,
        strip_markdown=shared.plugin.strip_markdown,
    )
    _current = platform
    return platform


def _adapter_factory(config: Any) -> QQPlatform:
    return build_platform(config)


def register(ctx: Any) -> None:
    """Hermes plugin hook: register the platform adapter and its tools."""
    register_platform = getattr(ctx, "register_platform", None)
    if not callable(register_platform):
        logger.error("plugin context has no register_platform; QQ platform unavailable")
        return

    register_platform(
        name=PLATFORM_NAME,
        label="QQ (NapCat)",
        adapter_factory=_adapter_factory,
        check_fn=check_requirements,
        validate_config=validate_config,
        required_env=["CHATBOT_CONFIG", "CHATBOT_ADAPTER_URL", "CHATBOT_ADAPTER_TOKEN"],
        # Where cron/cross-platform messages go; bootstrap writes group:<id>.
        cron_deliver_env_var="CHATBOT_HOME_CHANNEL",
        install_hint="aiohttp 与 crupest-hermes-chatbot-core 需要装进 Hermes 的 Python 环境",
        max_message_length=4500,
        emoji="🐧",
        platform_hint=(
            "你正在 QQ 里聊天。消息以 `[昵称(QQ号)#序号]` 开头，那是发送者；"
            "`[@self]` 表示有人 @ 了你，`[@数字]` 表示 @ 了别人；"
            '`[image1 id="…" cache="…"]` 这类是媒体占位，cache 后面是本地路径、failed 或 none。'
        ),
    )
    register_tools(ctx, current_platform)
