from collections.abc import Iterable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import TypeVar, ParamSpec, Any, Generic, ClassVar, Optional, Union

from ._const import CRU_NOT_FOUND

T = TypeVar("T")
O = TypeVar("O")
R = TypeVar("R")
F = TypeVar("F")

CanBeList = T | Iterable[T] | None

OptionalIndex = int | None
OptionalType = type | None
ElementOperation = Callable[[T], Any] | None
ElementPredicate = Callable[[T], bool]
ElementTransformer = Callable[[T], R]
SelfElementTransformer = ElementTransformer[T, T]
AnyElementTransformer = ElementTransformer[Any, Any]
OptionalElementOperation = ElementOperation | None
OptionalElementTransformer = ElementTransformer | None
OptionalSelfElementTransformer = ElementTransformer[T, T]
OptionalAnyElementTransformer = AnyElementTransformer | None


def _flatten_with_func(o: T, max_depth: int, is_leave: ElementPredicate[T],
                       get_children: SelfElementTransformer[T], depth: int = 0) -> Iterable[T]:
    if depth == max_depth or is_leave(o):
        yield o
        return
    for child in get_children(o):
        yield from _flatten_with_func(child, max_depth, is_leave, get_children, depth + 1)


class _Action(Enum):
    SKIP = 0
    SEND = 1
    STOP = 2
    AGGREGATE = 3


@dataclass
class _Result(Generic[T]):
    Action: ClassVar[type[_Action]] = _Action

    value: T | O | None
    action: Action

    @staticmethod
    def skip() -> "_Result"[T]:
        return _Result(None, _Action.SKIP)

    @staticmethod
    def send(value: Any) -> "_Result"[T]:
        return _Result(value, _Action.SEND)

    @staticmethod
    def stop(value: Any = None) -> "_Result"[T]:
        return _Result(value, _Action.STOP)

    @staticmethod
    def aggregate(*result: "_Result"[T]) -> "_Result"[T]:
        return _Result(result, _Action.AGGREGATE)

    @staticmethod
    def send_last(value: Any) -> "_Result"[T]:
        return _Result.aggregate(_Result.send(value), _Result.stop())

    def flatten(self) -> Iterable["_Result"[T]]:
        return _flatten_with_func(self, -1, lambda r: r.action != _Action.AGGREGATE, lambda r: r.value)


_r_skip = _Result.skip
_r_send = _Result.send
_r_stop = _Result.stop
_r_send_last = _Result.send_last
_r_aggregate = _Result.aggregate


class _Defaults:
    @staticmethod
    def true(_):
        return True

    @staticmethod
    def false(_):
        return False

    @staticmethod
    def not_found(_):
        return CRU_NOT_FOUND


def _default_upstream() -> Iterable[Iterable]:
    return iter([])


CruIterableUpstream = Iterable[Iterable]
CruIterableOptionalUpstream = CruIterableUpstream | None


class CruIterableCreators:
    @staticmethod
    def with_(o: Any, /, upstreams: CruIterableOptionalUpstream = _default_upstream()) -> "CruIterableWrapper":
        return CruIterableWrapper(iter(o), upstreams)

    @staticmethod
    def empty(upstreams: CruIterableOptionalUpstream = _default_upstream()) -> "CruIterableWrapper":
        return CruIterableCreators.with_([], upstreams)

    @staticmethod
    def range(a, b=None, c=None, /, upstreams: CruIterableOptionalUpstream = _default_upstream()) -> \
    "CruIterableWrapper"[int]:
        args = [arg for arg in [a, b, c] if arg is not None]
        return CruIterableCreators.with_(range(*args), upstreams)

    @staticmethod
    def unite(*args: T, upstreams: CruIterableOptionalUpstream = _default_upstream()) -> "CruIterableWrapper"[T]:
        return CruIterableCreators.with_(args, upstreams)

    @staticmethod
    def _concat(*iterables: Iterable) -> Iterable:
        for iterable in iterables:
            yield from iterable

    @staticmethod
    def concat(*iterables: Iterable,
               upstreams: CruIterableOptionalUpstream = _default_upstream()) -> "CruIterableWrapper":
        return CruIterableWrapper(CruIterableCreators._concat(*iterables), upstreams)


