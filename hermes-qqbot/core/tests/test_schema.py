from __future__ import annotations

import json

import pytest
from crupest_qqbot_core.errors import SchemaError
from crupest_qqbot_core.schema import ApiResponse, Event, parse_frame


def test_parse_message_event() -> None:
    raw = json.dumps({
        "time": 1,
        "self_id": 42,
        "post_type": "message",
        "message_type": "group",
        "group_id": 7,
        "user_id": 8,
        "message": [{"type": "text", "data": {"text": "hi"}}],
        "real_seq": 3,
    })
    frame = parse_frame(raw)
    assert isinstance(frame, Event)
    assert frame.message_type == "group"
    assert frame.message[0].type == "text"
    assert frame.real_seq == 3


def test_parse_string_message_is_kept() -> None:
    frame = parse_frame(json.dumps({"post_type": "message", "self_id": 1, "message": "plain"}))
    assert isinstance(frame, Event)
    assert frame.message == "plain"


def test_parse_api_response() -> None:
    frame = parse_frame(json.dumps({"status": "ok", "retcode": 0, "data": {"message_id": 5}, "echo": "e1"}))
    assert isinstance(frame, ApiResponse)
    assert frame.echo == "e1"
    assert frame.retcode == 0


def test_unknown_frame() -> None:
    with pytest.raises(SchemaError) as excinfo:
        parse_frame(json.dumps({"hello": "world"}))
    assert excinfo.value.kind == "unknown_frame"


def test_bad_json() -> None:
    with pytest.raises(SchemaError) as excinfo:
        parse_frame("{not json")
    assert excinfo.value.kind == "json"
    assert excinfo.value.raw_excerpt


def test_non_object_frame() -> None:
    with pytest.raises(SchemaError) as excinfo:
        parse_frame("[1, 2]")
    assert excinfo.value.kind == "shape"


def test_wrong_field_type_reports_path() -> None:
    with pytest.raises(SchemaError) as excinfo:
        parse_frame(json.dumps({"post_type": "message", "self_id": 1, "message": 5}))
    assert excinfo.value.kind == "shape"
    assert "message" in excinfo.value.path


def test_unknown_fields_are_preserved() -> None:
    frame = parse_frame(json.dumps({"post_type": "message", "self_id": 1, "brand_new": 9}))
    assert isinstance(frame, Event)
    assert frame.model_extra is not None
    assert frame.model_extra["brand_new"] == 9
