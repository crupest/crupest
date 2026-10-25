from __future__ import annotations

from crupest_qqbot_core.render import MediaResult, render_event


def test_group_prefix_uses_real_seq(group_event) -> None:
    event = group_event()
    assert render_event(event, event.self_id) == "[张三(10001)#8821] 你好"


def test_group_prefix_falls_back_to_message_id(group_event) -> None:
    event = group_event(real_seq=None)
    assert render_event(event, event.self_id) == "[张三(10001)#1234] 你好"


def test_dm_has_no_prefix(group_event) -> None:
    event = group_event(message_type="private", group_id=None, message_id=99)
    assert render_event(event, event.self_id) == "你好"


def test_at_segments(group_event) -> None:
    event = group_event(message=[
        {"type": "at", "data": {"qq": "1950119910"}},
        {"type": "text", "data": {"text": " 看这个"}},
        {"type": "at", "data": {"qq": "12345"}},
    ])
    text = render_event(event, event.self_id)
    assert text == "[张三(10001)#8821] [@self] 看这个[@12345]"


def test_bare_mention_is_kept(group_event) -> None:
    event = group_event(message=[{"type": "at", "data": {"qq": "1950119910"}}])
    assert render_event(event, event.self_id) == "[张三(10001)#8821] [@self]"


def test_command_is_returned_bare(group_event) -> None:
    event = group_event(message=[
        {"type": "at", "data": {"qq": "1950119910"}},
        {"type": "text", "data": {"text": " /reset"}},
    ])
    assert render_event(event, event.self_id) == "/reset"


def test_command_with_leading_whitespace_and_newlines(group_event) -> None:
    event = group_event(message=[
        {"type": "text", "data": {"text": "   "}},
        {"type": "at", "data": {"qq": "1950119910"}},
        {"type": "text", "data": {"text": "\n/model gpt"}},
    ])
    assert render_event(event, event.self_id) == "/model gpt"


def test_typed_at_marker_is_not_a_command(group_event) -> None:
    event = group_event(message=[{"type": "text", "data": {"text": "[@self] /reset"}}])
    rendered = render_event(event, event.self_id)
    assert rendered == "[张三(10001)#8821] [@self] /reset"


def test_empty_message_returns_none(group_event) -> None:
    assert render_event(group_event(message=[]), 1950119910) is None
    assert render_event(group_event(message=[{"type": "text", "data": {"text": "   "}}]), 1950119910) is None


def test_text_is_not_stripped(group_event) -> None:
    event = group_event(message=[{"type": "text", "data": {"text": "  padded  "}}])
    assert render_event(event, event.self_id) == "[张三(10001)#8821]   padded  "


def test_internal_event_skips_prefix(group_event) -> None:
    event = group_event(
        message=[{"type": "text", "data": {"text": "[系统] 用户 张三(10001) 戳了戳你"}}],
        adapter={"internal": True, "origin": "poke"},
    )
    assert render_event(event, event.self_id) == "[系统] 用户 张三(10001) 戳了戳你"


def test_media_placeholder_states(group_event) -> None:
    event = group_event(message=[
        {"type": "image", "data": {"file": "a.jpg"}},
        {"type": "image", "data": {"file": "b.jpg"}},
        {"type": "image", "data": {"file": "c.jpg"}},
    ])
    text = render_event(event, event.self_id, [
        MediaResult(path="/cache/a.jpg"),
        MediaResult(failed=True),
        MediaResult(),
    ])
    assert text == (
        '[张三(10001)#8821] [image1 id="a.jpg" cache="/cache/a.jpg"]'
        '[image2 id="b.jpg" cache="failed"]'
        '[image3 id="c.jpg" cache="none"]'
    )


def test_missing_media_results_default_to_none(group_event) -> None:
    event = group_event(message=[{"type": "image", "data": {"file": "a.jpg"}}])
    assert render_event(event, event.self_id) == '[张三(10001)#8821] [image1 id="a.jpg" cache="none"]'


def test_file_placeholder_has_name_and_id(group_event) -> None:
    event = group_event(message=[{"type": "file", "data": {"file_id": "fid", "file_name": "报告 v2.pdf"}}])
    text = render_event(event, event.self_id)
    assert text == '[张三(10001)#8821] [file1 name="报告 v2.pdf" id="fid" cache="none"]'


def test_quotes_are_escaped(group_event) -> None:
    event = group_event(message=[{"type": "file", "data": {"file_id": 'a"b', "file_name": "x"}}])
    text = render_event(event, event.self_id) or ""
    assert 'id="a\\"b"' in text


def test_media_numbering_is_per_kind(group_event) -> None:
    event = group_event(message=[
        {"type": "image", "data": {"file": "a.jpg"}},
        {"type": "record", "data": {"file": "v.amr"}},
        {"type": "image", "data": {"file": "b.jpg"}},
    ])
    text = render_event(event, event.self_id) or ""
    assert "[image1 " in text
    assert "[voice1 " in text
    assert "[image2 " in text


def test_forward_placeholder(group_event) -> None:
    event = group_event(message=[{"type": "forward", "data": {"id": "ff"}}])
    assert render_event(event, event.self_id) == '[张三(10001)#8821] [forward id="ff"]'


def test_reply_segment_is_not_rendered(group_event) -> None:
    event = group_event(message=[
        {"type": "reply", "data": {"id": "77"}},
        {"type": "text", "data": {"text": "好的"}},
    ])
    assert render_event(event, event.self_id) == "[张三(10001)#8821] 好的"
