from __future__ import annotations

from collections.abc import Iterable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import (
    Generator,
    Literal,
    Self,
    TypeAlias,
    TypeVar,
    ParamSpec,
    Any,
    Generic,
    ClassVar,
    Optional,
    Union,
    assert_never,
    cast,
    overload,
    override,
)

from ._const import CruNoValue, CruNotFound

P = ParamSpec("P")
T = TypeVar("T")
O = TypeVar("O")
F = TypeVar("F")

CanBeList: TypeAlias = Iterable[T] | T | None

OptionalIndex: TypeAlias = int | None
OptionalType: TypeAlias = type | None
ElementOperation: TypeAlias = Callable[[T], Any]
ElementPredicate: TypeAlias = Callable[[T], bool]
ElementTransformer: TypeAlias = Callable[[T], O]
SelfElementTransformer: TypeAlias = ElementTransformer[T, T]
AnyElementTransformer: TypeAlias = ElementTransformer[Any, Any]


def flatten_with_func(
    o: T,
    max_depth: int,
    is_leave: ElementPredicate[T],
    get_children: ElementTransformer[T, Iterable[T]],
    depth: int = 0,
) -> Iterable[T]:
    if depth == max_depth or is_leave(o):
        yield o
        return
    for child in get_children(o):
        yield from flatten_with_func(
            child, max_depth, is_leave, get_children, depth + 1
        )


class _StepActionKind(Enum):
    SKIP = 0
    # TODO: Rename this
    SEND = 1
    STOP = 2
    AGGREGATE = 3


@dataclass
class _StepAction(Generic[T]):
    value: Iterable[_StepAction[T]] | T | None
    kind: _StepActionKind

    @property
    def non_aggregate_value(self) -> T:
        assert self.kind != _StepActionKind.AGGREGATE
        return cast(T, self.value)

    @staticmethod
    def skip() -> _StepAction[T]:
        return _StepAction(None, _StepActionKind.SKIP)

    @staticmethod
    def send(value: T | None) -> _StepAction[T]:
        return _StepAction(value, _StepActionKind.SEND)

    @staticmethod
    def stop(value: T | None = None) -> _StepAction[T]:
        return _StepAction(value, _StepActionKind.STOP)

    @staticmethod
    def aggregate(*results: _StepAction[T]) -> _StepAction[T]:
        return _StepAction(results, _StepActionKind.AGGREGATE)

    @staticmethod
    def send_last(value: Any) -> _StepAction[T]:
        return _StepAction.aggregate(_StepAction.send(value), _StepAction.stop())

    def flatten(self) -> Iterable[_StepAction[T]]:
        return flatten_with_func(
            self,
            -1,
            lambda r: r.kind != _StepActionKind.AGGREGATE,
            lambda r: cast(Iterable[_StepAction[T]], r.value),
        )


_r_skip = _StepAction.skip
_r_send = _StepAction.send
_r_stop = _StepAction.stop
_r_send_last = _StepAction.send_last
_r_aggregate = _StepAction.aggregate


_GeneralStepAction: TypeAlias = _StepAction[T] | T | None
_GeneralStepActionConverter: TypeAlias = Callable[
    [_GeneralStepAction[T]], _StepAction[T]
]
_IterateOperation = Callable[[T, int], _GeneralStepAction[O]]
_IteratePreHook = Callable[[Iterable[T]], _GeneralStepAction[O]]
_IteratePostHook = Callable[[int], _GeneralStepAction[O]]


