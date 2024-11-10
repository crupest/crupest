from collections.abc import Iterable, Callable
from typing import TypeVar, ParamSpec, Any, Generic

from ._const import CRU_NOT_FOUND

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")

CanBeList = T | Iterable[T] | None
ElementOperation = Callable[[T], Any]
ElementPredicate = Callable[[T], bool]
ElementTransformer = Callable[[Any], Any]
OptionalElementOperation = Callable[[T], Any] | None
OptionalElementTransformer = Callable[[Any], Any] | None


class ListOperations:

    @staticmethod
    def sub_by_indices(l: Iterable[T], *index: int) -> list[T]:
        return [v for i, v in enumerate(l) if i in index]

    @staticmethod
    def complement_indices(length: int, *index: int) -> list[int]:
        return [i for i in range(length) if i not in index]

    @staticmethod
    def foreach(l: Iterable[T], *f: OptionalElementOperation[T]) -> None:
        if len(f) == 0: return
        for v in l:
            for f_ in f:
                if f_ is not None:
                    f_(v)

    @staticmethod
    def all(l: Iterable[T], p: ElementPredicate[T]) -> bool:
        for v in l:
            if not p(v): return False
        return True

    @staticmethod
    def all_is_instance(l: Iterable[T], *t: type) -> bool:
        return all(type(v) in t for v in l)

    @staticmethod
    def any(l: Iterable[T], p: ElementPredicate[T]) -> bool:
        for v in l:
            if p(v): return True
        return False

    @staticmethod
    def find_all_if(l: Iterable[T], p: ElementPredicate[T]) -> list[T]:
        return [v for v in l if p(v)]

    @staticmethod
    def find_if(l: Iterable[T], p: ElementPredicate[T]) -> T | CRU_NOT_FOUND:
        r = ListOperations.find_all_if(l, p)
        return r[0] if len(r) > 0 else CRU_NOT_FOUND

    @staticmethod
    def find_all_indices_if(l: Iterable[T], p: ElementPredicate[T]) -> list[int]:
        return [i for i, v in enumerate(l) if p(v)]

    @staticmethod
    def find_index_if(l: Iterable[T], p: ElementPredicate[T]) -> int | CRU_NOT_FOUND:
        r = ListOperations.find_all_indices_if(l, p)
        return r[0] if len(r) > 0 else CRU_NOT_FOUND

    @staticmethod
    def transform(l: Iterable[T], *f: OptionalElementTransformer) -> list[Any]:
        r = []
        for v in l:
            for f_ in f:
                if f_ is not None:
                    v = f_(v)
            r.append(v)
        return r

    @staticmethod
    def transform_if(l: Iterable[T], f: OptionalElementTransformer, p: ElementPredicate[T]) -> list[Any]:
        return [(f(v) if f else v) for v in l if p(v)]

    @staticmethod
    def remove_by_indices(l: Iterable[T], *index: int | None) -> list[T]:
        return [v for i, v in enumerate(l) if i not in index]

    @staticmethod
    def remove_if(l: Iterable[T], p: ElementPredicate[T]) -> list[T]:
        i = ListOperations.find_index_if(l, p)
        return ListOperations.remove_by_indices(l, i)

    @staticmethod
    def remove_all_if(l: Iterable[T], p: ElementPredicate[T]) -> list[T]:
        return [v for v in l if not p(v)]

    @staticmethod
    def remove_all_value(l: Iterable[T], *r: Any) -> list[T]:
        return [v for v in l if v not in r]

    @staticmethod
    def replace_all_value(l: Iterable[T], old_value: Any, new_value: R) -> list[T | R]:
        return [new_value if v == old_value else v for v in l]

    @staticmethod
    def make(v: CanBeList[T], /, none_to_empty_list: bool = True) -> list[T]:
        if v is None and none_to_empty_list: return []
        return list(v) if isinstance(v, Iterable) else [v]


class CruList(list, Generic[T]):
    @property
    def is_empty(self) -> bool:
        return len(self) == 0

    def sub_by_indices(self, *index: int) -> "CruList"[T]:
        return CruList(ListOperations.sub_by_indices(self, *index))

    def complement_indices(self, *index: int) -> list[int]:
        return ListOperations.complement_indices(len(self), *index)

    def foreach(self, *f: OptionalElementOperation[T]) -> None:
        ListOperations.foreach(self, *f)

    def all(self, p: ElementPredicate[T]) -> bool:
        return ListOperations.all(self, p)

    def all_is_instance(self, *t: type) -> bool:
        return ListOperations.all_is_instance(self, *t)

    def any(self, p: ElementPredicate[T]) -> bool:
        return ListOperations.any(self, p)

    def find_all_if(self, p: ElementPredicate[T]) -> "CruList"[T]:
        return CruList(ListOperations.find_all_if(self, p))

    def find_if(self, p: ElementPredicate[T]) -> T | CRU_NOT_FOUND:
        return ListOperations.find_if(self, p)

    def find_all_indices_if(self, p: ElementPredicate[T]) -> "CruList"[int]:
        return CruList(ListOperations.find_all_indices_if(self, p))

    def find_index_if(self, p: ElementPredicate[T]) -> int | CRU_NOT_FOUND:
        return ListOperations.find_index_if(self, p)

    def transform(self, *f: OptionalElementTransformer) -> "CruList"[Any]:
        return CruList(ListOperations.transform(self, *f))

    def transform_if(self, f: OptionalElementTransformer, p: ElementPredicate[T]) -> "CruList"[Any]:
        return CruList(ListOperations.transform_if(self, f, p))

    def remove_by_indices(self, *index: int) -> "CruList"[T]:
        return CruList(ListOperations.remove_by_indices(self, *index))

    def remove_if(self, p: ElementPredicate[T]) -> "CruList"[T]:
        return CruList(ListOperations.remove_if(self, p))

    def remove_all_if(self, p: ElementPredicate[T]) -> "CruList"[T]:
        return CruList(ListOperations.remove_all_if(self, p))

    def remove_all_value(self, *r: Any) -> "CruList"[T]:
        return CruList(ListOperations.remove_all_value(self, *r))

    def replace_all_value(self, old_value: Any, new_value: R) -> "CruList"[T | R]:
        return CruList(ListOperations.replace_all_value(self, old_value, new_value))

    @staticmethod
    def make(l: CanBeList[T]) -> "CruList"[T]:
        return CruList(ListOperations.make(l))


