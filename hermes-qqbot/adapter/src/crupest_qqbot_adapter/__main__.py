"""Adapter entry point."""
from __future__ import annotations

import argparse
import asyncio
import shutil
import sys
from pathlib import Path

from crupest_qqbot_core.config import load_config, load_secrets
from crupest_qqbot_core.errors import ConfigError
from crupest_qqbot_core.logging import setup_logging

from .app import AdapterService

DEFAULT_CONFIG = Path("/opt/qqbot-defaults/config.example.toml")


def ensure_config(path: Path) -> None:
    """Create the shared config from the baked example when it is missing."""
    if path.exists():
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DEFAULT_CONFIG, path)
        print(f"[adapter] created default config at {path}", file=sys.stderr)
    except OSError as exc:
        print(f"[adapter] could not create {path} ({exc}); using built-in defaults", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="crupest-qqbot-adapter")
    parser.add_argument("--config", default="/opt/qqbot/config.toml", help="shared config TOML")
    args = parser.parse_args(argv)

    config_path = Path(args.config)
    ensure_config(config_path)

    try:
        config = load_config(config_path)
        secrets = load_secrets()
    except ConfigError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    setup_logging(config.logging.level)
    asyncio.run(AdapterService(config, secrets).run())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