class CruGenericIterableMeta:
    StepActionKind = _StepActionKind
    StepAction = _StepAction
    GeneralStepAction = _GeneralStepAction
    GeneralStepActionConverter = _GeneralStepActionConverter
    IterateOperation = _IterateOperation
    IteratePreHook = _IteratePreHook
    IteratePostHook = _IteratePostHook

    @staticmethod
    def _non_result_to_send(value: O | None) -> _StepAction[O]:
        return _StepAction.send(value)

    @staticmethod
    def _non_result_to_stop(value: O | None) -> _StepAction[O]:
        return _StepAction.stop(value)

    @staticmethod
    def _none_pre_iterate() -> _StepAction[O]:
        return _r_skip()

    @staticmethod
    def _none_post_iterate(
        _index: int,
    ) -> _StepAction[O]:
        return _r_skip()

    def iterate(
        self,
        operation: _IterateOperation[T, O],
        fallback_return: O,
        pre_iterate: _IteratePreHook[T, O],
        post_iterate: _IteratePostHook[O],
        convert_non_result: Callable[[O | None], _StepAction[O]],
    ) -> Generator[O, None, O]:
        pre_result = pre_iterate(self._iterable)
        if not isinstance(pre_result, _StepAction):
            real_pre_result = convert_non_result(pre_result)
        for r in real_pre_result.flatten():
            if r.kind == _StepActionKind.STOP:
                return r.non_aggregate_value
            elif r.kind == _StepActionKind.SEND:
                yield r.non_aggregate_value

        for index, element in enumerate(self._iterable):
            result = operation(element, index)
            if not isinstance(result, _StepAction):
                real_result = convert_non_result(result)
            for r in real_result.flatten():
                if r.kind == _StepActionKind.STOP:
                    return r.non_aggregate_value
                elif r.kind == _StepActionKind.SEND:
                    yield r.non_aggregate_value
                else:
                    continue

        post_result = post_iterate(index + 1)
        if not isinstance(post_result, _StepAction):
            real_post_result = convert_non_result(post_result)
        for r in real_post_result.flatten():
            if r.kind == _StepActionKind.STOP:
                return r.non_aggregate_value
            elif r.kind == _StepActionKind.SEND:
                yield r.non_aggregate_value

        return fallback_return

    def _new(
        self,
        operation: _IterateOperation,
        fallback_return: O,
        /,
        pre_iterate: _IteratePreHook[T, O] | None = None,
        post_iterate: _IteratePostHook[O] | None = None,
    ) -> CruIterableWrapper:
        return CruIterableWrapper(
            self.iterate(
                operation,
                fallback_return,
                pre_iterate or CruIterableWrapper._none_pre_iterate,
                post_iterate or CruIterableWrapper._none_post_iterate,
                CruIterableWrapper._non_result_to_send,
            ),
            self._create_new_upstream(),
        )

    def _result(
        self,
        operation: _IterateOperation,
        fallback_return: O,
        /,
        result_transform: SelfElementTransformer[O] | None = None,
        pre_iterate: _IteratePreHook[T, O] | None = None,
        post_iterate: _IteratePostHook[O] | None = None,
    ) -> O:
        try:
            for _ in self.iterate(
                operation,
                fallback_return,
                pre_iterate or CruIterableWrapper._none_pre_iterate,
                post_iterate or CruIterableWrapper._none_post_iterate,
                CruIterableWrapper._non_result_to_stop,
            ):
                pass
        except StopIteration as stop:
            return (
                stop.value if result_transform is None else result_transform(stop.value)
            )
        raise RuntimeError("Should not reach here")


class IterDefaultResults:
    @staticmethod
    def true(_):
        return True

    @staticmethod
    def false(_):
        return False

    @staticmethod
    def not_found(_):
        return CruNotFound.VALUE


class CruIterableCreators:
    @staticmethod
    def with_(o: Any) -> CruIterableWrapper:
        return CruIterableWrapper(iter(o))

    @staticmethod
    def empty() -> CruIterableWrapper:
        return CruIterableCreators.with_([])

    @staticmethod
    def range(
        a,
        b=None,
        c=None,
    ) -> CruIterableWrapper[int]:
        args = [arg for arg in [a, b, c] if arg is not None]
        return CruIterableCreators.with_(range(*args))

    @staticmethod
    def unite(*args: T) -> CruIterableWrapper[T]:
        return CruIterableCreators.with_(args)

    @staticmethod
    def _concat(*iterables: Iterable) -> Iterable:
        for iterable in iterables:
            yield from iterable

    @staticmethod
    def concat(*iterables: Iterable) -> CruIterableWrapper:
        return CruIterableWrapper(CruIterableCreators._concat(*iterables))


