"""TOML configuration shared by both processes.

The same file is mounted into the adapter and the plugin.  Each side validates
only the fields it uses: adding a key for one process must never stop the other
from starting.
"""
from __future__ import annotations

import hashlib
import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigError

_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class ChatConfig:
    group_id: int | None = None
    user_id: int | None = None
    active_window_seconds: float = 300.0


@dataclass(frozen=True)
class AdapterConfig:
    onebot_port: int = 18800
    plugin_port: int = 18810
    onebot_path: str = "/onebot"
    plugin_path: str = "/hermes"
    call_timeout_seconds: float = 60.0
    upload_timeout_seconds: float = 600.0
    queue_size: int = 1024


@dataclass(frozen=True)
class PluginConfig:
    media_max_bytes: int = 1024 * 1024 * 1024
    strip_markdown: bool = True
    max_message_length: int = 4500
    rpc_timeout_margin_seconds: float = 20.0
    cache_dir: str = "/opt/data/share/media"


@dataclass(frozen=True)
class NotifyConfig:
    poke: bool = False
    member_change: bool = False


@dataclass(frozen=True)
class FeaturesConfig:
    """What the model is allowed to put into a message."""

    at: bool = True
    at_all: bool = True
    face: bool = True
    dice: bool = True
    rps: bool = True
    poke: bool = True
    forward: bool = True
    upload: bool = True


@dataclass(frozen=True)
class LimitsConfig:
    poke_cooldown_seconds: float = 10.0
    at_all_cooldown_seconds: float = 0.0
    forward_cooldown_seconds: float = 10.0
    forward_max_nodes: int = 20
    upload_cooldown_seconds: float = 60.0
    upload_max_bytes: int = 50 * 1024 * 1024
    upload_dir: str = "/opt/data/share"
    max_segments_per_message: int = 100


@dataclass(frozen=True)
class LoggingConfig:
    level: str = "INFO"
    message_preview_chars: int = 80


