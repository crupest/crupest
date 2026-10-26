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
HERMES_BIN = VENV / "bin/hermes"

PLUGIN_SRC = Path("/opt/chatbot-plugin")
PLUGIN_NAME = "crupest-chatbot"
# Directory name must be a valid Python package name; the manifest name may keep hyphens.
PLUGIN_DEST = HERMES_HOME / "plugins" / "crupest_chatbot"
ADAPTER_TOKEN = os.environ.get("CHATBOT_ADAPTER_TOKEN", "")


def log(message: str) -> None:
    print(f"[bootstrap] {message}", file=sys.stderr, flush=True)


def fail(message: str) -> None:
    log(message)
    raise SystemExit(1)


def run(*args: object, quiet: bool = False) -> None:
    command = [str(arg) for arg in args]
    try:
        subprocess.run(
            command,
            check=True,
            stdout=subprocess.DEVNULL if quiet else None,
            stderr=subprocess.DEVNULL if quiet else None,
        )
    except FileNotFoundError:
        fail(f"missing executable: {command[0]}")
    except subprocess.CalledProcessError as exc:
        fail(f"command failed ({exc.returncode}): {' '.join(command)}")


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
    """Copy the baked plugin into the volume and enable it."""
    if not PLUGIN_SRC.is_dir():
        fail(f"baked plugin missing at {PLUGIN_SRC}")
    if not ADAPTER_TOKEN:
        fail("CHATBOT_ADAPTER_TOKEN is empty (check envs/hermes.env)")

    log(f"installing QQ plugin into {PLUGIN_DEST}")
    if PLUGIN_DEST.exists():
        shutil.rmtree(PLUGIN_DEST)
    shutil.copytree(PLUGIN_SRC, PLUGIN_DEST)

    # The gateway inherits CHATBOT_* from the container environment (env_file);
    # nothing needs to be written. Old image leftovers are cleaned manually
    # during migration, not at every boot.

    run(HERMES_BIN, "plugins", "enable", PLUGIN_NAME, "--no-allow-tool-override", quiet=True)


def write_first_run_config() -> None:
    """Seed Hermes config on a fresh volume only; upgrades stay manual."""
    path = HERMES_HOME / "config.yaml"
    if path.exists():
        return
    log("writing first-run Hermes config")
    from ruamel.yaml import YAML

    path.write_text("{}\n", encoding="utf-8")
    yaml = YAML()
    yaml.preserve_quotes = True
    with open(path, encoding="utf-8") as handle:
        config = yaml.load(handle) or {}

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

    toolsets = config.setdefault("platform_toolsets", {})
    toolsets["onebot"] = [
        "file",
        "terminal",
        "cronjob",
        "memory",
        "skills",
        "todo",
        "clarify",
        "chatbot",
        "session_search",
        "web",
        "vision",
    ]

    platforms = config.setdefault("platforms", {})
    if isinstance(platforms, dict):
        onebot_platform = platforms.setdefault("onebot", {})
        if isinstance(onebot_platform, dict):
            onebot_platform["enabled"] = True

    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle)

    env_path = HERMES_HOME / ".env"
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "GATEWAY_ALLOW_ALL_USERS=" not in existing:
        with open(env_path, "a", encoding="utf-8") as handle:
            handle.write("\nGATEWAY_ALLOW_ALL_USERS=true\n")
    env_path.chmod(0o600)


def run_hermes() -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    (HERMES_HOME / "plugins").mkdir(parents=True, exist_ok=True)
    install_soul()
    write_first_run_config()
    install_plugin()


def main() -> None:
    run_hermes()


if __name__ == "__main__":
    main()
