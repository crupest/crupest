from __future__ import annotations

from core_helpers import SELF_ID, make_event
from crupest_qqbot_core.notice import render_notice


def _notice(**overrides):
    payload = {
        "post_type": "notice",
        "group_id": 123456,
        "user_id": 10001,
        "sender": {"user_id": 10001, "nickname": "张三"},
    }
    payload.update(overrides)
    return make_event(**payload)


def test_poke_to_self() -> None:
    event = _notice(notice_type="notify", sub_type="poke", target_id=SELF_ID)
    result = render_notice(event, SELF_ID, 123456)
    assert result is not None
    assert result["adapter"] == {"internal": True, "origin": "poke"}
    assert result["message"][0]["data"]["text"] == "[系统] 用户 张三(10001) 戳了戳你"
    assert result["message_type"] == "group"
    assert result["group_id"] == 123456


def test_poke_to_someone_else_is_ignored() -> None:
    event = _notice(notice_type="notify", sub_type="poke", target_id=555)
    assert render_notice(event, SELF_ID, 123456) is None


def test_self_poke_is_ignored() -> None:
    event = _notice(notice_type="notify", sub_type="poke", target_id=SELF_ID, user_id=SELF_ID)
    assert render_notice(event, SELF_ID, 123456) is None


def test_member_join() -> None:
    event = _notice(notice_type="group_increase", sub_type="approve")
    result = render_notice(event, SELF_ID, 123456)
    assert result is not None
    assert result["adapter"]["origin"] == "member_join"
    assert "加入了群聊" in result["message"][0]["data"]["text"]


def test_member_leave() -> None:
    event = _notice(notice_type="group_decrease", sub_type="leave")
    result = render_notice(event, SELF_ID, 123456)
    assert result is not None
    assert result["adapter"]["origin"] == "member_leave"
    assert "退出了群聊" in result["message"][0]["data"]["text"]


def test_member_kick() -> None:
    event = _notice(notice_type="group_decrease", sub_type="kick")
    result = render_notice(event, SELF_ID, 123456)
    assert result is not None
    assert result["adapter"]["origin"] == "member_kick"
    assert "被管理员移出了群聊" in result["message"][0]["data"]["text"]


def test_self_leave_is_ignored() -> None:
    event = _notice(notice_type="group_decrease", sub_type="leave", user_id=SELF_ID)
    assert render_notice(event, SELF_ID, 123456) is None


def test_missing_sender_falls_back_to_qq() -> None:
    event = _notice(notice_type="group_increase", sender=None)
    result = render_notice(event, SELF_ID, 123456)
    assert result is not None
    assert "用户 10001(10001)" in result["message"][0]["data"]["text"]


def test_unknown_notice_is_ignored() -> None:
    event = _notice(notice_type="group_ban")
    assert render_notice(event, SELF_ID, 123456) is None
