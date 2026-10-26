from __future__ import annotations

import pytest
from crupest_chatbot_core import errors


def test_schema_error_response() -> None:
    exc = errors.SchemaError("json", raw_excerpt="{")
    response = exc.to_response("e1")
    assert response["status"] == "failed"
    assert response["retcode"] == errors.RETCODE_BAD_PARAM
    assert response["reason"] == errors.REASON_SCHEMA
    assert response["echo"] == "e1"


def test_policy_error_response() -> None:
    exc = errors.PolicyError("set_group_ban", errors.REASON_POLICY_DENIED)
    response = exc.to_response()
    assert response["retcode"] == errors.RETCODE_POLICY
    assert response["reason"] == errors.REASON_POLICY_DENIED
    assert "set_group_ban" in response["wording"]


def test_transport_error_response() -> None:
    response = errors.TransportError().to_response()
    assert response["retcode"] == errors.RETCODE_TRANSPORT
    assert response["reason"] == errors.REASON_NOT_CONNECTED


def test_timeout_error_response() -> None:
    response = errors.UpstreamTimeout("send_group_msg", 60).to_response()
    assert response["retcode"] == errors.RETCODE_UPSTREAM_TIMEOUT
    assert response["reason"] == errors.REASON_NAPCAT_TIMEOUT
    assert "60" in response["wording"]


def test_config_error_lists_every_problem() -> None:
    exc = errors.ConfigError(["a", "b"])
    assert exc.errors == ["a", "b"]
    message = str(exc)
    assert "- a" in message
    assert "- b" in message


def test_retcodes_are_distinct() -> None:
    codes = {
        errors.RETCODE_OK,
        errors.RETCODE_BAD_PARAM,
        errors.RETCODE_UNKNOWN_ACTION,
        errors.RETCODE_POLICY,
        errors.RETCODE_UPSTREAM_TIMEOUT,
        errors.RETCODE_TRANSPORT,
    }
    assert len(codes) == 6


def test_exception_is_catchable_as_base() -> None:
    with pytest.raises(errors.ChatbotError):
        raise errors.PolicyError("x", errors.REASON_TARGET_MISMATCH)
