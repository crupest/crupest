from __future__ import annotations

from crupest_chatbot_core.ratelimit import Cooldowns


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_first_call_is_allowed() -> None:
    cooldowns = Cooldowns({"poke": 10}, clock=Clock())
    assert cooldowns.allow("poke") is True


def test_second_call_inside_window_is_denied() -> None:
    clock = Clock()
    cooldowns = Cooldowns({"poke": 10}, clock=clock)
    assert cooldowns.allow("poke") is True
    clock.now += 9.9
    assert cooldowns.allow("poke") is False


def test_call_after_window_is_allowed() -> None:
    clock = Clock()
    cooldowns = Cooldowns({"poke": 10}, clock=clock)
    assert cooldowns.allow("poke") is True
    clock.now += 10.0
    assert cooldowns.allow("poke") is True


def test_unknown_key_is_unlimited() -> None:
    cooldowns = Cooldowns({"poke": 10}, clock=Clock())
    assert cooldowns.allow("send_group_msg") is True
    assert cooldowns.allow("send_group_msg") is True


def test_zero_window_is_unlimited() -> None:
    cooldowns = Cooldowns({"poke": 0}, clock=Clock())
    assert cooldowns.allow("poke") is True
    assert cooldowns.allow("poke") is True


def test_reset_clears_history() -> None:
    cooldowns = Cooldowns({"poke": 10}, clock=Clock())
    assert cooldowns.allow("poke") is True
    assert cooldowns.allow("poke") is False
    cooldowns.reset()
    assert cooldowns.allow("poke") is True
