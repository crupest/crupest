from collections.abc import Callable
from typing import Any, Iterable, TypeVar, cast

_T = TypeVar("_T")
_D = TypeVar("_D")


def remove_element(
    iterable: Iterable[_T | None], to_rm: Iterable[Any], des: type[_D] | None = None
) -> _D:
    to_rm = set(to_rm)
    return cast(Callable[..., _D], des or list)(v for v in iterable if v not in to_rm)


def remove_none(iterable: Iterable[_T | None], des: type[_D] | None = None) -> _D:
    return cast(Callable[..., _D], des or list)(v for v in iterable if v is not None)
