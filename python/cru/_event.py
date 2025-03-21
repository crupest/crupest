from __future__ import annotations

from collections.abc import Callable
from typing import Generic, ParamSpec, TypeVar

from .list import CruList

_P = ParamSpec("_P")
_R = TypeVar("_R")


class CruEventHandlerToken(Generic[_P, _R]):
    def __init__(
        self, event: CruEvent, handler: Callable[_P, _R], once: bool = False
    ) -> None:
        self._event = event
        self._handler = handler
        self._once = once

    @property
    def event(self) -> CruEvent:
        return self._event

    @property
    def handler(self) -> Callable[_P, _R]:
        return self._handler

    @property
    def once(self) -> bool:
        return self._once


class CruEvent(Generic[_P, _R]):
    def __init__(self, name: str) -> None:
        self._name = name
        self._tokens: CruList[CruEventHandlerToken] = CruList()

    def register(
        self, handler: Callable[_P, _R], once: bool = False
    ) -> CruEventHandlerToken:
        token = CruEventHandlerToken(self, handler, once)
        self._tokens.append(token)
        return token

    def unregister(self, *handlers: CruEventHandlerToken | Callable[_P, _R]) -> int:
        old_length = len(self._tokens)
        self._tokens.reset(
            self._tokens.as_cru_iterator().filter(
                (lambda t: t in handlers or t.handler in handlers)
            )
        )
        return old_length - len(self._tokens)

    def trigger(self, *args: _P.args, **kwargs: _P.kwargs) -> CruList[_R]:
        results = CruList(
            self._tokens.as_cru_iterator()
            .transform(lambda t: t.handler(*args, **kwargs))
            .to_list()
        )
        self._tokens.reset(self._tokens.as_cru_iterator().filter(lambda t: not t.once))
        return results
