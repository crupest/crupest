#!/usr/bin/env python3
"""Hermes gateway bootstrap: SOUL, QQ plugin, first-run config."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path("/opt/hermes")
VENV = APP_DIR / "venv"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data/.hermes"))
CONFIG_PATH = HERMES_HOME / "config.yaml"
PLUGINS_DIR = HERMES_HOME / "plugins"

PLATFORM_NAME = "onebot"
PLUGIN_SRC = Path("/opt/chatbot-plugin")
PLUGIN_NAME = "crupest-chatbot"
PLUGIN_TOOLSET = "chatbot"
CONNECTIONS_TOOLSET = "connections"
# Directory name must be a valid Python package name; the manifest name may keep hyphens.
PLUGIN_DEST = PLUGINS_DIR / PLUGIN_NAME.replace("-", "_")
ADAPTER_TOKEN = os.environ.get("CHATBOT_ADAPTER_TOKEN", "")


def log(message: str) -> None:
    print(f"[bootstrap] {message}", file=sys.stderr, flush=True)


def fail(message: str) -> None:
    log(message)
    raise SystemExit(1)


def install_soul() -> None:
    """Keep the volume's SOUL in sync with the image, backing up local edits."""
    source = APP_DIR / "SOUL.md"
    target = HERMES_HOME / "SOUL.md"
    if not source.exists():
        return
    if not target.exists() or target.stat().st_size == 0:
        log("installing default SOUL.md")
        shutil.copyfile(source, target)
        return
    if target.read_bytes() == source.read_bytes():
        return
    backup = target.with_name(f"SOUL.md.bak.{int(time.time())}")
    shutil.copyfile(target, backup)
    shutil.copyfile(source, target)
    log(f"updated SOUL.md (backup: {backup.name})")


def install_plugin() -> None:
    """Copy the baked plugin into the volume; config enabling happens later."""
    if not PLUGIN_SRC.is_dir():
        fail(f"baked plugin missing at {PLUGIN_SRC}")
    if not ADAPTER_TOKEN:
        fail("CHATBOT_ADAPTER_TOKEN is empty (check envs/hermes.env)")

    log(f"installing QQ plugin into {PLUGIN_DEST}")
    if PLUGIN_DEST.exists():
        shutil.rmtree(PLUGIN_DEST)
    shutil.copytree(PLUGIN_SRC, PLUGIN_DEST)


def prepare_config(*, fresh: bool) -> None:
    """Apply first-run and every required config change in one load/write pass."""
    if fresh:
        log("writing first-run Hermes config")

    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    with open(CONFIG_PATH, encoding="utf-8") as handle:
        config = yaml.load(handle) or {}
    changed = fresh

    if fresh:
        # 首次启动的默认值；已有卷不覆盖这些用户可改的设置。
        config["group_sessions_per_user"] = False

        display = config.setdefault("display", {})
        if not isinstance(display, dict):
            display = {}
            config["display"] = display
        display["memory_notifications"] = "off"

        gateway = config.setdefault("gateway", {})
        if isinstance(gateway, dict):
            timestamps = gateway.setdefault("message_timestamps", {})
            if isinstance(timestamps, dict):
                timestamps.setdefault("enabled", True)

        if os.environ.get("DEEPSEEK_API_KEY") and not config.get("model"):
            config["model"] = {
                "provider": "deepseek",
                "default": "deepseek-v4-flash",
                "supports_vision": True,
            }

        agent = config.setdefault("agent", {})
        if isinstance(agent, dict):
            agent.setdefault("image_input_mode", "native")

        web = config.setdefault("web", {})
        if isinstance(web, dict):
            web.setdefault("backend", "crupest-deepseek")

        platforms = config.setdefault("platforms", {})
        if isinstance(platforms, dict):
            onebot_platform = platforms.setdefault(PLATFORM_NAME, {})
            if isinstance(onebot_platform, dict):
                onebot_platform["enabled"] = True

    # 保持 0.19 的会话保留行为；0.22 默认开启自动清理。
    sessions = config.setdefault("sessions", {})
    if not isinstance(sessions, dict):
        sessions = {}
        config["sessions"] = sessions
    if sessions.get("auto_prune") is not False:
        sessions["auto_prune"] = False
        changed = True

    # 启用 QQ 插件。直接写 config，避免 source build 缺少 PM runtime。
    plugins = config.setdefault("plugins", {})
    if not isinstance(plugins, dict):
        plugins = {}
        config["plugins"] = plugins
        changed = True
    enabled = plugins.setdefault("enabled", [])
    if not isinstance(enabled, list):
        enabled = []
        plugins["enabled"] = enabled
        changed = True
    if PLUGIN_NAME not in enabled:
        enabled.append(PLUGIN_NAME)
        changed = True
    disabled = plugins.setdefault("disabled", [])
    if isinstance(disabled, list) and PLUGIN_NAME in disabled:
        disabled.remove(PLUGIN_NAME)
        changed = True
    entries = plugins.setdefault("entries", {})
    if isinstance(entries, dict):
        entry = entries.setdefault(PLUGIN_NAME, {})
        if isinstance(entry, dict) and entry.get("allow_tool_override") is not False:
            entry["allow_tool_override"] = False
            changed = True

    known = config.setdefault("known_plugin_toolsets", {})
    if isinstance(known, dict) and known.get(PLUGIN_TOOLSET) != [PLUGIN_TOOLSET]:
        known[PLUGIN_TOOLSET] = [PLUGIN_TOOLSET]
        changed = True

    # 启用 0.22 的 Connections toolset（托管应用连接 + MCP 管理）。
    toolsets = config.setdefault("platform_toolsets", {})
    if fresh:
        toolsets[PLATFORM_NAME] = [
            "file",
            "terminal",
            "cronjob",
            "memory",
            "skills",
            "todo",
            "clarify",
            PLUGIN_TOOLSET,
            CONNECTIONS_TOOLSET,
            "session_search",
            "web",
            "vision",
        ]
    elif isinstance(toolsets, dict):
        onebot = toolsets.get(PLATFORM_NAME)
        if isinstance(onebot, list) and CONNECTIONS_TOOLSET not in onebot:
            onebot.append(CONNECTIONS_TOOLSET)
            changed = True

    if changed:
        with open(CONFIG_PATH, "w", encoding="utf-8") as handle:
            yaml.dump(config, handle)


def migrate_config() -> None:
    """Apply Hermes' non-interactive Docker config migrations before boot."""
    script = APP_DIR / "scripts" / "docker_config_migrate.py"
    if not script.exists():
        log(f"config migration script missing at {script}")
        return
    command = [str(VENV / "bin" / "python"), str(script)]
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError:
        fail(f"missing executable: {command[0]}")
    except subprocess.CalledProcessError as exc:
        fail(f"command failed ({exc.returncode}): {' '.join(command)}")


def bootstrap() -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    PLUGINS_DIR.mkdir(parents=True, exist_ok=True)
    fresh = not CONFIG_PATH.exists()
    if fresh:
        # Give the migrator a file to stamp; prepare_config fills in defaults after.
        CONFIG_PATH.write_text("{}\n", encoding="utf-8")

    install_soul()
    install_plugin()
    migrate_config()
    prepare_config(fresh=fresh)


if __name__ == "__main__":
    bootstrap()
