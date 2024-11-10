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


_ArgsChainableCallable: TypeAlias = Callable[..., Iterable[Any]]
_KwargsChainableCallable: TypeAlias = Callable[..., Iterable[tuple[str, Any]]]
_ChainableCallable: TypeAlias = Callable[
    ..., tuple[Iterable[Any], Iterable[tuple[str, Any]]]
]


class CruFunctionMeta:
    class Base:
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

    class ChainMode(Flag):
        ARGS = auto()
        KWARGS = auto()
        BOTH = ARGS | KWARGS

    ArgsChainableCallable = _ArgsChainableCallable
    KwargsChainableCallable = _KwargsChainableCallable
    ChainableCallable = _ChainableCallable

    @staticmethod
    def chain_with_args(
        funcs: Iterable[_ArgsChainableCallable], *bind_args, **bind_kwargs
    ) -> _ArgsChainableCallable:
        def chained_func(*args):
            for func in funcs:
                args = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(*args)
            return args

        return chained_func

    @staticmethod
    def chain_with_kwargs(
        funcs: Iterable[_KwargsChainableCallable], *bind_args, **bind_kwargs
    ) -> _KwargsChainableCallable:
        def chained_func(**kwargs):
            for func in funcs:
                kwargs = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(**kwargs)
            return kwargs

        return chained_func

    @staticmethod
    def chain_with_both(
        funcs: Iterable[_ChainableCallable], *bind_args, **bind_kwargs
    ) -> _ChainableCallable:
        def chained_func(*args, **kwargs):
            for func in funcs:
                args, kwargs = CruFunctionMeta.bind(func, *bind_args, **bind_kwargs)(
                    *args, **kwargs
                )
            return args, kwargs

        return chained_func

    @staticmethod
    def chain(
        mode: ChainMode,
        funcs: Iterable[
            _ArgsChainableCallable | _KwargsChainableCallable | _ChainableCallable
        ],
        *bind_args,
        **bind_kwargs,
    ) -> _ArgsChainableCallable | _KwargsChainableCallable | _ChainableCallable:
        if mode == CruFunctionMeta.ChainMode.ARGS:
            return CruFunctionMeta.chain_with_args(
                cast(Iterable[_ArgsChainableCallable], funcs),
                *bind_args,
                **bind_kwargs,
            )
        elif mode == CruFunctionMeta.ChainMode.KWARGS:
            return CruFunctionMeta.chain_with_kwargs(
                cast(Iterable[_KwargsChainableCallable], funcs),
                *bind_args,
                **bind_kwargs,
            )
        elif mode == CruFunctionMeta.ChainMode.BOTH:
            return CruFunctionMeta.chain_with_both(
                cast(Iterable[_ChainableCallable], funcs), *bind_args, **bind_kwargs
            )


class CruFunction(Generic[_P, _T]):

    def __init__(self, f: Callable[_P, _T]):
        self._f = f

    @property
    def me(self) -> Callable[_P, _T]:
        return self._f

    def bind(self, *bind_args, **bind_kwargs) -> CruFunction[..., _T]:
        return CruFunction(CruFunctionMeta.bind(self._f, *bind_args, **bind_kwargs))

    def _iter_with_self(
        self, funcs: Iterable[Callable[..., Any]]
    ) -> Iterable[Callable[..., Any]]:
        yield self
        yield from funcs

    @staticmethod
    def chain_with_args(
        self,
        funcs: Iterable[_ArgsChainableCallable],
        *bind_args,
        **bind_kwargs,
    ) -> _ArgsChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_args(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain_with_kwargs(
        self, funcs: Iterable[_KwargsChainableCallable], *bind_args, **bind_kwargs
    ) -> _KwargsChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_kwargs(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain_with_both(
        self, funcs: Iterable[_ChainableCallable], *bind_args, **bind_kwargs
    ) -> _ChainableCallable:
        return CruFunction(
            CruFunctionMeta.chain_with_both(
                self._iter_with_self(funcs), *bind_args, **bind_kwargs
            )
        )

    def chain(
        self,
        mode: CruFunctionChainMode,
        funcs: Iterable[
            _ArgsChainableCallable | _KwargsChainableCallable | _ChainableCallable
        ],
        *bind_args,
        **bind_kwargs,
    ) -> _ArgsChainableCallable | _KwargsChainableCallable | _ChainableCallable:
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
            _ArgsChainableCallable | _KwargsChainableCallable | _ChainableCallable
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
