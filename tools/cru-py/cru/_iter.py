from __future__ import annotations

from collections.abc import Iterable, Callable
from dataclasses import dataclass
from enum import Enum
from typing import (
    Concatenate,
    Generator,
    Iterator,
    Literal,
    Never,
    Self,
    TypeAlias,
    TypeVar,
    ParamSpec,
    Any,
    Generic,
    cast,
)

from ._base import CRU, cru_unreachable
from ._const import CruNotFound

_P = ParamSpec("_P")
_T = TypeVar("_T")
_O = TypeVar("_O")
_V = TypeVar("_V")
_R = TypeVar("_R")


class _Generic:
    class StepActionKind(Enum):
        SKIP = 0
        PUSH = 1
        STOP = 2
        AGGREGATE = 3

    @dataclass
    class StepAction(Generic[_V, _R]):
        value: Iterable[Self] | _V | _R | None
        kind: _Generic.StepActionKind

        @property
        def push_value(self) -> _V:
            assert self.kind == _Generic.StepActionKind.PUSH
            return cast(_V, self.value)

        @property
        def stop_value(self) -> _R:
            assert self.kind == _Generic.StepActionKind.STOP
            return cast(_R, self.value)

        @staticmethod
        def skip() -> _Generic.StepAction[_V, _R]:
            return _Generic.StepAction(None, _Generic.StepActionKind.SKIP)

        @staticmethod
        def push(value: _V | None) -> _Generic.StepAction[_V, _R]:
            return _Generic.StepAction(value, _Generic.StepActionKind.PUSH)

        @staticmethod
        def stop(value: _R | None = None) -> _Generic.StepAction[_V, _R]:
            return _Generic.StepAction(value, _Generic.StepActionKind.STOP)

        @staticmethod
        def aggregate(
            *results: _Generic.StepAction[_V, _R]
        ) -> _Generic.StepAction[_V, _R]:
            return _Generic.StepAction(results, _Generic.StepActionKind.AGGREGATE)

        @staticmethod
        def push_last(value: _V | None) -> _Generic.StepAction[_V, _R]:
            return _Generic.StepAction.aggregate(
                _Generic.StepAction.push(value), _Generic.StepAction.stop()
            )

        def flatten(self) -> Iterable[Self]:
            return _Generic.flatten(
                self,
                is_leave=lambda r: r.kind != _Generic.StepActionKind.AGGREGATE,
                get_children=lambda r: cast(Iterable[Self], r.value),
            )

    GeneralStepAction: TypeAlias = StepAction[_V, _R] | _V | _R | None
    IterateOperation: TypeAlias = Callable[[_T, int], GeneralStepAction[_V, _R]]
    IteratePreHook: TypeAlias = Callable[[Iterable[_T]], GeneralStepAction[_V, _R]]
    IteratePostHook: TypeAlias = Callable[[int], GeneralStepAction[_V, _R]]

    @staticmethod
    def _is_not_iterable(o: Any) -> bool:
        return not isinstance(o, Iterable)

    @staticmethod
    def _return_self(o):
        return o

    @staticmethod
    def iterable_flatten(
        maybe_iterable: Iterable[_T] | _T, max_depth: int = -1, *, _depth: int = 0
    ) -> Iterable[Iterable[_T] | _T]:
        if _depth == max_depth or not isinstance(maybe_iterable, Iterable):
            yield maybe_iterable
            return

        for child in maybe_iterable:
            yield from _Generic.iterable_flatten(
                child,
                max_depth,
                _depth=_depth + 1,
            )

    @staticmethod
    def flatten(
        o: _O,
        max_depth: int = -1,
        /,
        is_leave: _Wrapper.ElementPredicate[_O] = _is_not_iterable,
        get_children: _Wrapper.ElementTransformer[_O, Iterable[_O]] = _return_self,
        *,
        _depth: int = 0,
    ) -> Iterable[_O]:
        if _depth == max_depth or is_leave(o):
            yield o
            return
        for child in get_children(o):
            yield from _Generic.flatten(
                child,
                max_depth,
                is_leave,
                get_children,
                _depth=_depth + 1,
            )

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
    def _non_result_to_push(value: Any) -> StepAction[_V, _R]:
        return _Generic.StepAction.push(value)

    @staticmethod
    def _non_result_to_stop(value: Any) -> StepAction[_V, _R]:
        return _Generic.StepAction.stop(value)

    @staticmethod
    def _none_hook(_: Any) -> StepAction[_V, _R]:
        return _Generic.StepAction.skip()

    def iterate(
        iterable: Iterable[_T],
        operation: IterateOperation[_T, _V, _R],
        fallback_return: _R,
        pre_iterate: IteratePreHook[_T, _V, _R],
        post_iterate: IteratePostHook[_V, _R],
        convert_value_result: Callable[[_V | _R | None], StepAction[_V, _R]],
    ) -> Generator[_V, None, _R]:
        pre_result = pre_iterate(iterable)
        if not isinstance(pre_result, _Generic.StepAction):
            real_pre_result = convert_value_result(pre_result)
        for r in real_pre_result.flatten():
            if r.kind == _Generic.StepActionKind.STOP:
                return r.stop_value
            elif r.kind == _Generic.StepActionKind.PUSH:
                yield r.push_value
            else:
                assert r.kind == _Generic.StepActionKind.SKIP

        for index, element in enumerate(iterable):
            result = operation(element, index)
            if not isinstance(result, _Generic.StepAction):
                real_result = convert_value_result(result)
            for r in real_result.flatten():
                if r.kind == _Generic.StepActionKind.STOP:
                    return r.stop_value
                elif r.kind == _Generic.StepActionKind.PUSH:
                    yield r.push_value
                else:
                    assert r.kind == _Generic.StepActionKind.SKIP
                    continue

        post_result = post_iterate(index + 1)
        if not isinstance(post_result, _Generic.StepAction):
            real_post_result = convert_value_result(post_result)
        for r in real_post_result.flatten():
            if r.kind == _Generic.StepActionKind.STOP:
                return r.stop_value
            elif r.kind == _Generic.StepActionKind.PUSH:
                yield r.push_value
            else:
                assert r.kind == _Generic.StepActionKind.SKIP

        return fallback_return

    def create_new(
        iterable: Iterable[_T],
        operation: IterateOperation[_T, _V, _R],
        fallback_return: _R,
        /,
        pre_iterate: IteratePreHook[_T, _V, _R] | None = None,
        post_iterate: IteratePostHook[_V, _R] | None = None,
    ) -> Generator[_V, None, _R]:
        return _Generic.iterate(
            iterable,
            operation,
            fallback_return,
            pre_iterate or _Generic._none_hook,
            post_iterate or _Generic._none_hook,
            _Generic._non_result_to_push,
        )

    def get_result(
        iterable: Iterable[_T],
        operation: IterateOperation[_T, _V, _R],
        fallback_return: _R,
        /,
        pre_iterate: IteratePreHook[_T, _V, _R] | None = None,
        post_iterate: IteratePostHook[_V, _R] | None = None,
    ) -> _R:
        try:
            for _ in _Generic.iterate(
                iterable,
                operation,
                fallback_return,
                pre_iterate or _Generic._none_hook,
                post_iterate or _Generic._none_hook,
                _Generic._non_result_to_stop,
            ):
                pass
        except StopIteration as stop:
            return stop.value
        cru_unreachable()


