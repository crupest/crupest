#!/usr/bin/env python3
"""Shared bootstrap for the adapter and Hermes gateway containers."""
from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

APP_DIR = Path("/opt/hermes")
VENV = APP_DIR / "venv"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", "/opt/data/.hermes"))
ADAPTER_CONFIG = Path(os.environ.get("ONEBOT_ADAPTER_CONFIG", "/opt/data/.onebot_adapter/config.json"))
HANDOFF_FILE = Path(os.environ.get("ONEBOT_HANDOFF_FILE", "/opt/data/handoff/hermes_ws_token"))
ADAPTER_URL = os.environ.get("ONEBOT_ADAPTER_URL", "ws://onebot-adapter:18810/hermes")
ADAPTER_BIN = VENV / "bin/hermes-onebot-adapter"
HERMES_BIN = VENV / "bin/hermes"

TOOLSET_MARKER = HERMES_HOME / ".onebot_toolsets_initialized"
SELF_PROFILE_MARKER = HERMES_HOME / ".onebot_self_profile_initialized"
ENV_FILE = HERMES_HOME / ".entrypoint.env"


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


def init_adapter_config() -> None:
    if ADAPTER_CONFIG.exists() and ADAPTER_CONFIG.stat().st_size > 0:
        log("adapter config ready (created=0)")
        return
    ADAPTER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    ADAPTER_CONFIG.unlink(missing_ok=True)
    log(f"initializing adapter config at {ADAPTER_CONFIG}")
    run(ADAPTER_BIN, "--init-config", quiet=True)
    log("adapter config ready (created=1)")


def sync_onebot_token() -> str:
    from onebot_adapter.config import load_config, save_config

    try:
        cfg = load_config(ADAPTER_CONFIG)
    except Exception as exc:
        fail(f"cannot load adapter config {ADAPTER_CONFIG}: {exc}")
    env_token = os.environ.get("ONEBOT_WS_TOKEN", "").strip()
    if not env_token:
        log("ONEBOT_WS_TOKEN is not set; keeping config.json value")
        return cfg.hermes_ws_token
    if cfg.onebot_ws_token == env_token:
        return cfg.hermes_ws_token
    log("syncing ONEBOT_WS_TOKEN into adapter config")
    save_config(
        cfg.with_overrides(onebot_ws_token=env_token),
        ADAPTER_CONFIG,
        source="docker-entrypoint",
        reason="docker.onebot_ws_token",
        actor="docker-entrypoint",
        submitted_fields=["onebot_ws_token"],
    )
    return cfg.hermes_ws_token


def install_soul() -> None:
    source = APP_DIR / "SOUL.md"
    target = HERMES_HOME / "SOUL.md"
    if source.exists() and (not target.exists() or target.stat().st_size == 0):
        log("installing default SOUL.md")
        shutil.copyfile(source, target)


def write_handoff(token: str) -> None:
    """Expose only the plugin WS token, never the full adapter config."""
    if not token:
        fail("hermes_ws_token is empty in adapter config")
    HANDOFF_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = HANDOFF_FILE.with_name(f".{HANDOFF_FILE.name}.tmp")
    tmp.write_text(token + "\n", encoding="utf-8")
    tmp.chmod(0o600)
    os.replace(tmp, HANDOFF_FILE)


def wait_for_handoff() -> str:
    for _ in range(60):
        try:
            token = HANDOFF_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            token = ""
        if token:
            return token
        time.sleep(1)
    fail(f"adapter handoff token not available: {HANDOFF_FILE}")


