from __future__ import annotations

from collections.abc import Iterable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import (
    Concatenate,
    Generator,
    Iterator,
    Literal,
    Self,
    TypeAlias,
    TypeVar,
    ParamSpec,
    Any,
    Generic,
    cast,
    overload,
)

from ._cru import CRU
from ._meta import CruDecCreators
from ._const import CruNotFound

_P = ParamSpec("_P")
_T = TypeVar("_T")
_O = TypeVar("_O")
_V = TypeVar("_V")
_R = TypeVar("_R")

CanBeList: TypeAlias = Iterable[_T] | _T | None

ElementOperation: TypeAlias = Callable[[_T], Any]
ElementPredicate: TypeAlias = Callable[[_T], bool]
AnyElementPredicate: TypeAlias = ElementPredicate[Any]
ElementTransformer: TypeAlias = Callable[[_T], _O]
SelfElementTransformer: TypeAlias = ElementTransformer[_T, _T]
AnyElementTransformer: TypeAlias = ElementTransformer[Any, Any]


class _StepActionKind(Enum):
    SKIP = 0
    PUSH = 1
    STOP = 2
    AGGREGATE = 3


@dataclass
class _StepAction(Generic[_V, _R]):
    value: Iterable[Self] | _V | _R | None
    kind: _StepActionKind

    @property
    def push_value(self) -> _V:
        assert self.kind == _StepActionKind.PUSH
        return cast(_V, self.value)

    @property
    def stop_value(self) -> _R:
        assert self.kind == _StepActionKind.STOP
        return cast(_R, self.value)

    @staticmethod
    def skip() -> _StepAction[_V, _R]:
        return _StepAction(None, _StepActionKind.SKIP)

    @staticmethod
    def push(value: _V | None) -> _StepAction[_V, _R]:
        return _StepAction(value, _StepActionKind.PUSH)

    @staticmethod
    def stop(value: _R | None = None) -> _StepAction[_V, _R]:
        return _StepAction(value, _StepActionKind.STOP)

    @staticmethod
    def aggregate(*results: _StepAction[_V, _R]) -> _StepAction[_V, _R]:
        return _StepAction(results, _StepActionKind.AGGREGATE)

    @staticmethod
    def push_last(value: _V | None) -> _StepAction[_V, _R]:
        return _StepAction.aggregate(_StepAction.push(value), _StepAction.stop())

    def flatten(self) -> Iterable[Self]:
        return CruIterableMeta.flatten(
            self,
            is_leave=lambda r: r.kind != _StepActionKind.AGGREGATE,
            get_children=lambda r: cast(Iterable[Self], r.value),
        )


_GeneralStepAction: TypeAlias = _StepAction[_V, _R] | _V | _R | None
_IterateOperation = Callable[[_T, int], _GeneralStepAction[_V, _R]]
_IteratePreHook = Callable[[Iterable[_T]], _GeneralStepAction[_V, _R]]
_IteratePostHook = Callable[[int], _GeneralStepAction[_V, _R]]


