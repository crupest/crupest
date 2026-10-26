from __future__ import annotations

from crupest_chatbot_core import segments


def test_constructors() -> None:
    assert segments.text("hi") == {"type": "text", "data": {"text": "hi"}}
    assert segments.at(42) == {"type": "at", "data": {"qq": "42"}}
    assert segments.reply(7) == {"type": "reply", "data": {"id": "7"}}
    assert segments.image("a.jpg", "http://x/a.jpg")["data"] == {"file": "a.jpg", "url": "http://x/a.jpg"}
    assert segments.file("fid", "doc.pdf")["data"]["file_id"] == "fid"


def test_event_segments_array(group_event) -> None:
    event = group_event(message=[{"type": "text", "data": {"text": "hi"}}])
    assert segments.event_segments(event) == [{"type": "text", "data": {"text": "hi"}}]


def test_event_segments_string_is_wrapped(group_event) -> None:
    event = group_event(message="hi")
    assert segments.event_segments(event) == [{"type": "text", "data": {"text": "hi"}}]


def test_event_segments_missing(group_event) -> None:
    assert segments.event_segments(group_event(message=None)) == []


def test_mentions_self(group_event) -> None:
    event = group_event(message=[{"type": "at", "data": {"qq": "1950119910"}}])
    assert segments.mentions_self(segments.event_segments(event), event.self_id)


def test_mentions_self_ignores_all_and_others(group_event) -> None:
    event = group_event(message=[{"type": "at", "data": {"qq": "all"}}, {"type": "at", "data": {"qq": "1"}}])
    assert not segments.mentions_self(segments.event_segments(event), event.self_id)


def test_has_content() -> None:
    assert segments.has_content([{"type": "at", "data": {"qq": "1"}}])
    assert not segments.has_content([{"type": "text", "data": {"text": "  \n "}}])
    assert not segments.has_content([])
    assert segments.has_content([{"type": "text", "data": {"text": "x"}}])


def test_media_id_prefers_file_id_for_files() -> None:
    assert segments.media_id({"type": "file", "data": {"file_id": "fid", "file": "name"}}) == "fid"
    assert segments.media_id({"type": "file", "data": {"file": "name"}}) == "name"
    assert segments.media_id({"type": "image", "data": {"file": "abc.jpg"}}) == "abc.jpg"
    assert segments.media_id({"type": "image", "data": {}}) == ""


def test_format_sender_prefix() -> None:
    assert segments.format_sender_prefix("张三", 10001, 8821) == "[张三(10001)#8821]"
    assert segments.format_sender_prefix("张三", 10001, "") == "[张三(10001)]"
    assert segments.format_sender_prefix("", "", "") == "[]"


def test_extract_reply_and_forward() -> None:
    message = [
        {"type": "reply", "data": {"id": "77"}},
        {"type": "forward", "data": {"id": "ff"}},
    ]
    assert segments.extract_reply_id(message) == "77"
    assert segments.extract_forward_id(message) == "ff"
    assert segments.extract_reply_id([{"type": "text", "data": {"text": "x"}}]) is None


def test_command_regex_positive() -> None:
    match = segments.COMMAND_RE.match("[@self] /reset")
    assert match is not None
    assert match.group(1) == "/reset"


def test_command_regex_allows_whitespace_and_newlines() -> None:
    assert segments.COMMAND_RE.match("   [@self]   /model gpt")
    assert segments.COMMAND_RE.match("[@self]\n/reset")


def test_command_regex_negative() -> None:
    assert segments.COMMAND_RE.match("你好 /reset") is None
    assert segments.COMMAND_RE.match("/reset") is None
    assert segments.COMMAND_RE.match("[@12345] /reset") is None
