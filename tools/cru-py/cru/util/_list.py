from collections.abc import Iterable, Callable
from typing import TypeVar, ParamSpec, Any, Generic

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")

CanBeList = T | Iterable[T] | None


class ListOperations:

    @staticmethod
    def foreach(l: Iterable[T], *f: Callable[[T], None] | None) -> None:
        if len(f) == 0: return
        for v in l:
            for f_ in f:
                if f_ is not None:
                    f_(v)

    @staticmethod
    def transform(l: Iterable[T], *f: Callable | None) -> list[R]:
        r = []
        for v in l:
            for f_ in f:
                if f_ is not None:
                    v = f_(v)
            r.append(v)
        return r

    @staticmethod
    def transform_if(l: Iterable[T], f: Callable[[T], R] | None, p: Callable[[T], bool] | None) -> list[R]:
        return [(f(v) if f else v) for v in l if (p(v) if p else True)]

    @staticmethod
    def all(l: Iterable[T], *p: Callable[[T], bool] | None) -> bool:
        if len(p) == 0 or all(v is None for v in p):
            raise ValueError("At least one predicate is required!")
        for v in l:
            for p_ in p:
                if p_ is not None and not p_(v): return False
        return True

    @staticmethod
    def all_is_instance(l: Iterable[T], *t: type) -> bool:
        return all(type(v) in t for v in l)

    @staticmethod
    def any(l: Iterable[T], *p: Callable[[T], bool] | None) -> bool:
        if len(p) == 0 or all(v is None for v in p):
            raise ValueError("At least one predicate is required!")
        for v in l:
            for p_ in p:
                if p_ is not None and p_(v): return True
        return False

    @staticmethod
    def make(v: CanBeList[T], /, none_to_empty_list: bool = True) -> list[T]:
        if v is None and none_to_empty_list: return []
        return v if isinstance(v, Iterable) else [v]

    @staticmethod
    def remove_all_if(l: Iterable[T], *p: Callable[[], bool] | None) -> list[T]:
        def stay(v):
            for p_ in p:
                if p_ is not None and p_(): return False
            return True

        return [v for v in l if stay(v)]

    @staticmethod
    def remove_all_value(l: Iterable[T], *r) -> list[T]:
        return [v for v in l if v not in r]

    @staticmethod
    def replace_all_value(l: Iterable[T], old_value: Any, new_value: R) -> list[T | R]:
        return [new_value if v == old_value else v for v in l]


class CruList(list, Generic[T]):

    def foreach(self, *f: Callable[[T], None] | None) -> None:
        ListOperations.foreach(self, *f)

    def transform(self, *f: Callable[[T], R] | None) -> "CruList"[R]:
        return CruList(ListOperations.transform(self, *f))

    def transform_if(self, f: Callable[[T], R] | None, p: Callable[[T], bool] | None) -> "CruList"[R]:
        return CruList(ListOperations.transform_if(self, f, p))

    def all(self, *p: Callable[[T], bool] | None) -> bool:
        return ListOperations.all(self, *p)

    def all_is_instance(self, *t: type) -> bool:
        return ListOperations.all_is_instance(self, *t)

    def any(self, *p: Callable[[T], bool] | None) -> bool:
        return ListOperations.any(self, *p)

    def remove_all_if(self, *p: Callable[[]]) -> "CruList"[T]:
        return CruList(ListOperations.remove_all_if(self, *p))

    def remove_all_value(self, *r) -> "CruList"[T]:
        return CruList(ListOperations.remove_all_value(self, *r))

    def replace_all_value(self, old_value: Any, new_value: R) -> "CruList"[T | R]:
        return CruList(ListOperations.replace_all_value(self, old_value, new_value))

    @staticmethod
    def make(l: CanBeList[T]) -> "CruList"[T]:
        return CruList(ListOperations.make(l))
