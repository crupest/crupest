from __future__ import annotations

from adapter_helpers import make_event
from crupest_chatbot_adapter.seq import SeqMap


def test_record_and_resolve() -> None:
    seq = SeqMap()
    seq.record(8821, 1234)
    assert seq.resolve(8821) == "1234"
    assert seq.resolve("8821") == "1234"


def test_resolve_miss() -> None:
    assert SeqMap().resolve(1) is None


def test_record_event() -> None:
    seq = SeqMap()
    seq.record_event(make_event(real_seq=7, message_id=99))
    assert seq.resolve(7) == "99"


def test_record_ignores_empty_values() -> None:
    seq = SeqMap()
    seq.record(None, 1)
    seq.record(1, None)
    assert len(seq) == 0


def test_capacity_is_fifo() -> None:
    seq = SeqMap(capacity=2)
    seq.record(1, 11)
    seq.record(2, 22)
    seq.record(3, 33)
    assert seq.resolve(1) is None
    assert seq.resolve(2) == "22"
    assert seq.resolve(3) == "33"


def test_apply_translates_known_action() -> None:
    seq = SeqMap()
    seq.record(8821, 1234)
    prepared = seq.apply("set_msg_emoji_like", {"real_seq": 8821, "emoji_id": "124"})
    assert prepared == {"message_id": "1234", "emoji_id": "124"}


def test_apply_passes_through_on_miss() -> None:
    prepared = SeqMap().apply("set_msg_emoji_like", {"real_seq": 5, "emoji_id": "124"})
    assert prepared == {"message_id": 5, "emoji_id": "124"}


def test_apply_leaves_other_actions_alone() -> None:
    seq = SeqMap()
    prepared = seq.apply("send_group_msg", {"real_seq": 1, "message": []})
    assert prepared == {"real_seq": 1, "message": []}


def test_apply_translates_voice_transcript() -> None:
    seq = SeqMap()
    seq.record(3, 33)
    assert seq.apply("fetch_ptt_text", {"real_seq": 3}) == {"message_id": "33"}


def test_apply_without_real_seq() -> None:
    prepared = SeqMap().apply("mark_msg_as_read", {"message_id": 9})
    assert prepared == {"message_id": 9}


def test_known_ids_include_dm_messages_without_real_seq() -> None:
    seq = SeqMap()
    seq.record_event(make_event(message_type="private", group_id=None, real_seq=None, message_id=77))
    assert seq.known(77) is True
    assert seq.known("77") is True
    assert seq.known(78) is False


def test_known_ids_are_fifo_bounded() -> None:
    seq = SeqMap(capacity=2)
    for message_id in (1, 2, 3):
        seq.record_event(make_event(message_id=message_id))
    assert seq.known(1) is False
    assert seq.known(2) is True
    assert seq.known(3) is True
