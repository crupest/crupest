from __future__ import annotations

import pytest
from adapter_helpers import make_event
from crupest_chatbot_adapter import policy
from crupest_chatbot_core.config import NotifyConfig
from crupest_chatbot_core.errors import REASON_BAD_PARAM, REASON_POLICY_DENIED, REASON_TARGET_MISMATCH, PolicyError

GROUP = policy.Binding(group_id=123456)
DM = policy.Binding(user_id=10001)
NOTIFY_ON = NotifyConfig(poke=True, member_change=True)


class FakeWindow:
    def __init__(self, active: bool) -> None:
        self._active = active

    def active(self) -> bool:
        return self._active


def decision(event, binding=GROUP, window_active=False, notify=None):
    return policy.decide_event(event, binding, FakeWindow(window_active), notify or NotifyConfig())


@pytest.mark.parametrize(
    ("event", "expected"),
    [
        (make_event(group_id=999), (False, "other_chat")),
        (make_event(group_id=123456), (True, "mention")),
        (make_event(message=[{"type": "text", "data": {"text": "hi"}}]), (False, "inactive")),
        (make_event(user_id=1950119910), (False, "self")),
        (make_event(message=[]), (False, "empty")),
    ],
)
def test_group_gate(event, expected) -> None:
    result = decision(event)
    assert (result.forward, result.reason) == expected


def test_group_window_forward() -> None:
    event = make_event(message=[{"type": "text", "data": {"text": "hi"}}])
    result = decision(event, window_active=True)
    assert (result.forward, result.reason) == (True, "window")


def test_group_mention_wins_over_window() -> None:
    event = make_event()
    result = decision(event, window_active=True)
    assert result.reason == "mention"


def test_dm_gate() -> None:
    inside = make_event(message_type="private", group_id=None, user_id=10001)
    outside = make_event(message_type="private", group_id=None, user_id=2)
    assert decision(inside, binding=DM).forward is True
    assert decision(outside, binding=DM) == policy.Decision(False, "other_chat")


def test_group_binding_ignores_dm() -> None:
    event = make_event(message_type="private", group_id=None)
    assert decision(event).reason == "other_chat"


def test_unsupported_post_type() -> None:
    event = make_event(post_type="meta_event", notice_type=None)
    assert decision(event) == policy.Decision(False, "unsupported")


def test_notice_requires_binding_and_switch() -> None:
    poke = make_event(post_type="notice", notice_type="notify", sub_type="poke", target_id=1950119910)
    assert decision(poke, notify=NOTIFY_ON).forward is True
    assert decision(poke).reason == "notice_ignored"
    assert decision(poke, binding=DM, notify=NOTIFY_ON).reason == "other_chat"


def test_notice_other_group() -> None:
    join = make_event(post_type="notice", notice_type="group_increase", group_id=999)
    assert decision(join, notify=NOTIFY_ON).reason == "other_chat"


def test_allowlist_rejects_unknown_action() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_group_ban", {"group_id": 123456}, GROUP)
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_target_is_filled_when_missing() -> None:
    prepared = policy.authorize("send_group_msg", {"message": []}, GROUP)
    assert prepared["group_id"] == 123456


def test_target_mismatch_is_rejected() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_msg", {"group_id": 999, "message": []}, GROUP)
    assert excinfo.value.reason == REASON_TARGET_MISMATCH


def test_target_equal_as_string_is_accepted() -> None:
    prepared = policy.authorize("send_group_msg", {"group_id": "123456", "message": []}, GROUP)
    assert prepared["group_id"] == "123456"
    assert "group_id" in prepared


def test_dm_binding_rejects_group_send() -> None:
    with pytest.raises(PolicyError):
        policy.authorize("send_group_msg", {"message": []}, DM)