def install_plugin(token: str) -> None:
    if not token:
        fail("hermes_ws_token is empty in adapter config")
    log(f"installing/updating the OneBot plugin in {HERMES_HOME}")
    run(
        ADAPTER_BIN,
        "install",
        "--hermes-dir",
        HERMES_HOME,
        "--adapter-url",
        ADAPTER_URL,
        "--adapter-token",
        token,
    )
    env_path = HERMES_HOME / ".env"
    if env_path.exists():
        env_path.chmod(0o600)

    lines = [
        f"ONEBOT_ADAPTER_URL={shlex.quote(ADAPTER_URL)}",
        f"ONEBOT_ADAPTER_TOKEN={shlex.quote(token)}",
    ]
    group_id = os.environ.get("QQ_GROUP_ID", "").strip()
    if group_id:
        lines.append(f"ONEBOT_HOME_CHANNEL={shlex.quote('group:' + group_id)}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    ENV_FILE.chmod(0o600)

    run(HERMES_BIN, "plugins", "enable", "onebot-platform", "--no-allow-tool-override")


def write_first_run_config() -> None:
    if TOOLSET_MARKER.exists():
        return
    log("writing restricted platform_toolsets.onebot")
    from ruamel.yaml import YAML

    path = HERMES_HOME / "config.yaml"
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

    entries = config.setdefault("plugins", {}).setdefault("entries", {})
    onebot = entries.setdefault("onebot", {})
    onebot["tool_allowlist"] = [
        "onebot_send_message",
        "onebot_send_forward_msg",
        "onebot_forward_single_msg",
        "onebot_upload_file",
        "onebot_set_msg_emoji_like",
        "onebot_poke",
        "onebot_send_like",
        "onebot_mark_msg_as_read",
        "onebot_set_avatar",
        "onebot_set_qq_profile",
        "onebot_set_group_card",
    ]
    onebot["tool_allowlist_prefixes"] = [
        "onebot_get_",
        "onebot_fetch_",
        "onebot_nc_get_",
    ]
    tool_policies = onebot.setdefault("tool_policies", {})
    for tool_name in (
        "onebot_set_avatar",
        "onebot_set_qq_profile",
        "onebot_set_group_card",
    ):
        tool_policies.setdefault(tool_name, {})["permission"] = "everyone"

    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle)

    env_path = HERMES_HOME / ".env"
    existing = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    if "GATEWAY_ALLOW_ALL_USERS=" not in existing:
        with open(env_path, "a", encoding="utf-8") as handle:
            handle.write("\nGATEWAY_ALLOW_ALL_USERS=true\n")
    env_path.chmod(0o600)
    TOOLSET_MARKER.touch()


def run_adapter() -> None:
    ADAPTER_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    init_adapter_config()
    token = sync_onebot_token()
    write_handoff(token)


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


def ensure_self_profile_config() -> None:
    """One-time migration for existing configs that predate self-profile tools."""
    if SELF_PROFILE_MARKER.exists():
        return
    path = HERMES_HOME / "config.yaml"
    if not path.exists():
        return
    from ruamel.yaml import YAML

    yaml = YAML()
    yaml.preserve_quotes = True
    with open(path, encoding="utf-8") as handle:
        config = yaml.load(handle) or {}
    plugins = config.setdefault("plugins", {})
    entries = plugins.setdefault("entries", {}) if isinstance(plugins, dict) else {}
    onebot = entries.setdefault("onebot", {}) if isinstance(entries, dict) else {}
    if not isinstance(onebot, dict):
        onebot = {}
        entries["onebot"] = onebot

    allowlist = onebot.get("tool_allowlist")
    if not isinstance(allowlist, list):
        allowlist = []
        onebot["tool_allowlist"] = allowlist
    for name in (
        "onebot_set_avatar",
        "onebot_set_qq_profile",
        "onebot_set_group_card",
    ):
        if name not in allowlist:
            allowlist.append(name)

    prefixes = onebot.get("tool_allowlist_prefixes")
    if not isinstance(prefixes, list):
        prefixes = []
        onebot["tool_allowlist_prefixes"] = prefixes
    for prefix in ("onebot_get_", "onebot_fetch_", "onebot_nc_get_"):
        if prefix not in prefixes:
            prefixes.append(prefix)

    policies = onebot.get("tool_policies")
    if not isinstance(policies, dict):
        policies = {}
        onebot["tool_policies"] = policies
    for name in (
        "onebot_set_avatar",
        "onebot_set_qq_profile",
        "onebot_set_group_card",
    ):
        policy = policies.get(name)
        if not isinstance(policy, dict):
            policy = {}
            policies[name] = policy
        policy.setdefault("permission", "everyone")

    with open(path, "w", encoding="utf-8") as handle:
        yaml.dump(config, handle)
    SELF_PROFILE_MARKER.touch()


def run_hermes() -> None:
    HERMES_HOME.mkdir(parents=True, exist_ok=True)
    (HERMES_HOME / "plugins").mkdir(parents=True, exist_ok=True)
    install_soul()
    token = wait_for_handoff()
    install_plugin(token)
    write_first_run_config()
    ensure_feature_config()
    ensure_self_profile_config()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--role", choices=("adapter", "hermes"), default="hermes")
    args = parser.parse_args()
    if args.role == "adapter":
        run_adapter()
    else:
        run_hermes()


if __name__ == "__main__":
    main()
