from __future__ import annotations

from collections.abc import Callable
from enum import Flag, auto
from typing import (
    Any,
    Generic,
    Iterable,
    Literal,
    ParamSpec,
    TypeAlias,
    TypeVar,
)


from ._cru import CRU
from ._const import CruPlaceholder

_P = ParamSpec("_P")
_P1 = ParamSpec("_P1")
_T = TypeVar("_T")


class _Dec:
    @staticmethod
    def wrap(
        origin: Callable[_P, Callable[_P1, _T]]
    ) -> Callable[_P, _Wrapper[_P1, _T]]:
        def _wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _Wrapper[_P1, _T]:
            return _Wrapper(origin(*args, **kwargs))

        return _wrapped


class _RawBase:
    @staticmethod
    def none(*_v, **_kwargs) -> None:
        return None

    @staticmethod
    def true(*_v, **_kwargs) -> Literal[True]:
        return True

    @staticmethod
    def false(*_v, **_kwargs) -> Literal[False]:
        return False

    @staticmethod
    def identity(v: _T) -> _T:
        return v

    @staticmethod
    def only_you(v: _T, *_v, **_kwargs) -> _T:
        return v

    @staticmethod
    def equal(a: Any, b: Any) -> bool:
        return a == b

    @staticmethod
    def not_equal(a: Any, b: Any) -> bool:
        return a != b

    @staticmethod
    def not_(v: Any) -> Any:
        return not v


class _Wrapper(Generic[_P, _T]):
    def __init__(self, f: Callable[_P, _T]):
        self._f = f

    @property
    def me(self) -> Callable[_P, _T]:
        return self._f

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self._f(*args, **kwargs)

    @_Dec.wrap
    def bind(self, *bind_args, **bind_kwargs) -> Callable[..., _T]:
        func = self.me

        def bound_func(*args, **kwargs):
            popped = 0
            real_args = []
            for arg in bind_args:
                if CruPlaceholder.check(arg):
                    real_args.append(args[popped])
                    popped += 1
                else:
                    real_args.append(arg)
            real_args.extend(args[popped:])
            return func(*real_args, **(bind_kwargs | kwargs))

        return bound_func

    class ChainMode(Flag):
        ARGS = auto()
        KWARGS = auto()
        BOTH = ARGS | KWARGS

    ArgsChainableCallable: TypeAlias = Callable[..., Iterable[Any]]
    KwargsChainableCallable: TypeAlias = Callable[..., Iterable[tuple[str, Any]]]
    ChainableCallable: TypeAlias = Callable[
        ..., tuple[Iterable[Any], Iterable[tuple[str, Any]]]
    ]

    @_Dec.wrap
    def chain_with_args(
        self, funcs: Iterable[ArgsChainableCallable], *bind_args, **bind_kwargs
    ) -> ArgsChainableCallable:
        def chained_func(*args):
            args = self.bind(*bind_args, **bind_kwargs)(*args)

            for func in funcs:
                args = _Wrapper(func).bind(*bind_args, **bind_kwargs)(*args)
            return args

        return chained_func

    @_Dec.wrap
    def chain_with_kwargs(
        self, funcs: Iterable[KwargsChainableCallable], *bind_args, **bind_kwargs
    ) -> KwargsChainableCallable:
        def chained_func(**kwargs):
            kwargs = self.bind(*bind_args, **bind_kwargs)(**kwargs)
            for func in funcs:
                kwargs = _Wrapper(func).bind(func, *bind_args, **bind_kwargs)(**kwargs)
            return kwargs

        return chained_func

    @_Dec.wrap
    def chain_with_both(
        self, funcs: Iterable[ChainableCallable], *bind_args, **bind_kwargs
    ) -> ChainableCallable:
        def chained_func(*args, **kwargs):
            for func in funcs:
                args, kwargs = _Wrapper(func).bind(func, *bind_args, **bind_kwargs)(
                    *args, **kwargs
                )
            return args, kwargs

        return chained_func


class _Base:
    none = _Wrapper(_RawBase.none)
    true = _Wrapper(_RawBase.true)
    false = _Wrapper(_RawBase.false)
    identity = _Wrapper(_RawBase.identity)
    only_you = _Wrapper(_RawBase.only_you)
    equal = _Wrapper(_RawBase.equal)
    not_equal = _Wrapper(_RawBase.not_equal)
    not_ = _Wrapper(_RawBase.not_)


class _Creators:
    @staticmethod
    def make_isinstance_of_types(*types: type) -> Callable:
        return _Wrapper(lambda v: type(v) in types)


class CruFunction:
    RawBase = _RawBase
    Base = _Base
    Creators = _Creators
    Wrapper = _Wrapper
    Decorators = _Dec


CRU.add_objects(CruFunction)