class CruIterableWrapper(Generic[T]):
    Upstream = CruIterableUpstream
    OptionalUpstream = CruIterableOptionalUpstream
    _Result = _Result[T]
    _Operation = Callable[[T, int], _Result | Any | None]

    def __init__(self, iterable: Iterable[T], /, upstreams: OptionalUpstream = _default_upstream()) -> None:
        self._iterable = iterable
        self._upstreams = None if upstreams is None else list(upstreams)

    @property
    def me(self) -> Iterable[T]:
        return self._iterable

    # TODO: Return Type
    @property
    def my_upstreams(self) -> Optional["CruIterableWrapper"]:
        if self._upstreams is None:
            return None
        return CruIterableWrapper(iter(self._upstreams))

    def disable_my_upstreams(self) -> "CruIterableWrapper"[T]:
        return CruIterableWrapper(self._iterable, None)

    def clear_my_upstreams(self) -> "CruIterableWrapper"[T]:
        return CruIterableWrapper(self._iterable)

    def _create_upstreams_prepend_self(self) -> Upstream:
        yield self._iterable
        yield self.my_upstreams

    # TODO: Return Type
    def _create_new_upstreams(self, append: bool = True) -> Optional["CruIterableWrapper"]:
        if not append: return self.my_upstreams
        if self.my_upstreams is None:
            return None
        return CruIterableWrapper(self._create_upstreams_prepend_self())

    def clone_me(self, /, update_upstreams: bool = True) -> "CruIterableWrapper"[T]:
        return CruIterableWrapper(self._iterable, self._create_new_upstreams(update_upstreams))

    def replace_me_with(self, iterable: Iterable[O], /, update_upstreams: bool = True) -> "CruIterableWrapper"[O]:
        return CruIterableCreators.with_(iterable, upstreams=self._create_new_upstreams(update_upstreams))

    def replace_me_with_empty(self, /, update_upstreams: bool = True) -> "CruIterableWrapper"[O]:
        return CruIterableCreators.empty(upstreams=self._create_new_upstreams(update_upstreams))

    def replace_me_with_range(self, a, b=None, c=None, /, update_upstreams: bool = True) -> "CruIterableWrapper"[int]:
        return CruIterableCreators.range(a, b, c, upstreams=self._create_new_upstreams(update_upstreams))

    def replace_me_with_unite(self, *args: O, update_upstreams: bool = True) -> "CruIterableWrapper"[O]:
        return CruIterableCreators.unite(*args, upstreams=self._create_new_upstreams(update_upstreams))

    def replace_me_with_concat(self, *iterables: Iterable, update_upstreams: bool = True) -> "CruIterableWrapper":
        return CruIterableCreators.concat(*iterables, upstreams=self._create_new_upstreams(update_upstreams))

    @staticmethod
    def _non_result_to_yield(value: Any | None) -> _Result:
        return _Result.stop(value)

    @staticmethod
    def _non_result_to_return(value: Any | None) -> _Result:
        return _Result.stop(value)

    def _real_iterate(self, operation: _Operation,
                      convert_non_result: Callable[[Any | None], _Result]) -> Iterable:

        for index, element in enumerate(self._iterable):
            result = operation(element, index)
            if not isinstance(result, _Result):
                result = convert_non_result(result)
            for result in result.flatten():
                if result.action == _Result.Action.STOP:
                    return result.value
                elif result.action == _Result.Action.SEND:
                    yield result.value
                else:
                    continue

    def _new(self, operation: _Operation) -> "CruIterableWrapper":
        return CruIterableWrapper(self._real_iterate(operation, CruIterableWrapper._non_result_to_yield),
                                  self._create_new_upstreams())

    def _result(self, operation: _Operation,
                result_transform: OptionalElementTransformer[T, T | O] = None) -> T | O:
        try:
            self._real_iterate(operation, CruIterableWrapper._non_result_to_return)
        except StopIteration as stop:
            return stop.value if result_transform is None else result_transform(stop.value)

    @staticmethod
    def _make_set(iterable: Iterable, discard: Iterable | None) -> set:
        s = set(iterable)
        if discard is not None:
            s = s - set(discard)
        return s

    @staticmethod
    def _make_list(iterable: Iterable, discard: Iterable | None) -> list:
        if discard is None: return list(iterable)
        return [v for v in iterable if v not in discard]

    # noinspection PyMethodMayBeStatic
    def _help_make_set(self, iterable: Iterable, discard: Iterable | None = iter([None])) -> set:
        return CruIterableWrapper._make_set(iterable, discard)

    # noinspection PyMethodMayBeStatic
    def _help_make_list(self, iterable: Iterable, discard: Iterable | None = iter([None])) -> list:
        return CruIterableWrapper._make_list(iterable, discard)

    def to_set(self, discard: Iterable | None = None) -> set[T]:
        return CruIterableWrapper._make_set(self.me, discard)

    def to_list(self, discard: Iterable | None = None) -> list[T]:
        return CruIterableWrapper._make_list(self.me, discard)

    def copy(self) -> "CruIterableWrapper":
        return CruIterableWrapper(iter(self.to_list()), self._create_new_upstreams())

    def concat(self, *iterable: Iterable[T]) -> "CruIterableWrapper":
        return self.replace_me_with_concat(self.me, *iterable)

    def all(self, predicate: ElementPredicate[T]) -> bool:
        """
        partial
        """
        return self._result(lambda v, _: predicate(v) and None, _Defaults.true)

    def all_isinstance(self, *types: OptionalType) -> bool:
        """
        partial
        """
        types = self._help_make_set(types)
        return self.all(lambda v: type(v) in types)

    def any(self, predicate: ElementPredicate[T]) -> bool:
        """
        partial
        """
        return self._result(lambda v, _: predicate(v) or None, _Defaults.false)

    def number(self) -> "CruIterableWrapper":
        """
        partial
        """
        return self._new(lambda _, i: i)

    def take(self, predicate: ElementPredicate[T]) -> "CruIterableWrapper":
        """
        complete
        """
        return self._new(lambda v, _: _r_send(v) if predicate(v) else None)

    def transform(self, *transformers: OptionalElementTransformer) -> "CruIterableWrapper":
        """
        complete
        """

        def _transform_element(element, _):
            for transformer in self._help_make_list(transformers):
                if transformer is not None:
                    element = transformer(element)
            return _r_send(element)

        return self._new(_transform_element)

    def take_n(self, max_count: int, neg_is_clone: bool = True) -> "CruIterableWrapper":
        """
        partial
        """
        if max_count < 0:
            if neg_is_clone:
                return self.clone_me()
            else:
                raise ValueError("max_count must be 0 or positive.")
        elif max_count == 0:
            return self.drop_all()
        return self._new(lambda v, i: _r_send(v) if i < max_count - 1 else _r_send_last(v))

    def take_by_indices(self, *indices: OptionalIndex) -> "CruIterableWrapper":
        """
        partial
        """
        indices = self._help_make_set(indices)
        max_index = max(indices)
        return self.take_n(max_index + 1)._new(lambda v, i: _r_send(v) if i in indices else None)

    def single_or(self, fallback: Any | None = CRU_NOT_FOUND) -> T | Any | CRU_NOT_FOUND:
        """
        partial
        """
        first_2 = self.take_n(2)
        has_value = False
        value = None
        for element in first_2.me:
            if has_value:
                raise ValueError("More than one value found.")
            has_value = True
            value = element
        if has_value:
            return value
        else:
            return fallback

    def first_or(self, predicate: ElementPredicate[T], fallback: Any | None = CRU_NOT_FOUND) -> T | CRU_NOT_FOUND:
        """
        partial
        """
        result_iterable = self.take_n(1).single_or()

    @staticmethod
    def first_index(iterable: Iterable[T], predicate: ElementPredicate[T]) -> int | CRU_NOT_FOUND:
        """
        partial
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                return index

    @staticmethod
    def take_indices(iterable: Iterable[T], predicate: ElementPredicate[T]) -> Iterable[int]:
        """
        complete
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                yield index

    @staticmethod
    def flatten(o, max_depth=-1, is_leave: ElementPredicate | None = None,
                get_children: OptionalElementTransformer = None) -> Iterable:
        """
        complete
        """
        if is_leave is None:
            is_leave = lambda v: not isinstance(v, Iterable)
        if get_children is None:
            get_children = lambda v: v
        return CruIterableWrapper._flatten_with_func(o, max_depth, is_leave, get_children)

    @staticmethod
    def skip_by_indices(iterable: Iterable[T], *indices: OptionalIndex) -> Iterable[T]:
        """
        complete
        """
        indices = set(indices) - {None}
        for index, element in enumerate(iterable):
            if index not in indices:
                yield element

    @staticmethod
    def skip_if(iterable: Iterable[T], predicate: ElementPredicate[T]) -> list[T]:
        """
        complete
        """
        for element in iterable:
            if not predicate(element):
                yield element

    def drop_all(self) -> "CruIterableWrapper":
        return self.replace_me_with_empty()

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
    def foreach(iterable: Iterable[T], *f: OptionalElementOperation[T]) -> None:
        if len(f) == 0: return
        for v in iterable:
            for f_ in f:
                if f_ is not None:
                    f_(v)

    @staticmethod
    def make(v: CanBeList[T], /, none_to_empty_list: bool = True) -> list[T]:
        if v is None and none_to_empty_list: return []
        return list(v) if isinstance(v, Iterable) else [v]