@dataclass(frozen=True)
class Config:
    chat: ChatConfig = field(default_factory=ChatConfig)
    adapter: AdapterConfig = field(default_factory=AdapterConfig)
    plugin: PluginConfig = field(default_factory=PluginConfig)
    notify: NotifyConfig = field(default_factory=NotifyConfig)
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    limits: LimitsConfig = field(default_factory=LimitsConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    sha: str = ""


@dataclass(frozen=True)
class Secrets:
    onebot_ws_token: str = ""
    plugin_ws_token: str = ""


def _section(data: dict[str, Any], name: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(name, {})
    if not isinstance(value, dict):
        errors.append(f"[{name}] 必须是表")
        return {}
    return value


def _as_int(raw: Any, label: str, errors: list[str], default: int, minimum: int | None = None) -> int:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, int):
        errors.append(f"{label} 必须是整数")
        return default
    if minimum is not None and raw < minimum:
        errors.append(f"{label} 必须 >= {minimum}")
    return raw


def _as_float(raw: Any, label: str, errors: list[str], default: float, minimum: float | None = None) -> float:
    if raw is None:
        return default
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        errors.append(f"{label} 必须是数字")
        return default
    value = float(raw)
    if minimum is not None and value < minimum:
        errors.append(f"{label} 必须 >= {minimum:g}")
    return value


def _as_bool(raw: Any, label: str, errors: list[str], default: bool) -> bool:
    if raw is None:
        return default
    if not isinstance(raw, bool):
        errors.append(f"{label} 必须是布尔值")
        return default
    return raw


def _as_str(raw: Any, label: str, errors: list[str], default: str) -> str:
    if raw is None:
        return default
    if not isinstance(raw, str):
        errors.append(f"{label} 必须是字符串")
        return default
    return raw


def _build(data: dict[str, Any], *, require_chat: bool = True) -> Config:
    errors: list[str] = []

    chat_raw = _section(data, "chat", errors)
    group_id = _as_int(chat_raw.get("group_id"), "chat.group_id", errors, 0, minimum=1)
    user_id = _as_int(chat_raw.get("user_id"), "chat.user_id", errors, 0, minimum=1)
    if require_chat and not group_id and not user_id:
        errors.append("chat.group_id 与 chat.user_id 至少填一个（或设置 CHATBOT_GROUP_ID / CHATBOT_USER_ID）")
    chat = ChatConfig(
        group_id=group_id or None,
        user_id=user_id or None,
        active_window_seconds=_as_float(
            chat_raw.get("active_window_seconds"), "chat.active_window_seconds", errors, 300.0, minimum=1.0,
        ),
    )

    adapter_raw = _section(data, "adapter", errors)
    adapter = AdapterConfig(
        onebot_port=_as_int(adapter_raw.get("onebot_port"), "adapter.onebot_port", errors, 18800, minimum=1),
        plugin_port=_as_int(adapter_raw.get("plugin_port"), "adapter.plugin_port", errors, 18810, minimum=1),
        onebot_path=_as_str(adapter_raw.get("onebot_path"), "adapter.onebot_path", errors, "/onebot"),
        plugin_path=_as_str(adapter_raw.get("plugin_path"), "adapter.plugin_path", errors, "/hermes"),
        call_timeout_seconds=_as_float(
            adapter_raw.get("call_timeout_seconds"), "adapter.call_timeout_seconds", errors, 60.0, minimum=1.0,
        ),
        upload_timeout_seconds=_as_float(
            adapter_raw.get("upload_timeout_seconds"), "adapter.upload_timeout_seconds", errors, 600.0, minimum=1.0,
        ),
        queue_size=_as_int(adapter_raw.get("queue_size"), "adapter.queue_size", errors, 1024, minimum=16),
    )
    if adapter.onebot_port == adapter.plugin_port:
        errors.append("adapter.onebot_port 与 adapter.plugin_port 不能相同")

    plugin_raw = _section(data, "plugin", errors)
    plugin = PluginConfig(
        media_max_bytes=_as_int(
            plugin_raw.get("media_max_bytes"), "plugin.media_max_bytes", errors, 1024 * 1024 * 1024, minimum=1024,
        ),
        strip_markdown=_as_bool(plugin_raw.get("strip_markdown"), "plugin.strip_markdown", errors, True),
        max_message_length=_as_int(
            plugin_raw.get("max_message_length"), "plugin.max_message_length", errors, 4500, minimum=100,
        ),
        rpc_timeout_margin_seconds=_as_float(
            plugin_raw.get("rpc_timeout_margin_seconds"),
            "plugin.rpc_timeout_margin_seconds", errors, 20.0, minimum=5.0,
        ),
        cache_dir=_as_str(
            plugin_raw.get("cache_dir"), "plugin.cache_dir", errors, "/opt/data/share/media",
        ),
    )

    notify_raw = _section(data, "notify", errors)
    notify = NotifyConfig(
        poke=_as_bool(notify_raw.get("poke"), "notify.poke", errors, False),
        member_change=_as_bool(notify_raw.get("member_change"), "notify.member_change", errors, False),
    )

    features_raw = _section(data, "features", errors)
    features = FeaturesConfig(
        at=_as_bool(features_raw.get("at"), "features.at", errors, True),
        at_all=_as_bool(features_raw.get("at_all"), "features.at_all", errors, True),
        face=_as_bool(features_raw.get("face"), "features.face", errors, True),
        dice=_as_bool(features_raw.get("dice"), "features.dice", errors, True),
        rps=_as_bool(features_raw.get("rps"), "features.rps", errors, True),
        poke=_as_bool(features_raw.get("poke"), "features.poke", errors, True),
        forward=_as_bool(features_raw.get("forward"), "features.forward", errors, True),
        upload=_as_bool(features_raw.get("upload"), "features.upload", errors, True),
    )

    limits_raw = _section(data, "limits", errors)
    limits = LimitsConfig(
        poke_cooldown_seconds=_as_float(
            limits_raw.get("poke_cooldown_seconds"), "limits.poke_cooldown_seconds", errors, 10.0, minimum=0.0,
        ),
        at_all_cooldown_seconds=_as_float(
            limits_raw.get("at_all_cooldown_seconds"),
            "limits.at_all_cooldown_seconds", errors, 0.0, minimum=0.0,
        ),
        forward_cooldown_seconds=_as_float(
            limits_raw.get("forward_cooldown_seconds"),
            "limits.forward_cooldown_seconds", errors, 10.0, minimum=0.0,
        ),
        forward_max_nodes=_as_int(
            limits_raw.get("forward_max_nodes"), "limits.forward_max_nodes", errors, 20, minimum=1,
        ),
        upload_cooldown_seconds=_as_float(
            limits_raw.get("upload_cooldown_seconds"),
            "limits.upload_cooldown_seconds", errors, 60.0, minimum=0.0,
        ),
        upload_max_bytes=_as_int(
            limits_raw.get("upload_max_bytes"), "limits.upload_max_bytes", errors, 50 * 1024 * 1024, minimum=1,
        ),
        upload_dir=_as_str(limits_raw.get("upload_dir"), "limits.upload_dir", errors, "/opt/data/share"),
        max_segments_per_message=_as_int(
            limits_raw.get("max_segments_per_message"),
            "limits.max_segments_per_message", errors, 100, minimum=1,
        ),
    )

    logging_raw = _section(data, "logging", errors)
    level = _as_str(logging_raw.get("level"), "logging.level", errors, "INFO").upper()
    if level not in _LOG_LEVELS:
        errors.append(f"logging.level 必须是 {'/'.join(sorted(_LOG_LEVELS))} 之一")
    log_cfg = LoggingConfig(
        level=level,
        message_preview_chars=_as_int(
            logging_raw.get("message_preview_chars"), "logging.message_preview_chars", errors, 80, minimum=0,
        ),
    )

    if errors:
        raise ConfigError(errors)
    return Config(
        chat=chat, adapter=adapter, plugin=plugin, notify=notify,
        features=features, limits=limits, logging=log_cfg,
    )


def _env_id(name: str) -> int | str | None:
    """QQ ids arrive as strings; keep a bad value as-is so validation names it."""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return raw


def _env_chat(data: dict[str, Any]) -> dict[str, Any]:
    """Chat binding from the environment; it wins over the file."""
    group = _env_id("CHATBOT_GROUP_ID")
    user = _env_id("CHATBOT_USER_ID")
    if group is None and user is None:
        return data
    raw_chat = data.get("chat")
    chat = dict(raw_chat) if isinstance(raw_chat, dict) else {}
    chat["group_id"] = group
    chat["user_id"] = user
    merged = dict(data)
    merged["chat"] = chat
    return merged


def load_config(path: str | Path | None = None, *, require_chat: bool = True) -> Config:
    """Parse the shared TOML; a missing file means built-in defaults.

    ``CHATBOT_GROUP_ID`` / ``CHATBOT_USER_ID`` override the ``[chat]`` binding.
    ``require_chat=False`` lets the plugin start before the adapter has created
    the file; it learns the binding from ``adapter_ready``.
    """
    raw = b""
    data: dict[str, Any] = {}
    if path is not None:
        config_path = Path(path)
        if config_path.exists():
            try:
                raw = config_path.read_bytes()
            except OSError as exc:
                raise ConfigError([f"读取 {config_path} 失败: {exc}"]) from exc
            try:
                data = tomllib.loads(raw.decode("utf-8"))
            except (tomllib.TOMLDecodeError, UnicodeDecodeError) as exc:
                raise ConfigError([f"{config_path} 不是合法的 TOML: {exc}"]) from exc
    data = _env_chat(data)
    config = _build(data, require_chat=require_chat)
    sha = hashlib.sha256(raw).hexdigest()[:16]
    return Config(
        chat=config.chat,
        adapter=config.adapter,
        plugin=config.plugin,
        notify=config.notify,
        features=config.features,
        limits=config.limits,
        logging=config.logging,
        sha=sha,
    )


def load_secrets() -> Secrets:
    """Tokens from the environment; compose injects them via env_file."""
    onebot = os.environ.get("CHATBOT_ONEBOT_TOKEN", "").strip()
    plugin = os.environ.get("CHATBOT_PLUGIN_TOKEN", "").strip()
    errors: list[str] = []
    if not onebot:
        errors.append("CHATBOT_ONEBOT_TOKEN 不能为空")
    if not plugin:
        errors.append("CHATBOT_PLUGIN_TOKEN 不能为空")
    if errors:
        raise ConfigError(errors)
    return Secrets(onebot_ws_token=onebot, plugin_ws_token=plugin)
