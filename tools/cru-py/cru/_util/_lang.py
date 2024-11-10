from collections.abc import Callable
from typing import Any, Iterable, TypeVar, cast

T = TypeVar("T")
D = TypeVar("D")


def remove_element(
    iterable: Iterable[T | None], to_rm: Iterable[Any], des: type[D] | None = None
) -> D:
    to_rm = set(to_rm)
    return cast(Callable[..., D], des or list)(v for v in iterable if v not in to_rm)


def remove_none(iterable: Iterable[T | None], des: type[D] | None = None) -> D:
    return cast(Callable[..., D], des or list)(v for v in iterable if v is not None)