class ListOperations:
    @staticmethod
    def all(iterable: Iterable[T], predicate: ElementPredicate[T]) -> bool:
        """
        partial
        """
        return _God.spy(iterable, lambda v, _: predicate(v) and None, _God.Default.true)

    @staticmethod
    def all_isinstance(iterable: Iterable[T], *types: OptionalType) -> bool:
        """
        partial
        """
        types = _God.help_make_set(types)
        return ListOperations.all(iterable, lambda v: type(v) in types)

    @staticmethod
    def any(iterable: Iterable[T], predicate: ElementPredicate[T]) -> bool:
        """
        partial
        """
        return _God.spy(iterable, lambda v, _: predicate(v) or None, _God.Default.false)

    @staticmethod
    def indices(iterable: Iterable[T]) -> Iterable[int]:
        """
        partial
        """
        return _God.new(iterable, lambda _, i: i)

    @staticmethod
    def take(iterable: Iterable[T], predicate: ElementPredicate[T]) -> Iterable[T]:
        """
        complete
        """
        return _God.new(iterable, lambda v, _: _God.yield_(v) if predicate(v) else None)

    @staticmethod
    def transform(iterable: Iterable[T], *transformers: OptionalElementTransformer) -> Iterable:
        """
        complete
        """

        def _transform_element(element, _):
            for transformer in transformers:
                if transformer is not None:
                    element = transformer(element)
            return element

        return _God.new(iterable, _transform_element)

    @staticmethod
    def take_n(iterable: Iterable[T], n: int) -> Iterable[T]:
        """
        partial
        """
        if n < 0:
            return iterable
        elif n == 0:
            return []
        return range(n)._god_yield(iterable, lambda v, i: _yield(v) if i < n else _return())

    @staticmethod
    def take_by_indices(iterable: Iterable[T], *indices: OptionalIndex) -> Iterable[T]:
        """
        partial
        """
        indices = set(indices) - {None}
        max_index = max(indices)
        iterable = ListOperations.take_n(iterable, max_index + 1)
        return _god_yield(iterable, lambda v, i: _yield(v) if i in indices else None)

    @staticmethod
    def first(iterable: Iterable[T]) -> T | CRU_NOT_FOUND:
        """
        partial
        """
        result_iterable = ListOperations.take_n(iterable, 1)
        for element in result_iterable:
            return element
        return CRU_NOT_FOUND

    @staticmethod
    def first_index(iterable: Iterable[T], predicate: ElementPredicate[T]) -> int | CRU_NOT_FOUND:
        """
        partial
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                return index

    @staticmethod
    def take_indices(iterable: Iterable[T], predicate: ElementPredicate[T]) -> Iterable[int]:
        """
        complete
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                yield index

    @staticmethod
    def _flatten(o, depth: int, max_depth: int) -> Iterable:
        if depth == max_depth or not isinstance(o, Iterable):
            yield o
            return
        for v in o:
            yield from ListOperations._flatten(v, depth + 1, max_depth)

    @staticmethod
    def flatten(o, max_depth=-1) -> Iterable:
        """
        complete
        """
        return ListOperations._flatten(o, 0, max_depth)

    @staticmethod
    def skip_by_indices(iterable: Iterable[T], *indices: OptionalIndex) -> Iterable[T]:
        """
        complete
        """
        indices = set(indices) - {None}
        for index, element in enumerate(iterable):
            if index not in indices:
                yield element

    @staticmethod
    def skip_if(iterable: Iterable[T], predicate: ElementPredicate[T]) -> list[T]:
        """
        complete
        """
        for element in iterable:
            if not predicate(element):
                yield element

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
    def foreach(iterable: Iterable[T], *f: OptionalElementOperation[T]) -> None:
        if len(f) == 0: return
        for v in iterable:
            for f_ in f:
                if f_ is not None:
                    f_(v)

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

    def split_by_indices(self, *index: int) -> tuple["CruList"[T], "CruList"[T]]:
        l1, l2 = ListOperations.split_by_indices(self, *index)
        return CruList(l1), CruList(l2)

    def complement_indices(self, *index: int) -> list[int]:
        return ListOperations.complement_indices(len(self), *index)

    def foreach(self, *f: OptionalElementOperation[T]) -> None:
        ListOperations.foreach(self, *f)

    def all(self, p: ElementPredicate[T]) -> bool:
        return ListOperations.all(self, p)

    def all_is_instance(self, *t: type) -> bool:
        return ListOperations.all_isinstance(self, *t)

    def any(self, p: ElementPredicate[T]) -> bool:
        return ListOperations.any(self, p)

    def find_all_if(self, p: ElementPredicate[T]) -> "CruList"[T]:
        return CruList(ListOperations.take(self, p))

    def find_if(self, p: ElementPredicate[T]) -> T | CRU_NOT_FOUND:
        return ListOperations.first(self, p)

    def find_all_indices_if(self, p: ElementPredicate[T]) -> "CruList"[int]:
        return CruList(ListOperations.take_indices(self, p))

    def find_index_if(self, p: ElementPredicate[T]) -> int | CRU_NOT_FOUND:
        return ListOperations.first_index(self, p)

    def split_if(self, p: ElementPredicate[T]) -> tuple["CruList"[T], "CruList"[T]]:
        l1, l2 = ListOperations.split_if(self, p)
        return CruList(l1), CruList(l2)

    def split_by_types(self, *t: type) -> tuple["CruList"[T], "CruList"[T]]:
        l1, l2 = ListOperations.split_by_types(self, *t)
        return CruList(l1), CruList(l2)

    def transform(self, *f: OptionalElementTransformer) -> "CruList"[Any]:
        return CruList(ListOperations.transform(self, *f))

    def transform_if(self, f: OptionalElementTransformer, p: ElementPredicate[T]) -> "CruList"[Any]:
        return CruList(ListOperations.transform_if(self, f, p))

    def remove_by_indices(self, *index: int) -> "CruList"[T]:
        return CruList(ListOperations.skip_by_indices(self, *index))

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