class CruIterableMeta:
    class Generic:
        StepActionKind = _StepActionKind
        StepAction = _StepAction
        GeneralStepAction = _GeneralStepAction
        IterateOperation = _IterateOperation
        IteratePreHook = _IteratePreHook
        IteratePostHook = _IteratePostHook

        class Results:
            @staticmethod
            def true(_) -> Literal[True]:
                return True

            @staticmethod
            def false(_) -> Literal[False]:
                return False

            @staticmethod
            def not_found(_) -> Literal[CruNotFound.VALUE]:
                return CruNotFound.VALUE

        @staticmethod
        def _non_result_to_push(value: Any) -> _StepAction[_V, _R]:
            return _StepAction.push(value)

        @staticmethod
        def _non_result_to_stop(value: Any) -> _StepAction[_V, _R]:
            return _StepAction.stop(value)

        @staticmethod
        def _none_hook(_: Any) -> _StepAction[_V, _R]:
            return _StepAction.skip()

        def iterate(
            iterable: Iterable[_T],
            operation: _IterateOperation[_T, _V, _R],
            fallback_return: _R,
            pre_iterate: _IteratePreHook[_T, _V, _R],
            post_iterate: _IteratePostHook[_V, _R],
            convert_value_result: Callable[[_V | _R | None], _StepAction[_V, _R]],
        ) -> Generator[_V, None, _R]:
            pre_result = pre_iterate(iterable)
            if not isinstance(pre_result, _StepAction):
                real_pre_result = convert_value_result(pre_result)
            for r in real_pre_result.flatten():
                if r.kind == _StepActionKind.STOP:
                    return r.stop_value
                elif r.kind == _StepActionKind.PUSH:
                    yield r.push_value
                else:
                    assert r.kind == _StepActionKind.SKIP

            for index, element in enumerate(iterable):
                result = operation(element, index)
                if not isinstance(result, _StepAction):
                    real_result = convert_value_result(result)
                for r in real_result.flatten():
                    if r.kind == _StepActionKind.STOP:
                        return r.stop_value
                    elif r.kind == _StepActionKind.PUSH:
                        yield r.push_value
                    else:
                        assert r.kind == _StepActionKind.SKIP
                        continue

            post_result = post_iterate(index + 1)
            if not isinstance(post_result, _StepAction):
                real_post_result = convert_value_result(post_result)
            for r in real_post_result.flatten():
                if r.kind == _StepActionKind.STOP:
                    return r.stop_value
                elif r.kind == _StepActionKind.PUSH:
                    yield r.push_value
                else:
                    assert r.kind == _StepActionKind.SKIP

            return fallback_return

        def create_new(
            iterable: Iterable[_T],
            operation: _IterateOperation[_T, _V, _R],
            fallback_return: _R,
            /,
            pre_iterate: _IteratePreHook[_T, _V, _R] | None = None,
            post_iterate: _IteratePostHook[_V, _R] | None = None,
        ) -> Generator[_V, None, _R]:
            return CruIterableMeta.Generic.iterate(
                iterable,
                operation,
                fallback_return,
                pre_iterate or CruIterableMeta.Generic._none_hook,
                post_iterate or CruIterableMeta.Generic._none_hook,
                CruIterableMeta.Generic._non_result_to_push,
            )

        def get_result(
            iterable: Iterable[_T],
            operation: _IterateOperation[_T, _V, _R],
            fallback_return: _R,
            /,
            pre_iterate: _IteratePreHook[_T, _V, _R] | None = None,
            post_iterate: _IteratePostHook[_V, _R] | None = None,
        ) -> _R:
            try:
                for _ in CruIterableMeta.Generic.iterate(
                    iterable,
                    operation,
                    fallback_return,
                    pre_iterate or CruIterableMeta.Generic._none_hook,
                    post_iterate or CruIterableMeta.Generic._none_hook,
                    CruIterableMeta.Generic._non_result_to_stop,
                ):
                    pass
            except StopIteration as stop:
                return stop.value
            raise RuntimeError("Should not reach here")

    class Creators:
        @staticmethod
        def empty() -> Iterable[_T]:
            return iter([])

        @staticmethod
        def range(*args) -> Iterable[int]:
            return iter(range(*args))

        @staticmethod
        def unite(*args: _O) -> Iterable[_O]:
            return iter(args)

        @staticmethod
        def concat(*iterables: Iterable[_T]) -> Iterable[_T]:
            for iterable in iterables:
                yield from iterable

    @staticmethod
    def with_count(c: Callable[Concatenate[int, _P], _O]) -> Callable[_P, _O]:
        count = 0

        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _O:
            nonlocal count
            r = c(count, *args, **kwargs)
            count += 1
            return r

        return wrapper

    @staticmethod
    def to_set(iterable: Iterable[_T], discard: Iterable[Any]) -> set[_T]:
        return set(iterable) - set(discard)

    @staticmethod
    def to_list(iterable: Iterable[_T], discard: Iterable[Any]) -> list[_T]:
        return [v for v in iterable if v not in set(discard)]

    @staticmethod
    def all(iterable: Iterable[_T], predicate: ElementPredicate[_T]) -> bool:
        for value in iterable:
            if not predicate(value):
                return False
        return True

    @staticmethod
    def any(iterable: Iterable[_T], predicate: ElementPredicate[_T]) -> bool:
        for value in iterable:
            if predicate(value):
                return True
        return False

    @staticmethod
    def foreach(iterable: Iterable[_T], operation: ElementOperation[_T]) -> None:
        for value in iterable:
            operation(value)

    @staticmethod
    def transform(
        iterable: Iterable[_T], transformer: ElementTransformer[_T, _O]
    ) -> Iterable[_O]:
        for value in iterable:
            yield transformer(value)

    @staticmethod
    def filter(iterable: Iterable[_T], predicate: ElementPredicate[_T]) -> Iterable[_T]:
        for value in iterable:
            if predicate(value):
                yield value

    @staticmethod
    def continue_if(
        iterable: Iterable[_T], predicate: ElementPredicate[_T]
    ) -> Iterable[_T]:
        for value in iterable:
            yield value
            if not predicate(value):
                break

    @staticmethod
    def first_n(iterable: Iterable[_T], max_count: int) -> Iterable[_T]:
        if max_count < 0:
            raise ValueError("max_count must be 0 or positive.")
        if max_count == 0:
            return CruIterableMeta.Creators.empty()
        return CruIterableMeta.continue_if(
            iterable, _with_count(lambda i, _: i < max_count - 1)
        )

    @staticmethod
    def drop_n(iterable: Iterable[_T], n: int) -> Iterable[_T]:
        if n < 0:
            raise ValueError("n must be 0 or positive.")
        if n == 0:
            return iterable
        return CruIterableMeta.filter(iterable, _with_count(lambda i, _: i < n))

    @staticmethod
    def single_or(
        iterable: Iterable[_T], fallback: _O | CruNotFound | None = CruNotFound.VALUE
    ) -> _T | _O | Any | CruNotFound:
        first_2 = CruIterableMeta.first_n(iterable, 2)
        has_value = False
        value = None
        for element in first_2:
            if has_value:
                raise ValueError("More than one value found.")
            has_value = True
            value = element
        if has_value:
            return value
        else:
            return fallback

    @staticmethod
    def _is_not_iterable(o: Any) -> bool:
        return not isinstance(o, Iterable)

    @staticmethod
    def _return_self(o):
        return o

    @staticmethod
    @overload
    def flatten(o: Iterable[_T], max_depth: int = -1) -> Iterable[_T]: ...

    @staticmethod
    @overload
    def flatten(
        o: _O,
        max_depth: int = -1,
        *,
        is_leave: ElementPredicate[_O],
        get_children: ElementTransformer[_O, Iterable[_O]],
    ) -> Iterable[_O]: ...

    @staticmethod
    def flatten(
        o: _O,
        max_depth: int = -1,
        *,
        is_leave: ElementPredicate[_O] = _is_not_iterable,
        get_children: ElementTransformer[_O, Iterable[_O]] = _return_self,
        _depth: int = 0,
    ) -> Iterable[Any]:
        if _depth == max_depth or is_leave(o):
            yield o
            return
        for child in get_children(o):
            yield from CruIterableMeta.flatten(
                child,
                max_depth,
                is_leave=is_leave,
                get_children=get_children,
                _depth=_depth + 1,
            )  # type: ignore