class CruInplaceList(CruList, Generic[T]):

    def clear(self) -> "CruInplaceList[T]":
        self.clear()
        return self

    def extend(self, *l: Iterable[T]) -> "CruInplaceList[T]":
        self.extend(l)
        return self

    def reset(self, *l: Iterable[T]) -> "CruInplaceList[T]":
        self.clear()
        self.extend(l)
        return self

    def transform(self, *f: OptionalElementTransformer) -> "CruInplaceList"[Any]:
        return self.reset(super().transform(*f))

    def transform_if(self, f: OptionalElementTransformer, p: ElementPredicate[T]) -> "CruInplaceList"[Any]:
        return self.reset(super().transform_if(f, p))

    def remove_by_indices(self, *index: int) -> "CruInplaceList"[T]:
        return self.reset(super().remove_by_indices(*index))

    def remove_all_if(self, p: ElementPredicate[T]) -> "CruInplaceList"[T]:
        return self.reset(super().remove_all_if(p))

    def remove_all_value(self, *r: Any) -> "CruInplaceList"[T]:
        return self.reset(super().remove_all_value(*r))

    def replace_all_value(self, old_value: Any, new_value: R) -> "CruInplaceList"[T | R]:
        return self.reset(super().replace_all_value(old_value, new_value))

    @staticmethod
    def make(l: CanBeList[T]) -> "CruInplaceList"[T]:
        return CruInplaceList(ListOperations.make(l))


K = TypeVar("K")


class CruUniqueKeyInplaceList(Generic[T, K]):
    KeyGetter = Callable[[T], K]

    def __init__(self, get_key: KeyGetter, *, before_add: Callable[[T], T] | None = None):
        super().__init__()
        self._get_key = get_key
        self._before_add = before_add
        self._l: CruInplaceList[T] = CruInplaceList()

    @property
    def object_key_getter(self) -> KeyGetter:
        return self._get_key

    @property
    def internal_list(self) -> CruInplaceList[T]:
        return self._l

    def validate_self(self):
        keys = self._l.transform(self._get_key)
        if len(keys) != len(set(keys)):
            raise ValueError("Duplicate keys!")

    def get_or(self, k: K, fallback: Any = CRU_NOT_FOUND) -> T | Any:
        r = self._l.find_if(lambda i: k == self._get_key(i))
        return r if r is not CRU_NOT_FOUND else fallback

    def get(self, k: K) -> T:
        v = self.get_or(k, CRU_NOT_FOUND)
        if v is CRU_NOT_FOUND:
            raise KeyError(f"Key not found!")
        return v

    def has_key(self, k: K) -> bool:
        return self.get_or(k, CRU_NOT_FOUND) is not CRU_NOT_FOUND

    def has_any_key(self, *k: K) -> bool:
        return self._l.any(lambda i: self._get_key(i) in k)

    def try_remove(self, k: K) -> bool:
        i = self._l.find_index_if(lambda v: k == self._get_key(v))
        if i is CRU_NOT_FOUND: return False
        self._l.remove_by_indices(i)
        return True

    def remove(self, k: K, allow_absense: bool = False) -> None:
        if not self.try_remove(k) and not allow_absense:
            raise KeyError(f"Key {k} not found!")

    def add(self, v: T, /, replace: bool = False) -> None:
        if self.has_key(self._get_key(v)):
            if replace:
                self.remove(self._get_key(v))
            else:
                raise ValueError(f"Key {self._get_key(v)} already exists!")
        if self._before_add is not None:
            v = self._before_add(v)
        self._l.append(v)

    def set(self, v: T) -> None:
        self.add(v, True)

    def extend(self, l: Iterable[T], /, replace: bool = False) -> None:
        if not replace and self.has_any_key([self._get_key(i) for i in l]):
            raise ValueError("Keys already exists!")
        if self._before_add is not None:
            l = [self._before_add(i) for i in l]
        keys = [self._get_key(i) for i in l]
        self._l.remove_all_if(lambda i: self._get_key(i) in keys).extend(l)

    def clear(self) -> None:
        self._l.clear()

    def __iter__(self):
        return iter(self._l)

    def __len__(self):
        return len(self._l)
