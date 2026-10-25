from __future__ import annotations

from crupest_qqbot_core.text import to_plain


def test_strips_fenced_block() -> None:
    assert to_plain("看下:\n```python\nprint(1)\n```\n完") == "看下:\nprint(1)\n完"


def test_strips_inline_code() -> None:
    assert to_plain("用 `pip install` 装") == "用 pip install 装"


def test_strips_headings() -> None:
    assert to_plain("## 标题\n正文") == "标题\n正文"


def test_strips_bold_and_underscore_bold() -> None:
    assert to_plain("**重要** 和 __也重要__") == "重要 和 也重要"


def test_idempotent() -> None:
    once = to_plain("## t\n**a** `b`\n```\nc\n```")
    assert to_plain(once) == once


def test_empty_passthrough() -> None:
    assert to_plain("") == ""
