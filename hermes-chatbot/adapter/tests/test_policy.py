from __future__ import annotations

import pytest
from adapter_helpers import make_event
from crupest_chatbot_adapter import policy
from crupest_chatbot_core.config import FeaturesConfig, LimitsConfig, NotifyConfig
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


def test_at_segment_is_kept() -> None:
    message = [{"type": "at", "data": {"qq": "42"}}, {"type": "text", "data": {"text": " hi"}}]
    prepared = policy.authorize("send_group_msg", {"message": message}, GROUP)
    assert prepared["message"] == message


def test_at_self_is_allowed() -> None:
    message = [{"type": "at", "data": {"qq": "1950119910"}}]
    prepared = policy.authorize(
        "send_group_msg", {"message": message}, GROUP,
        context=policy.Context(self_id="1950119910"),
    )
    assert prepared["message"] == message


def test_at_all_is_allowed_by_default() -> None:
    message = [{"type": "at", "data": {"qq": "all"}}]
    prepared = policy.authorize("send_group_msg", {"message": message}, GROUP)
    assert prepared["message"] == message


def test_at_all_can_be_disabled() -> None:
    message = [{"type": "at", "data": {"qq": "all"}}]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_group_msg", {"message": message}, GROUP,
            features=FeaturesConfig(at_all=False),
        )
    assert excinfo.value.reason == REASON_POLICY_DENIED


@pytest.mark.parametrize(
    ("flag", "segment"),
    [
        ("at", {"type": "at", "data": {"qq": "42"}}),
        ("face", {"type": "face", "data": {"id": "14"}}),
        ("dice", {"type": "dice", "data": {}}),
        ("rps", {"type": "rps", "data": {}}),
    ],
)
def test_disabled_segment_types_are_rejected_by_adapter(flag: str, segment: dict) -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_group_msg", {"message": [segment]}, GROUP,
            features=FeaturesConfig(**{flag: False}),
        )
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_at_in_dm_is_rejected() -> None:
    message = [{"type": "at", "data": {"qq": "1"}}]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_private_msg", {"message": message}, DM)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_at_non_numeric_is_rejected() -> None:
    message = [{"type": "at", "data": {"qq": "abc"}}]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_msg", {"message": message}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_face_segment_valid_and_invalid() -> None:
    assert policy.authorize(
        "send_group_msg", {"message": [{"type": "face", "data": {"id": "14"}}]}, GROUP,
    )["message"] == [{"type": "face", "data": {"id": "14"}}]
    with pytest.raises(PolicyError):
        policy.authorize(
            "send_group_msg", {"message": [{"type": "face", "data": {"id": "x"}}]}, GROUP,
        )


def test_dice_and_rps_segments() -> None:
    message = [{"type": "dice", "data": {}}, {"type": "rps", "data": {}}]
    assert policy.authorize("send_group_msg", {"message": message}, GROUP)["message"] == message
    with pytest.raises(PolicyError):
        policy.authorize(
            "send_group_msg", {"message": [{"type": "dice", "data": {"result": 3}}]}, GROUP,
        )


def test_unknown_segment_type_is_rejected() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_group_msg",
            {"message": [{"type": "json", "data": {"data": "{}"}}]},
            GROUP,
        )
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_media_outside_share_dir_is_rejected() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_group_msg",
            {"message": [{"type": "file", "data": {"file": "/etc/passwd"}}]},
            GROUP,
        )
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_media_url_is_rejected() -> None:
    message = [{"type": "image", "data": {"file": "https://example.com/a.jpg"}}]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_msg", {"message": message}, GROUP)
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_unknown_media_scheme_is_rejected() -> None:
    message = [{"type": "image", "data": {"file": "ftp://example.com/a.jpg"}}]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_msg", {"message": message}, GROUP)
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_media_inside_share_dir_is_allowed() -> None:
    message = [{"type": "image", "data": {"file": "/opt/data/share/media/a.jpg"}}]
    assert policy.authorize("send_group_msg", {"message": message}, GROUP)["message"] == message


