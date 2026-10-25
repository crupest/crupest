from __future__ import annotations

from pathlib import Path

import pytest
from crupest_qqbot_core.config import load_config, load_secrets
from crupest_qqbot_core.errors import ConfigError

MINIMAL = """
[chat]
group_id = 123456789
"""


def _write(tmp_path: Path, text: str, name: str = "config.toml") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_config(tmp_path: Path) -> None:
    config = load_config(_write(tmp_path, MINIMAL))
    assert config.chat.group_id == 123456789
    assert config.chat.user_id is None


def test_full_config(tmp_path: Path) -> None:
    text = """
[chat]
group_id = 1
user_id = 2
active_window_seconds = 120

[adapter]
onebot_port = 19000
plugin_port = 19010
call_timeout_seconds = 30
upload_timeout_seconds = 300

[plugin]
media_max_bytes = 1024
strip_markdown = false
max_message_length = 1000

[notify]
poke = true
member_change = true

[logging]
level = "debug"
message_preview_chars = 10
"""
    config = load_config(_write(tmp_path, text))
    assert config.chat.user_id == 2
    assert config.adapter.onebot_port == 19000
    assert config.plugin.max_message_length == 1000
    assert config.plugin.strip_markdown is False
    assert config.notify.poke is True
    assert config.logging.level == "DEBUG"
    assert len(config.sha) == 16


def test_unknown_keys_are_ignored(tmp_path: Path) -> None:
    config = load_config(_write(tmp_path, MINIMAL + "\n[future]\nwhatever = 1\n"))
    assert config.chat.group_id == 123456789


def test_missing_chat_ids(tmp_path: Path) -> None:
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write(tmp_path, "[chat]\nactive_window_seconds = 10\n"))
    assert any("至少填一个" in e for e in excinfo.value.errors)


def test_errors_are_aggregated(tmp_path: Path) -> None:
    text = """
[chat]
group_id = "not-an-int"

[adapter]
onebot_port = 70000
plugin_port = 70000
"""
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write(tmp_path, text))
    assert len(excinfo.value.errors) >= 3


def test_same_ports_rejected(tmp_path: Path) -> None:
    text = MINIMAL + "\n[adapter]\nonebot_port = 19000\nplugin_port = 19000\n"
    with pytest.raises(ConfigError) as excinfo:
        load_config(_write(tmp_path, text))
    assert any("不能相同" in e for e in excinfo.value.errors)


def test_bad_toml(tmp_path: Path) -> None:
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, "[chat\n"))


def test_missing_file_needs_env_binding(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QQBOT_GROUP_ID", raising=False)
    monkeypatch.delenv("QQBOT_USER_ID", raising=False)
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.toml")

    monkeypatch.setenv("QQBOT_GROUP_ID", "123456")
    config = load_config(tmp_path / "nope.toml")
    assert config.chat.group_id == 123456
    assert config.chat.active_window_seconds == 300.0


def test_env_binding_overrides_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QQBOT_USER_ID", "100001")
    monkeypatch.delenv("QQBOT_GROUP_ID", raising=False)
    config = load_config(_write(tmp_path, MINIMAL))
    assert config.chat.user_id == 100001
    assert config.chat.group_id is None


def test_missing_file_allowed_for_plugin(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QQBOT_GROUP_ID", raising=False)
    monkeypatch.delenv("QQBOT_USER_ID", raising=False)
    config = load_config(tmp_path / "nope.toml", require_chat=False)
    assert config.chat.group_id is None
    assert config.chat.user_id is None


def test_sha_is_stable_and_content_addressed(tmp_path: Path) -> None:
    first = load_config(_write(tmp_path, MINIMAL))
    second = load_config(_write(tmp_path, MINIMAL))
    assert first.sha == second.sha
    changed = load_config(_write(tmp_path, MINIMAL + "\n# comment\n"))
    assert changed.sha != first.sha


def test_cache_dir_default_and_override(tmp_path: Path) -> None:
    default = load_config(_write(tmp_path, MINIMAL))
    assert default.plugin.cache_dir == "/opt/data/share/media"
    overridden = load_config(_write(tmp_path, MINIMAL + '\n[plugin]\ncache_dir = "/srv/media"\n'))
    assert overridden.plugin.cache_dir == "/srv/media"


def test_secrets_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QQBOT_ONEBOT_TOKEN", "env-a")
    monkeypatch.setenv("QQBOT_PLUGIN_TOKEN", "env-b")
    secrets = load_secrets()
    assert secrets.onebot_ws_token == "env-a"
    assert secrets.plugin_ws_token == "env-b"


def test_secrets_missing_everything(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("QQBOT_ONEBOT_TOKEN", raising=False)
    monkeypatch.delenv("QQBOT_PLUGIN_TOKEN", raising=False)
    with pytest.raises(ConfigError) as excinfo:
        load_secrets()
    assert len(excinfo.value.errors) == 2
    assert all("QQBOT_" in error for error in excinfo.value.errors)


def test_secrets_reject_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QQBOT_ONEBOT_TOKEN", "")
    monkeypatch.setenv("QQBOT_PLUGIN_TOKEN", "b")
    with pytest.raises(ConfigError) as excinfo:
        load_secrets()
    assert any("QQBOT_ONEBOT_TOKEN" in error for error in excinfo.value.errors)