_with_count = CruIterableMeta.with_count


class CruIterableWrapper(Generic[_T]):
    Meta = CruIterableMeta

    class Dec:
        @staticmethod
        def _wrap(iterable: Iterable[_O]) -> CruIterableWrapper[_O]:
            return CruIterableWrapper(iterable)

        wrap = CruDecCreators.convert_result(_wrap)

        @staticmethod
        def _as_iterable(_self: CruIterableWrapper[_O]) -> CruIterableWrapper[_O]:
            return _self

        meta = CruDecCreators.create_implement_by(_as_iterable)
        meta_no_self = CruDecCreators.create_implement_by_no_self()

    def __init__(
        self,
        iterable: Iterable[_T],
    ) -> None:
        self._iterable = iterable

    def __iter__(self) -> Iterator[_T]:
        return self._iterable.__iter__()

    @property
    def me(self) -> Iterable[_T]:
        return self._iterable

    def replace_me(self, iterable: Iterable[_O]) -> CruIterableWrapper[_O]:
        return CruIterableWrapper(iterable)

    @Dec.wrap
    @Dec.meta_no_self(CruIterableMeta.Creators.empty)
    def replace_me_with_empty(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta_no_self(CruIterableMeta.Creators.range)
    def replace_me_with_range(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta_no_self(CruIterableMeta.Creators.unite)
    def replace_me_with_unite(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta_no_self(CruIterableMeta.Creators.concat)
    def replace_me_with_concat(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.to_set)
    def to_set(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.to_list)
    def to_list(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.all)
    def all(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.any)
    def any(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.foreach)
    def foreach(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta(CruIterableMeta.transform)
    def transform(self) -> None:
        pass

    map = transform

    @Dec.wrap
    @Dec.meta(CruIterableMeta.filter)
    def filter(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta(CruIterableMeta.continue_if)
    def continue_if(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta(CruIterableMeta.first_n)
    def first_n(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta(CruIterableMeta.drop_n)
    def drop_n(self) -> None:
        pass

    @Dec.wrap
    @Dec.meta(CruIterableMeta.flatten)
    def flatten(self) -> None:
        pass

    @Dec.meta(CruIterableMeta.single_or)
    def single_or(self) -> None:
        pass

    @Dec.wrap
    def select_by_indices(self, indices: Iterable[int]) -> Iterable[_T]:
        index_set = set(indices)
        max_index = max(index_set)
        return self.first_n(max_index + 1).filter(
            _with_count(lambda i, _: i in index_set)
        )

    @Dec.wrap
    def remove_values(self, values: Iterable[Any]) -> Iterable[_V]:
        value_set = set(values)
        return self.filter(lambda v: v not in value_set)

    @Dec.wrap
    def replace_values(
        self, old_values: Iterable[Any], new_value: _O
    ) -> Iterable[_V | _O]:
        value_set = set(old_values)
        return self.map(lambda v: new_value if v in value_set else v)


CRU.add_objects(CruIterableMeta, CruIterableWrapper)