def test_segment_count_is_capped() -> None:
    limits = LimitsConfig(max_segments_per_message=2)
    message = [{"type": "text", "data": {"text": str(index)}} for index in range(3)]
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_msg", {"message": message}, GROUP, limits=limits)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_poke_can_target_any_qq() -> None:
    prepared = policy.authorize("send_poke", {"user_id": "20002"}, GROUP)
    assert prepared == {"user_id": "20002", "group_id": 123456}


def test_poke_rejects_non_numeric_target() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_poke", {"user_id": "not-a-qq"}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_poke_respects_feature_flag() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_poke", {"user_id": "10001"}, GROUP,
            features=FeaturesConfig(poke=False),
        )
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_poke_in_dm_is_pinned_to_binding() -> None:
    assert policy.authorize("send_poke", {}, DM) == {"user_id": 10001}
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_poke", {"group_id": 123456}, DM)
    assert excinfo.value.reason == REASON_TARGET_MISMATCH


def test_forward_accepts_node_ids_only() -> None:
    messages = [
        {"type": "node", "data": {"id": "4512"}},
        {"type": "node", "data": {"id": "4513"}},
    ]
    prepared = policy.authorize("send_group_forward_msg", {"messages": messages}, GROUP)
    assert prepared["group_id"] == 123456
    assert prepared["messages"] == messages


@pytest.mark.parametrize(
    "node",
    [
        {"type": "node", "data": {"id": "4512", "content": []}},
        {"type": "node", "data": {"user_id": "1", "nickname": "x", "content": []}},
        {"type": "node", "data": {"id": "4512"}, "extra": 1},
        {"type": "text", "data": {"text": "x"}},
    ],
)
def test_forward_rejects_synthesised_nodes(node) -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize("send_group_forward_msg", {"messages": [node]}, GROUP)
    assert excinfo.value.reason == REASON_BAD_PARAM


def test_forward_node_count_is_capped() -> None:
    limits = LimitsConfig(forward_max_nodes=2)
    messages = [{"type": "node", "data": {"id": str(index)}} for index in range(3)]
    with pytest.raises(PolicyError):
        policy.authorize("send_group_forward_msg", {"messages": messages}, GROUP, limits=limits)


def test_forward_respects_feature_flag() -> None:
    with pytest.raises(PolicyError) as excinfo:
        policy.authorize(
            "send_group_forward_msg",
            {"messages": [{"type": "node", "data": {"id": "1"}}]},
            GROUP,
            features=FeaturesConfig(forward=False),
        )
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_upload_path_is_confined_to_share_dir(tmp_path) -> None:
    root = tmp_path / "share"
    root.mkdir()
    inside = root / "a.txt"
    inside.write_text("x", encoding="utf-8")
    outside = tmp_path / "b.txt"
    outside.write_text("x", encoding="utf-8")
    limits = LimitsConfig(upload_dir=str(root))

    prepared = {"file": str(inside), "name": "a.txt"}
    policy.check_upload("upload_group_file", prepared, limits)
    assert prepared["file"] == str(inside)

    with pytest.raises(PolicyError) as excinfo:
        policy.check_upload("upload_group_file", {"file": str(outside), "name": "b.txt"}, limits)
    assert excinfo.value.reason == REASON_POLICY_DENIED


def test_upload_relative_path_is_resolved_against_share_dir(tmp_path) -> None:
    root = tmp_path / "share"
    root.mkdir()
    (root / "a.txt").write_text("x", encoding="utf-8")
    limits = LimitsConfig(upload_dir=str(root))
    prepared = {"file": "a.txt"}
    policy.check_upload("upload_group_file", prepared, limits)
    assert prepared["file"] == str((root / "a.txt").resolve())


def test_upload_size_is_capped(tmp_path) -> None:
    target = tmp_path / "big.bin"
    target.write_bytes(b"x" * 10)
    limits = LimitsConfig(upload_dir=str(tmp_path), upload_max_bytes=5)
    with pytest.raises(PolicyError):
        policy.check_upload("upload_group_file", {"file": str(target), "name": "big.bin"}, limits)


def test_upload_name_cannot_escape(tmp_path) -> None:
    target = tmp_path / "a.txt"
    target.write_text("x", encoding="utf-8")
    limits = LimitsConfig(upload_dir=str(tmp_path))
    with pytest.raises(PolicyError):
        policy.check_upload("upload_group_file", {"file": str(target), "name": "../x"}, limits)
