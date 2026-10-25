"""Error taxonomy shared by the adapter and the plugin.

Every failure that crosses the wire becomes a *failed response frame* carrying a
retcode, a machine-readable ``reason`` and a human ``wording``.  Nothing is
silently downgraded: the caller (Hermes) decides what to do next.
"""
from __future__ import annotations

from typing import Any

RETCODE_OK = 0
RETCODE_BAD_PARAM = 100
RETCODE_UNKNOWN_ACTION = 103
RETCODE_POLICY = 200
RETCODE_UPSTREAM_TIMEOUT = 400
RETCODE_TRANSPORT = 500

REASON_POLICY_DENIED = "policy_denied"
REASON_TARGET_MISMATCH = "target_mismatch"
REASON_BAD_PARAM = "bad_param"
REASON_UNKNOWN_ACTION = "unknown_action"
REASON_NOT_CONNECTED = "not_connected"
REASON_NAPCAT_TIMEOUT = "napcat_timeout"
REASON_NAPCAT_FAILED = "napcat_failed"
REASON_MEDIA_UNAVAILABLE = "media_unavailable"
REASON_SCHEMA = "schema"


class QQBotError(Exception):
    """Base class for every error that maps onto a failed response frame."""

    retcode = RETCODE_TRANSPORT
    reason = "error"

    def __init__(self, message: str = "") -> None:
        self.message = message or self.reason
        super().__init__(self.message)

    def to_response(self, echo: str = "") -> dict[str, Any]:
        return {
            "status": "failed",
            "retcode": self.retcode,
            "reason": self.reason,
            "wording": self.message,
            "echo": echo,
        }


class SchemaError(QQBotError):
    """A frame did not match the expected shape."""

    retcode = RETCODE_BAD_PARAM
    reason = REASON_SCHEMA

    def __init__(self, kind: str, path: str = "", raw_excerpt: str = "") -> None:
        self.kind = kind
        self.path = path
        self.raw_excerpt = raw_excerpt
        detail = f"schema error ({kind})" + (f" at {path}" if path else "")
        super().__init__(detail)


class PolicyError(QQBotError):
    """An action or its target was refused by the adapter policy."""

    retcode = RETCODE_POLICY

    def __init__(self, action: str, reason: str, message: str = "") -> None:
        self.action = action
        self.reason = reason
        super().__init__(message or f"{action}: {reason}")


class TransportError(QQBotError):
    """The upstream connection is unusable."""

    retcode = RETCODE_TRANSPORT
    reason = REASON_NOT_CONNECTED


class UpstreamTimeout(QQBotError):
    """NapCat accepted the request but did not answer in time."""

    retcode = RETCODE_UPSTREAM_TIMEOUT
    reason = REASON_NAPCAT_TIMEOUT

    def __init__(self, action: str, seconds: float) -> None:
        self.action = action
        self.seconds = seconds
        super().__init__(f"{action}: 上游 {seconds:g}s 内没有响应")


class ConfigError(QQBotError):
    """Startup configuration is invalid (all problems are collected)."""

    retcode = RETCODE_BAD_PARAM
    reason = "config"

    def __init__(self, errors: list[str]) -> None:
        self.errors = list(errors)
        super().__init__("配置错误:\n" + "\n".join(f"- {e}" for e in self.errors))
