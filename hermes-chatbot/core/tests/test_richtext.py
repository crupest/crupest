from __future__ import annotations

import pytest
from crupest_chatbot_core import richtext
from crupest_chatbot_core.config import FeaturesConfig


def test_builds_all_segment_types() -> None:
    items = [
        {"type": "reply", "seq": 7},
        {"type": "text", "text": "你好 "},
        {"type": "at", "qq": "10001"},
        {"type": "face", "name": "微笑"},
        {"type": "dice"},
        {"type": "rps"},
    ]
    assert richtext.build(items, resolve_seq=lambda seq: "42" if seq == 7 else None) == [
        {"type": "reply", "data": {"id": "42"}},
        {"type": "text", "data": {"text": "你好 "}},
        {"type": "at", "data": {"qq": "10001"}},
        {"type": "face", "data": {"id": "14"}},
        {"type": "dice", "data": {}},
        {"type": "rps", "data": {}},
    ]


def test_empty_items_is_rejected() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([])


def test_too_many_segments_is_rejected() -> None:
    items = [{"type": "text", "text": "x"}] * (richtext.MAX_SEGMENTS + 1)
    with pytest.raises(richtext.RichTextError):
        richtext.build(items)


def test_unknown_type_is_rejected() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([{"type": "image", "file": "/x"}])


def test_unknown_face_is_rejected() -> None:
    with pytest.raises(richtext.RichTextError) as excinfo:
        richtext.build([{"type": "face", "name": "没有这个"}])
    assert excinfo.value.index == 0


def test_at_self_is_allowed() -> None:
    assert richtext.build([{"type": "at", "qq": "42"}]) == [
        {"type": "at", "data": {"qq": "42"}},
    ]


def test_at_all_is_allowed_by_default() -> None:
    assert richtext.build([{"type": "at", "qq": "all"}]) == [
        {"type": "at", "data": {"qq": "all"}},
    ]


def test_at_all_can_be_disabled() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([{"type": "at", "qq": "all"}], FeaturesConfig(at_all=False))


def test_at_in_dm_is_rejected() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([{"type": "at", "qq": "42"}], group=False)


def test_text_limit_is_enforced() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([{"type": "text", "text": "x" * 11}], max_text=10)


def test_reply_requires_known_seq() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build([{"type": "reply", "seq": 7}], resolve_seq=lambda seq: None)


def test_reply_must_be_first() -> None:
    with pytest.raises(richtext.RichTextError):
        richtext.build(
            [{"type": "text", "text": "x"}, {"type": "reply", "seq": 7}],
            resolve_seq=lambda seq: "42",
        )


def test_disabled_features_are_rejected() -> None:
    for item, features in [
        ({"type": "at", "qq": "42"}, FeaturesConfig(at=False)),
        ({"type": "face", "name": "微笑"}, FeaturesConfig(face=False)),
        ({"type": "dice"}, FeaturesConfig(dice=False)),
        ({"type": "rps"}, FeaturesConfig(rps=False)),
    ]:
        with pytest.raises(richtext.RichTextError):
            richtext.build([item], features)
