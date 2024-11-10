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
    cast,
)

from ._cru import CRU
from ._const import CruPlaceholder

_P = ParamSpec("_P")
_T = TypeVar("_T")


class CruRawFunctions:
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


CruArgsChainableCallable: TypeAlias = Callable[..., Iterable[Any]]
CruKwargsChainableCallable: TypeAlias = Callable[..., Iterable[tuple[str, Any]]]
CruChainableCallable: TypeAlias = Callable[
    ..., tuple[Iterable[Any], Iterable[tuple[str, Any]]]
]


class CruFunctionChainMode(Flag):
    ARGS = auto()
    KWARGS = auto()
    BOTH = ARGS | KWARGS


class CruFunctionMeta:
    @staticmethod
    def bind(func: Callable[..., _T], *bind_args, **bind_kwargs) -> Callable[..., _T]:
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

    @staticmethod
    def chain_with_args(
        funcs: Iterable[CruArgsChainableCallable], *bind_args, **bind_kwargs
    ) -> CruArgsChainableCallable:
        def chained_func(*args):
            for func in funcs:
                args = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(*args)
            return args

        return chained_func

    @staticmethod
    def chain_with_kwargs(
        funcs: Iterable[CruKwargsChainableCallable], *bind_args, **bind_kwargs
    ) -> CruKwargsChainableCallable:
        def chained_func(**kwargs):
            for func in funcs:
                kwargs = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(**kwargs)
            return kwargs

        return chained_func

    @staticmethod
    def chain_with_both(
        funcs: Iterable[CruChainableCallable], *bind_args, **bind_kwargs
    ) -> CruChainableCallable:
        def chained_func(*args, **kwargs):
            for func in funcs:
                args, kwargs = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(
                    *args, **kwargs
                )
            return args, kwargs

        return chained_func

    @staticmethod
    def chain(
        mode: CruFunctionChainMode,
        funcs: Iterable[
            CruArgsChainableCallable | CruKwargsChainableCallable | CruChainableCallable
        ],
        *bind_args,
        **bind_kwargs,
    ) -> CruArgsChainableCallable | CruKwargsChainableCallable | CruChainableCallable:
        if mode == CruFunctionChainMode.ARGS:
            return CruFunctionMeta.chain_with_args(
                cast(Iterable[CruArgsChainableCallable], funcs),
                *bind_args,
                **bind_kwargs,
            )
        elif mode == CruFunctionChainMode.KWARGS:
            return CruFunctionMeta.chain_with_kwargs(
                cast(Iterable[CruKwargsChainableCallable], funcs),
                *bind_args,
                **bind_kwargs,
            )
        elif mode == CruFunctionChainMode.BOTH:
            return CruFunctionMeta.chain_with_both(
                cast(Iterable[CruChainableCallable], funcs), *bind_args, **bind_kwargs
            )


# Advanced Function Wrapper
class CruFunction(Generic[_P, _T]):

    def __init__(self, f: Callable[_P, _T]):
        self._f = f

    @property
    def f(self) -> Callable[_P, _T]:
        return self._f

    @property
    def func(self) -> Callable[_P, _T]:
        return self.f

    def bind(self, *bind_args, **bind_kwargs) -> CruFunction[..., _T]:
        self._f = CruFunctionMeta.bind(self._f, *bind_args, **bind_kwargs)
        return self

    def _iter_with_self(
        self, funcs: Iterable[Callable[..., Any]]
    ) -> Iterable[Callable[..., Any]]:
        yield self
        yield from funcs

    @staticmethod
    def chain_with_args(
        self,
        funcs: Iterable[CruArgsChainableCallable],
        *bind_args,
        **bind_kwargs,
    ) -> CruArgsChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_args(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain_with_kwargs(
        self, funcs: Iterable[CruKwargsChainableCallable], *bind_args, **bind_kwargs
    ) -> CruKwargsChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_kwargs(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain_with_both(
        self, funcs: Iterable[CruChainableCallable], *bind_args, **bind_kwargs
    ) -> CruChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_both(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain(
        self,
        mode: CruFunctionChainMode,
        funcs: Iterable[
            CruArgsChainableCallable | CruKwargsChainableCallable | CruChainableCallable
        ],
        *bind_args,
        **bind_kwargs,
    ) -> CruArgsChainableCallable | CruKwargsChainableCallable | CruChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain(
                mode, self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self._f(*args, **kwargs)

    @staticmethod
    def make_chain(
        mode: CruFunctionChainMode,
        funcs: Iterable[
            CruArgsChainableCallable | CruKwargsChainableCallable | CruChainableCallable
        ],
        *bind_args,
        **bind_kwargs,
    ) -> CruFunction:
        return CruFunction(
            CruFunctionMeta.chain(mode, funcs, *bind_args, **bind_kwargs)
        )


class CruWrappedFunctions:
    none = CruFunction(CruRawFunctions.none)
    true = CruFunction(CruRawFunctions.true)
    false = CruFunction(CruRawFunctions.false)
    identity = CruFunction(CruRawFunctions.identity)
    only_you = CruFunction(CruRawFunctions.only_you)
    equal = CruFunction(CruRawFunctions.equal)
    not_equal = CruFunction(CruRawFunctions.not_equal)
    not_ = CruFunction(CruRawFunctions.not_)


class CruFunctionGenerators:
    @staticmethod
    def make_isinstance_of_types(*types: type) -> Callable:
        return CruFunction(lambda v: type(v) in types)


CRU.add_objects(
    CruRawFunctions,
    CruFunctionMeta,
    CruFunction,
    CruWrappedFunctions,
    CruFunctionGenerators,
)