class _Helper:
    @staticmethod
    def with_count(c: Callable[Concatenate[int, _P], _O]) -> Callable[_P, _O]:
        count = 0

        def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _O:
            nonlocal count
            r = c(count, *args, **kwargs)
            count += 1
            return r

        return wrapper


class _Creators:

    @staticmethod
    def empty(
        *,
        wrapper_type: type["_Wrapper[Never]"] | None = None,
        attr: dict[str, Any] | None = None,
    ) -> _Wrapper[Never]:
        wrapper_type = wrapper_type or _Wrapper
        return wrapper_type(iter([]), attr)

    @staticmethod
    def range(
        *args,
        wrapper_type: type["_Wrapper[int]"] | None = None,
        attr: dict[str, Any] | None = None,
    ) -> _Wrapper[int]:
        wrapper_type = wrapper_type or _Wrapper
        return wrapper_type(iter(range(*args)), attr)

    @staticmethod
    def unite(
        *args: _O,
        wrapper_type: type["_Wrapper[_O]"] | None = None,
        attr: dict[str, Any] | None = None,
    ) -> _Wrapper[_O]:
        wrapper_type = wrapper_type or _Wrapper
        return wrapper_type(iter(args), attr)

    @staticmethod
    def _concat(*iterables: Iterable[_T]) -> Iterable[_T]:
        for iterable in iterables:
            yield from iterable

    @staticmethod
    def concat(
        *iterables: Iterable[_T],
        wrapper_type: type["_Wrapper[_T]"] | None = None,
        attr: dict[str, Any] | None = None,
    ) -> _Wrapper[_T]:
        wrapper_type = wrapper_type or _Wrapper
        return wrapper_type(_Creators._concat(*iterables), attr)


