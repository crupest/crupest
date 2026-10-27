"""``real_seq`` -> ``message_id`` for the actions that need a message id.

The model sees ``#real_seq`` in the sender prefix (the old behaviour), but
NapCat's APIs want ``message_id``.  One conversation means one small FIFO,
populated from inbound events only — the bot's own messages never carry a
``real_seq``.

Every inbound ``message_id`` is also remembered on its own, so a forward can be
checked against messages the adapter actually saw (and never against a node the
caller made up).
"""
from __future__ import annotations

from collections import OrderedDict
from typing import Any

from crupest_chatbot_core.schema import Event

#: Actions whose ``real_seq`` parameter must be translated.
SEQ_ACTIONS = frozenset({"set_msg_emoji_like", "mark_msg_as_read", "get_msg", "fetch_ptt_text"})


class SeqMap:
    def __init__(self, capacity: int = 2000) -> None:
        self._capacity = max(1, capacity)
        self._entries: OrderedDict[str, str] = OrderedDict()
        self._ids: OrderedDict[str, None] = OrderedDict()

    def record(self, real_seq: Any, message_id: Any) -> None:
        if real_seq in (None, "") or message_id in (None, ""):
            return
        key = str(real_seq)
        self._entries[key] = str(message_id)
        self._entries.move_to_end(key)
        while len(self._entries) > self._capacity:
            self._entries.popitem(last=False)

    def record_id(self, message_id: Any) -> None:
        """Remember an inbound message id even when there is no ``real_seq`` (DMs)."""
        if message_id in (None, ""):
            return
        key = str(message_id)
        self._ids[key] = None
        self._ids.move_to_end(key)
        while len(self._ids) > self._capacity:
            self._ids.popitem(last=False)

    def record_event(self, event: Event) -> None:
        self.record(event.real_seq, event.message_id)
        self.record_id(event.message_id)

    def resolve(self, real_seq: Any) -> str | None:
        if real_seq in (None, ""):
            return None
        return self._entries.get(str(real_seq))

    def known(self, message_id: Any) -> bool:
        """True when *message_id* arrived as an inbound message."""
        return str(message_id or "") in self._ids

    def apply(self, action: str, params: dict[str, Any]) -> dict[str, Any]:
        """Replace ``real_seq`` with ``message_id`` for the actions that need it."""
        if action not in SEQ_ACTIONS or "real_seq" not in params:
            return params
        translated = dict(params)
        real_seq = translated.pop("real_seq")
        message_id = self.resolve(real_seq)
        # Miss: pass real_seq through as message_id (go-cqhttp/Lagrange compat).
        translated["message_id"] = message_id if message_id is not None else real_seq
        return translated

    def __len__(self) -> int:
        return len(self._entries)