@pytest.mark.parametrize(
    ("action", "params"),
    [
        ("send_group_msg", {"message": "[CQ:at,qq=all] hi"}),
        ("send_msg", {"message_type": "group", "message": "[CQ:at,qq=all] hi"}),
        ("send_private_msg", {"message": "[CQ:at,qq=all] hi"}),
    ],
)
def test_cq_string_message_is_rejected(action, params) -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(action, params, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_segment_array_is_accepted() -> None:
    prepared = policy.authorize(
        "send_group_msg", {"message": [{"type": "text", "data": {"text": "hi"}}]}, GROUP,
    )
    assert prepared["group_id"] == 123456


def test_send_msg_dispatch() -> None:
    group = policy.authorize("send_msg", {"message_type": "group", "message": []}, GROUP)
    assert group["group_id"] == 123456
    dm = policy.authorize("send_msg", {"message_type": "private", "message": []}, DM)
    assert dm["user_id"] == 10001
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_msg", {"message_type": "channel"}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_get_actions_without_target_are_allowed() -> None:
    assert policy.authorize("get_login_info", {}, GROUP) == {}
    assert policy.authorize("get_file", {"file_id": "x"}, GROUP) == {"file_id": "x"}


def test_group_scoped_reads_are_pinned() -> None:
    prepared = policy.authorize("get_group_msg_history", {"count": 5}, GROUP)
    assert prepared["group_id"] == 123456


def test_params_are_not_mutated() -> None:
    original = {"message": []}
    policy.authorize("send_group_msg", original, GROUP)
    assert original == {"message": []}


def test_set_group_card_fills_self() -> None:
    prepared = policy.authorize("set_group_card", {"card": "新名片"}, GROUP, self_id="1950119910")
    assert prepared["group_id"] == 123456
    assert prepared["user_id"] == "1950119910"
    assert prepared["card"] == "新名片"


def test_set_group_card_rejects_other_user() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_group_card", {"card": "x", "user_id": "1"}, GROUP, self_id="1950119910")
    assert excinfo.value.reason == REASON_TARGET_MISMATCH


def test_set_group_card_needs_known_self_id() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_group_card", {"card": "x"}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_profile_actions_have_no_target() -> None:
    assert policy.authorize("set_qq_profile", {"nickname": "派蒙"}, GROUP) == {"nickname": "派蒙"}
    assert policy.authorize("set_qq_avatar", {"file": "https://x/a.png"}, GROUP) == {"file": "https://x/a.png"}


def test_react_accepts_real_seq_only() -> None:
    params = {"real_seq": 7, "emoji_id": "124"}
    assert policy.authorize("set_msg_emoji_like", params, GROUP) == params


def test_react_rejects_message_id_bypass() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_msg_emoji_like", {"message_id": 7, "emoji_id": "124"}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_react_rejects_remove_flag() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_msg_emoji_like", {"real_seq": 7, "emoji_id": "124", "set": False}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_profile_rejects_extra_fields() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_qq_profile", {"nickname": "x", "sex": 1}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_avatar_rejects_extra_fields() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("set_qq_avatar", {"file": "https://x/a.png", "avatar": "x"}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_stranger_info_is_not_chat_bound() -> None:
    # Usable from a group instance too: it only takes a user_id and reads public info.
    assert policy.authorize("get_stranger_info", {"user_id": 42}, GROUP) == {"user_id": 42}
    assert policy.authorize("get_stranger_info", {"user_id": 42}, DM) == {"user_id": 42}


def test_friend_history_pins_dm_target() -> None:
    prepared = policy.authorize("get_friend_msg_history", {"count": 10}, DM)
    assert prepared["user_id"] == 10001
    with pytest.raises(PolicyError):
        policy.authorize("get_friend_msg_history", {"count": 10}, GROUP)


def test_group_file_listing_pins_group() -> None:
    assert policy.authorize("get_group_root_files", {"file_count": 50}, GROUP)["group_id"] == 123456
    prepared = policy.authorize("get_group_files_by_folder", {"folder_id": "f", "file_count": 10}, GROUP)
    assert prepared["group_id"] == 123456


def test_group_file_reads_pin_group() -> None:
    assert policy.authorize("get_group_file_url", {"file_id": "f"}, GROUP)["group_id"] == 123456
    assert policy.authorize("get_group_file_system_info", {}, GROUP)["group_id"] == 123456


def test_voice_transcript_param_subset() -> None:
    assert policy.authorize("fetch_ptt_text", {"real_seq": 3}, GROUP) == {"real_seq": 3}
    assert policy.authorize("fetch_ptt_text", {"message_id": "9"}, GROUP) == {"message_id": "9"}
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("fetch_ptt_text", {"real_seq": 3, "extra": 1}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_forward_read_has_no_target() -> None:
    assert policy.authorize("get_forward_msg", {"id": "abc"}, GROUP) == {"id": "abc"}
