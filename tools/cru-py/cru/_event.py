from typing import ParamSpec, TypeVar, Callable

from ._iter import CruInplaceList, CruList

P = ParamSpec('P')
R = TypeVar('R')
F = Callable[P, R]


class EventHandlerToken:
    def __init__(self, event: "Event", handler: F, once: bool = False) -> None:
        self._event = event
        self._handler = handler
        self._once = once

    @property
    def event(self) -> "Event":
        return self._event

    @property
    def handler(self) -> F:
        return self._handler

    @property
    def once(self) -> bool:
        return self._once


class Event:
    def __init__(self, name: str) -> None:
        self._name = name
        self._tokens: CruInplaceList[EventHandlerToken] = CruInplaceList()

    def register(self, handler: F, once: bool = False) -> EventHandlerToken:
        token = EventHandlerToken(self, handler, once)
        self._tokens.append(token)
        return token

    def unregister(self, *h: EventHandlerToken | F) -> int:

        self._tokens.find_all_indices_if(lambda t: )
