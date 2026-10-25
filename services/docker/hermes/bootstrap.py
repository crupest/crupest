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

PLUGIN_SRC = Path("/opt/qqbot-plugin")
PLUGIN_NAME = "crupest-qqbot"
# Directory name must be a valid Python package name; the manifest name may keep hyphens.
PLUGIN_DEST = HERMES_HOME / "plugins" / "crupest_qqbot"
ADAPTER_TOKEN = os.environ.get("QQBOT_ADAPTER_TOKEN", "")

TOOLSET_MARKER = HERMES_HOME / ".crupest_qqbot_toolsets_initialized"


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
        fail("QQBOT_ADAPTER_TOKEN is empty (check envs/hermes.env)")

    log(f"installing QQ plugin into {PLUGIN_DEST}")
    if PLUGIN_DEST.exists():
        shutil.rmtree(PLUGIN_DEST)
    shutil.copytree(PLUGIN_SRC, PLUGIN_DEST)

    # The gateway inherits QQBOT_* from the container environment (env_file);
    # nothing needs to be written. Old image leftovers are cleaned manually
    # during migration, not at every boot.

    run(HERMES_BIN, "plugins", "enable", PLUGIN_NAME, "--no-allow-tool-override", quiet=True)


def write_first_run_config() -> None:
    if TOOLSET_MARKER.exists():
        return
    log("writing first-run Hermes config")
    from ruamel.yaml import YAML

    path = HERMES_HOME / "config.yaml"
    if not path.exists():
        # The gateway has not run yet on a fresh volume; start from an empty
        # mapping — Hermes merges its defaults at load time.
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
        "onebot",
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
    TOOLSET_MARKER.touch()


def ensure_feature_config() -> None:
    """Apply the vision/web defaults without requiring a fresh config."""
    path = HERMES_HOME / "config.yaml"
    if not path.exists() or not os.environ.get("DEEPSEEK_API_KEY"):
        return
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    with open(path, encoding="utf-8") as handle:
        config = yaml.load(handle) or {}
    changed = False

    model = config.get("model")
    if isinstance(model, dict) and model.get("provider") in (None, "deepseek"):
        if model.get("default") in ("deepseek-chat", "deepseek-reasoner"):
            model["default"] = "deepseek-v4-flash"
            model["supports_vision"] = True
            changed = True
        elif model.get("default") == "deepseek-v4-flash" and not model.get("supports_vision"):
            model["supports_vision"] = True
            changed = True

    agent = config.setdefault("agent", {})
    if isinstance(agent, dict) and not agent.get("image_input_mode"):
        agent["image_input_mode"] = "native"
        changed = True

    web = config.setdefault("web", {})
    if isinstance(web, dict) and not web.get("backend"):
        web["backend"] = "crupest-deepseek"
        changed = True

    if changed:
        log("applying DeepSeek vision/web defaults")
        with open(path, "w", encoding="utf-8") as handle:
            yaml.dump(config, handle)


def run_hermes() -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    (HERMES_HOME / "plugins").mkdir(parents=True, exist_ok=True)
    install_soul()
    install_plugin()
    write_first_run_config()
    ensure_feature_config()


def main() -> None:
    run_hermes()


if __name__ == "__main__":
    main()
