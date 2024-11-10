from __future__ import annotations

from collections.abc import Callable
from typing import (
    Concatenate,
    Generic,
    ParamSpec,
    TypeVar,
    cast,
)

from ._cru import CRU

_P = ParamSpec("_P")
_T = TypeVar("_T")
_O = TypeVar("_O")
_R = TypeVar("_R")


class CruDecorator:

    class ConvertResult(Generic[_T, _O]):
        def __init__(
            self,
            converter: Callable[[_T], _O],
        ) -> None:
            self.converter = converter

        def __call__(self, origin: Callable[_P, _T]) -> Callable[_P, _O]:
            converter = self.converter

            def real_impl(*args: _P.args, **kwargs: _P.kwargs) -> _O:
                return converter(origin(*args, **kwargs))

            return real_impl

    class ImplementedBy(Generic[_T, _O, _P, _R]):
        def __init__(
            self,
            impl: Callable[Concatenate[_O, _P], _R],
            converter: Callable[[_T], _O],
        ) -> None:
            self.impl = impl
            self.converter = converter

        def __call__(
            self, _origin: Callable[[_T], None]
        ) -> Callable[Concatenate[_T, _P], _R]:
            converter = self.converter
            impl = self.impl

            def real_impl(_self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                return cast(Callable[Concatenate[_O, _P], _R], impl)(
                    converter(_self), *args, **kwargs
                )

            return real_impl

        @staticmethod
        def create_factory(converter: Callable[[_T], _O]) -> Callable[
            [Callable[Concatenate[_O, _P], _R]],
            CruDecorator.ImplementedBy[_T, _O, _P, _R],
        ]:
            def create(
                m: Callable[Concatenate[_O, _P], _R],
            ) -> CruDecorator.ImplementedBy[_T, _O, _P, _R]:
                return CruDecorator.ImplementedBy(m, converter)

            return create

    class ImplementedByNoSelf(Generic[_P, _R]):
        def __init__(self, impl: Callable[_P, _R]) -> None:
            self.impl = impl

        def __call__(
            self, _origin: Callable[[_T], None]
        ) -> Callable[Concatenate[_T, _P], _R]:
            impl = self.impl

            def real_impl(_self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                return cast(Callable[_P, _R], impl)(*args, **kwargs)

            return real_impl

        @staticmethod
        def create_factory() -> (
            Callable[[Callable[_P, _R]], CruDecorator.ImplementedByNoSelf[_P, _R]]
        ):
            def create(
                m: Callable[_P, _R],
            ) -> CruDecorator.ImplementedByNoSelf[_P, _R]:
                return CruDecorator.ImplementedByNoSelf(m)

            return create


CRU.add_objects(CruDecorator)