class CruIterableWrapper(Generic[T]):

    def __init__(
        self,
        iterable: Iterable[T],
    ) -> None:
        self._iterable = iterable

    def __iter__(self):
        return self._iterable.__iter__()

    @property
    def me(self) -> Iterable[T]:
        return self._iterable

    def replace_me_with(self, iterable: Iterable[O]) -> CruIterableWrapper[O]:
        return CruIterableCreators.with_(iterable)

    def replace_me_with_empty(self) -> CruIterableWrapper[O]:
        return CruIterableCreators.empty()

    def replace_me_with_range(self, a, b=None, c=None) -> CruIterableWrapper[int]:
        return CruIterableCreators.range(a, b, c)

    def replace_me_with_unite(self, *args: O) -> CruIterableWrapper[O]:
        return CruIterableCreators.unite(*args)

    def replace_me_with_concat(self, *iterables: Iterable) -> CruIterableWrapper:
        return CruIterableCreators.concat(*iterables)

    @staticmethod
    def _make_set(iterable: Iterable[O], discard: Iterable[Any] | None) -> set[O]:
        s = set(iterable)
        if discard is not None:
            s = s - set(discard)
        return s

    @staticmethod
    def _make_list(iterable: Iterable[O], discard: Iterable[Any] | None) -> list[O]:
        if discard is None:
            return list(iterable)
        return [v for v in iterable if v not in discard]

    def _help_make_set(
        self, iterable: Iterable[O], discard: Iterable[Any] | None
    ) -> set[O]:
        return CruIterableWrapper._make_set(iterable, discard)

    def _help_make_list(
        self, iterable: Iterable[O], discard: Iterable[Any] | None
    ) -> list[O]:
        return CruIterableWrapper._make_list(iterable, discard)

    def to_set(self, discard: Iterable[Any] | None = None) -> set[T]:
        return CruIterableWrapper._make_set(self.me, discard)

    def to_list(self, discard: Iterable[Any] | None = None) -> list[T]:
        return CruIterableWrapper._make_list(self.me, discard)

    def copy(self) -> CruIterableWrapper:
        return CruIterableWrapper(iter(self.to_list()), self._create_new_upstream())

    def new_start(
        self, other: Iterable[O], /, clear_upstream: bool = False
    ) -> CruIterableWrapper[O]:
        return CruIterableWrapper(
            other, None if clear_upstream else self._create_new_upstream()
        )

    @overload
    def concat(self) -> Self: ...

    @overload
    def concat(
        self, *iterable: Iterable[Any], last: Iterable[O]
    ) -> CruIterableWrapper[O]: ...

    def concat(self, *iterable: Iterable[Any]) -> CruIterableWrapper[Any]:  # type: ignore
        return self.new_start(CruIterableCreators.concat(self.me, *iterable))

    def all(self, predicate: ElementPredicate[T]) -> bool:
        """
        partial
        """
        return self._result(lambda v, _: predicate(v) and None, IterDefaultResults.true)

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
        return self._result(lambda v, _: predicate(v) or None, IterDefaultResults.false)

    def number(self) -> CruIterableWrapper:
        """
        partial
        """
        return self._new(lambda _, i: i)

    def take(self, predicate: ElementPredicate[T]) -> CruIterableWrapper:
        """
        complete
        """
        return self._new(lambda v, _: _r_send(v) if predicate(v) else None)

    def transform(
        self, *transformers: OptionalElementTransformer
    ) -> CruIterableWrapper:
        """
        complete
        """

        def _transform_element(element, _):
            for transformer in self._help_make_list(transformers):
                if transformer is not None:
                    element = transformer(element)
            return _r_send(element)

        return self._new(_transform_element)

    def take_n(self, max_count: int, neg_is_clone: bool = True) -> CruIterableWrapper:
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
        return self._new(
            lambda v, i: _r_send(v) if i < max_count - 1 else _r_send_last(v)
        )

    def take_by_indices(self, *indices: OptionalIndex) -> CruIterableWrapper:
        """
        partial
        """
        indices = self._help_make_set(indices)
        max_index = max(indices)
        return self.take_n(max_index + 1)._new(
            lambda v, i: _r_send(v) if i in indices else None
        )

    def single_or(
        self, fallback: Any | None = CRU_NOT_FOUND
    ) -> T | Any | CRU_NOT_FOUND:
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

    def first_or(
        self, predicate: ElementPredicate[T], fallback: Any | None = CRU_NOT_FOUND
    ) -> T | CRU_NOT_FOUND:
        """
        partial
        """
        result_iterable = self.take_n(1).single_or()

    @staticmethod
    def first_index(
        iterable: Iterable[T], predicate: ElementPredicate[T]
    ) -> int | CRU_NOT_FOUND:
        """
        partial
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                return index

    @staticmethod
    def take_indices(
        iterable: Iterable[T], predicate: ElementPredicate[T]
    ) -> Iterable[int]:
        """
        complete
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                yield index

    @staticmethod
    def flatten(
        o,
        max_depth=-1,
        is_leave: ElementPredicate | None = None,
        get_children: OptionalElementTransformer = None,
    ) -> Iterable:
        """
        complete
        """
        if is_leave is None:
            is_leave = lambda v: not isinstance(v, Iterable)
        if get_children is None:
            get_children = lambda v: v
        return CruIterableWrapper._flatten_with_func(
            o, max_depth, is_leave, get_children
        )

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

    def drop_all(self) -> CruIterableWrapper:
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
        if len(f) == 0:
            return
        for v in iterable:
            for f_ in f:
                if f_ is not None:
                    f_(v)

    @staticmethod
    def make(v: CanBeList[T], /, none_to_empty_list: bool = True) -> list[T]:
        if v is None and none_to_empty_list:
            return []
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
    def transform(
        iterable: Iterable[T], *transformers: OptionalElementTransformer
    ) -> Iterable:
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
        return range(n)._god_yield(
            iterable, lambda v, i: _yield(v) if i < n else _return()
        )

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
    def first_index(
        iterable: Iterable[T], predicate: ElementPredicate[T]
    ) -> int | CRU_NOT_FOUND:
        """
        partial
        """
        for index, element in enumerate(iterable):
            if predicate(element):
                return index

    @staticmethod
    def take_indices(
        iterable: Iterable[T], predicate: ElementPredicate[T]
    ) -> Iterable[int]:
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
        if len(f) == 0:
            return
        for v in iterable:
            for f_ in f:
                if f_ is not None:
                    f_(v)

    @staticmethod
    def make(v: CanBeList[T], /, none_to_empty_list: bool = True) -> list[T]:
        if v is None and none_to_empty_list:
            return []
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

    def transform_if(
        self, f: OptionalElementTransformer, p: ElementPredicate[T]
    ) -> "CruList"[Any]:
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

    def transform_if(
        self, f: OptionalElementTransformer, p: ElementPredicate[T]
    ) -> "CruInplaceList"[Any]:
        return self.reset(super().transform_if(f, p))

    def remove_by_indices(self, *index: int) -> "CruInplaceList"[T]:
        return self.reset(super().remove_by_indices(*index))

    def remove_all_if(self, p: ElementPredicate[T]) -> "CruInplaceList"[T]:
        return self.reset(super().remove_all_if(p))

    def remove_all_value(self, *r: Any) -> "CruInplaceList"[T]:
        return self.reset(super().remove_all_value(*r))

    def replace_all_value(
        self, old_value: Any, new_value: R
    ) -> "CruInplaceList"[T | R]:
        return self.reset(super().replace_all_value(old_value, new_value))

    @staticmethod
    def make(l: CanBeList[T]) -> "CruInplaceList"[T]:
        return CruInplaceList(ListOperations.make(l))


K = TypeVar("K")


class CruUniqueKeyInplaceList(Generic[T, K]):
    KeyGetter = Callable[[T], K]

    def __init__(
        self, get_key: KeyGetter, *, before_add: Callable[[T], T] | None = None
    ):
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
        if i is CRU_NOT_FOUND:
            return False
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
