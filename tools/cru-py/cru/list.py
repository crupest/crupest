from __future__ import annotations

from collections.abc import Callable, Iterator
from typing import Any, Generic, Iterable, TypeAlias, TypeVar, overload

from ._error import CruInternalError
from ._iter import CruIterator
from ._const import CruNotFound

_T = TypeVar("_T")
_O = TypeVar("_O")


class CruListEdit(CruIterator[_T]):
    def __init__(self, iterable: Iterable[_T], _list: CruList[Any]) -> None:
        super().__init__(iterable)
        self._list = _list

    def create_me(self, iterable: Iterable[_O]) -> CruListEdit[_O]:
        return CruListEdit(iterable, self._list)

    @property
    def list(self) -> CruList[Any]:
        return self._list

    def done(self) -> CruList[Any]:
        self._list.reset(self)
        return self._list


class CruList(list[_T]):
    def reset(self, new_values: Iterable[_T]):
        if self is new_values:
            new_values = list(new_values)
        self.clear()
        self.extend(new_values)
        return self

    def as_cru_iterator(self) -> CruIterator[_T]:
        return CruIterator(self)

    @staticmethod
    def make(maybe_list: Iterable[_T] | _T | None) -> CruList[_T]:
        if maybe_list is None:
            return CruList()
        if isinstance(maybe_list, Iterable):
            return CruList(maybe_list)
        return CruList([maybe_list])


_K = TypeVar("_K")

_KeyGetter: TypeAlias = Callable[[_T], _K]


class CruUniqueKeyList(Generic[_T, _K]):
    def __init__(
        self,
        key_getter: _KeyGetter[_T, _K],
        *,
        before_add: Callable[[_T], _T] | None = None,
    ):
        super().__init__()
        self._key_getter = key_getter
        self._before_add = before_add
        self._list: CruList[_T] = CruList()

    @property
    def key_getter(self) -> _KeyGetter[_T, _K]:
        return self._key_getter

    @property
    def internal_list(self) -> CruList[_T]:
        return self._list

    def validate_self(self):
        keys = self._list.transform(self._key_getter)
        if len(keys) != len(set(keys)):
            raise CruInternalError("Duplicate keys!")

    @overload
    def get_or(
        self, key: _K, fallback: CruNotFound = CruNotFound.VALUE
    ) -> _T | CruNotFound: ...

    @overload
    def get_or(self, key: _K, fallback: _O) -> _T | _O: ...

    def get_or(
        self, key: _K, fallback: _O | CruNotFound = CruNotFound.VALUE
    ) -> _T | _O | CruNotFound:
        return (
            self._list.as_cru_iterator()
            .filter(lambda v: key == self._key_getter(v))
            .first_or(fallback)
        )

    def get(self, key: _K) -> _T:
        value = self.get_or(key)
        if value is CruNotFound:
            raise KeyError(f"Key {key} not found!")
        return value  # type: ignore

    @property
    def keys(self) -> Iterable[_K]:
        return self._list.as_cru_iterator().map(self._key_getter)

    def has_key(self, key: _K) -> bool:
        return self.get_or(key) != CruNotFound.VALUE

    def try_remove(self, key: _K) -> bool:
        value = self.get_or(key)
        if value is CruNotFound.VALUE:
            return False
        self._list.remove(value)
        return True

    def remove(self, key: _K, allow_absence: bool = False) -> None:
        if not self.try_remove(key) and not allow_absence:
            raise KeyError(f"Key {key} not found!")

    def add(self, value: _T, /, replace: bool = False) -> None:
        v = self.get_or(self._key_getter(value))
        if v is not CruNotFound.VALUE:
            if not replace:
                raise KeyError(f"Key {self._key_getter(v)} already exists!")
            self._list.remove(v)
        if self._before_add is not None:
            value = self._before_add(value)
        self._list.append(value)

    def set(self, value: _T) -> None:
        self.add(value, True)

    def extend(self, iterable: Iterable[_T], /, replace: bool = False) -> None:
        values = list(iterable)
        to_remove = []
        for value in values:
            v = self.get_or(self._key_getter(value))
            if v is not CruNotFound.VALUE:
                if not replace:
                    raise KeyError(f"Key {self._key_getter(v)} already exists!")
                to_remove.append(v)
        for value in to_remove:
            self._list.remove(value)
        if self._before_add is not None:
            values = [self._before_add(value) for value in values]
        self._list.extend(values)

    def clear(self) -> None:
        self._list.reset([])

    def __iter__(self) -> Iterator[_T]:
        return iter(self._list)

    def __len__(self) -> int:
        return len(self._list)

    def cru_iter(self) -> CruIterator[_T]:
        return CruIterator(self._list)
