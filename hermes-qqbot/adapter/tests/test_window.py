from __future__ import annotations

from crupest_qqbot_adapter.window import Window


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def test_starts_inactive() -> None:
    assert Window(10, clock=Clock()).active() is False


def test_touch_then_active() -> None:
    clock = Clock()
    window = Window(10, clock=clock)
    window.touch()
    assert window.active() is True


def test_expires_after_ttl() -> None:
    clock = Clock()
    window = Window(10, clock=clock)
    window.touch()
    clock.now += 9.9
    assert window.active() is True
    clock.now += 0.2
    assert window.active() is False


def test_touch_extends() -> None:
    clock = Clock()
    window = Window(10, clock=clock)
    window.touch()
    clock.now += 9
    window.touch()
    clock.now += 9
    assert window.active() is True


def test_clear() -> None:
    window = Window(10)
    window.touch()
    window.clear()
    assert window.active() is False
