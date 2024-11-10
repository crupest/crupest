from __future__ import annotations

from collections.abc import Callable
from typing import Generic, Iterable, Self, TypeAlias, TypeVar
from ._iter import CruIterable

_T = TypeVar("_T")


class CruListEdit(CruIterable.Wrapper[_T]):
    def done(self) -> CruList[_T]:
        l: CruList[_T] = self.my_attr["list"]
        l.reset(self)
        return l


class CruList(list[_T]):
    def reset(self, new_values: Iterable[_T]):
        if self is new_values:
            new_values = list(new_values)
        self.clear()
        self.extend(new_values)
        return self

    def as_iterable_wrapper(self) -> CruIterable.Wrapper[_T]:
        return CruIterable.Wrapper(self)

    def as_edit_iterable_wrapper(self) -> CruListEdit[_T]:
        return CruListEdit(self, attr={"list": self})

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
            raise ValueError("Duplicate keys!")

    # TODO: Continue here!
    def get_or(self, key: K, fallback: Any = CRU_NOT_FOUND) -> _V | Any:
        r = self._l.find_if(lambda i: k == self._key_getter(i))
        return r if r is not CRU_NOT_FOUND else fallback

    def get(self, k: K) -> _V:
        v = self.get_or(k, CRU_NOT_FOUND)
        if v is CRU_NOT_FOUND:
            raise KeyError(f"Key not found!")
        return v

    def has_key(self, k: K) -> bool:
        return self.get_or(k, CRU_NOT_FOUND) is not CRU_NOT_FOUND

    def has_any_key(self, *k: K) -> bool:
        return self._l.any(lambda i: self._key_getter(i) in k)

    def try_remove(self, k: K) -> bool:
        i = self._l.find_index_if(lambda v: k == self._key_getter(v))
        if i is CRU_NOT_FOUND:
            return False
        self._l.remove_by_indices(i)
        return True

    def remove(self, k: K, allow_absense: bool = False) -> None:
        if not self.try_remove(k) and not allow_absense:
            raise KeyError(f"Key {k} not found!")

    def add(self, v: _V, /, replace: bool = False) -> None:
        if self.has_key(self._key_getter(v)):
            if replace:
                self.remove(self._key_getter(v))
            else:
                raise ValueError(f"Key {self._key_getter(v)} already exists!")
        if self._before_add is not None:
            v = self._before_add(v)
        self._l.append(v)

    def set(self, v: _V) -> None:
        self.add(v, True)

    def extend(self, l: Iterable[_V], /, replace: bool = False) -> None:
        if not replace and self.has_any_key([self._key_getter(i) for i in l]):
            raise ValueError("Keys already exists!")
        if self._before_add is not None:
            l = [self._before_add(i) for i in l]
        keys = [self._key_getter(i) for i in l]
        self._l.remove_all_if(lambda i: self._key_getter(i) in keys).extend(l)

    def clear(self) -> None:
        self._l.clear()

    def __iter__(self):
        return iter(self._l)

    def __len__(self):
        return len(self._l)