class _Wrapper(Generic[_T]):
    ElementOperation: TypeAlias = Callable[[_V], Any]
    ElementPredicate: TypeAlias = Callable[[_V], bool]
    AnyElementPredicate: TypeAlias = ElementPredicate[Any]
    ElementTransformer: TypeAlias = Callable[[_V], _O]
    SelfElementTransformer: TypeAlias = ElementTransformer[_V, _V]
    AnyElementTransformer: TypeAlias = ElementTransformer[Any, Any]

    def __init__(
        self, iterable: Iterable[_T], attr: dict[str, Any] | None = None
    ) -> None:
        self._iterable = iterable
        self._attr = attr or {}

    def __iter__(self) -> Iterator[_T]:
        return self._iterable.__iter__()

    @property
    def me(self) -> Iterable[_T]:
        return self._iterable

    @property
    def my_attr(self) -> dict[str, Any]:
        return self._attr

    def create_with_me(self, iterable: Iterable[_O]) -> _Wrapper[_O]:
        return type(self)(iterable, self._attr)  # type: ignore

    @staticmethod
    def _wrap(
        f: Callable[Concatenate[_Wrapper[_T], _P], Iterable[_O]]
    ) -> Callable[Concatenate[_Wrapper[_T], _P], _Wrapper[_O]]:
        def _wrapped(
            self: _Wrapper[_T], *args: _P.args, **kwargs: _P.kwargs
        ) -> _Wrapper[_O]:
            return self.create_with_me(f(self, *args, **kwargs))

        return _wrapped

    @_wrap
    def replace_me(self, iterable: Iterable[_O]) -> Iterable[_O]:
        return iterable

    def replace_me_with_empty(self) -> _Wrapper[Never]:
        return _Creators.empty(wrapper_type=type(self), attr=self._attr)  # type: ignore

    def replace_me_with_range(self, *args) -> _Wrapper[int]:
        return _Creators.range(*args, attr=self._attr)

    def replace_me_with_unite(self, *args: _O) -> _Wrapper[_O]:
        return _Creators.unite(*args, attr=self._attr)

    def replace_me_with_concat(self, *iterables: Iterable[_T]) -> _Wrapper[_T]:
        return _Creators.concat(*iterables, attr=self._attr)

    def to_set(self, discard: Iterable[Any]) -> set[_T]:
        return set(self.me) - set(discard)

    def to_list(self, discard: Iterable[Any]) -> list[_T]:
        return [v for v in self.me if v not in set(discard)]

    def all(self, predicate: ElementPredicate[_T]) -> bool:
        for value in self.me:
            if not predicate(value):
                return False
        return True

    def any(self, predicate: ElementPredicate[_T]) -> bool:
        for value in self.me:
            if predicate(value):
                return True
        return False

    def foreach(self, operation: ElementOperation[_T]) -> None:
        for value in self.me:
            operation(value)

    @_wrap
    def transform(self, transformer: ElementTransformer[_T, _O]) -> Iterable[_O]:
        for value in self.me:
            yield transformer(value)

    map = transform

    @_wrap
    def filter(self, predicate: ElementPredicate[_T]) -> Iterable[_T]:
        for value in self.me:
            if predicate(value):
                yield value

    @_wrap
    def continue_if(self, predicate: ElementPredicate[_T]) -> Iterable[_T]:
        for value in self.me:
            yield value
            if not predicate(value):
                break

    def first_n(self, max_count: int) -> _Wrapper[_T]:
        if max_count < 0:
            raise ValueError("max_count must be 0 or positive.")
        if max_count == 0:
            return self.replace_me_with_empty()  # type: ignore
        return self.continue_if(_Helper.with_count(lambda i, _: i < max_count - 1))

    def drop_n(self, n: int) -> _Wrapper[_T]:
        if n < 0:
            raise ValueError("n must be 0 or positive.")
        if n == 0:
            return self
        return self.filter(_Helper.with_count(lambda i, _: i < n))

    def single_or(
        self, fallback: _O | CruNotFound | None = CruNotFound.VALUE
    ) -> _T | _O | Any | CruNotFound:
        first_2 = self.first_n(2)
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

    @_wrap
    def flatten(self) -> Iterable[_T | Iterable[_T]]:
        return _Generic.iterable_flatten(self.me)

    def select_by_indices(self, indices: Iterable[int]) -> _Wrapper[_T]:
        index_set = set(indices)
        max_index = max(index_set)
        return self.first_n(max_index + 1).filter(
            _Helper.with_count(lambda i, _: i in index_set)
        )

    def remove_values(self, values: Iterable[Any]) -> _Wrapper[_T]:
        value_set = set(values)
        return self.filter(lambda v: v not in value_set)

    def replace_values(
        self, old_values: Iterable[Any], new_value: _O
    ) -> Iterable[_T | _O]:
        value_set = set(old_values)
        return self.transform(lambda v: new_value if v in value_set else v)


class CruIterable:
    Generic: TypeAlias = _Generic
    Helper: TypeAlias = _Helper
    Creators: TypeAlias = _Creators
    Wrapper: TypeAlias = _Wrapper


CRU.add_objects(CruIterable, _Wrapper)
