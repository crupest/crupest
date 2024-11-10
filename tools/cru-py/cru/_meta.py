from collections.abc import Callable
from typing import Concatenate, Generic, ParamSpec, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")
_O = TypeVar("_O")
_R = TypeVar("_R")


class CruDecorator:

    class ImplementedBy(Generic[_O, _P, _R]):
        # TODO: Continue here tomorrow!
        def __init__(
            self, impl: Callable[Concatenate[_O, _P], _R], pass_self: bool
        ) -> None:
            self.impl = impl
            self.pass_self = pass_self

        def __call__(
            self, _origin: Callable[[_T], None]
        ) -> Callable[Concatenate[_T, _P], _R]:
            def real_impl(_self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                if self.pass_self:
                    return self.impl(_self, *args, **kwargs)
                else:
                    return self.impl(*args, **kwargs)

            return real_impl

    @staticmethod
    def convert_result(
        converter: Callable[[_T], _O]
    ) -> Callable[[Callable[_P, _T]], Callable[_P, _O]]:
        def dec(original: Callable[_P, _T]) -> Callable[_P, _O]:
            def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _O:
                return converter(original(*args, **kwargs))

            return wrapped

        return dec

    @staticmethod
    def create_implement_by(converter: Callable[[_T], _O]) -> Callable[
        [Callable[Concatenate[_O, _P], _R]],
        Callable[
            [Callable[[_T], None]],
            Callable[Concatenate[_T, _P], _R],
        ],
    ]:
        def implement_by(
            m: Callable[Concatenate[_O, _P], _R],
        ) -> Callable[
            [Callable[[_T], None]],
            Callable[Concatenate[_T, _P], _R],
        ]:
            def implementation(_self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                return m(converter(_self), *args, **kwargs)

            def decorator(_: Callable[[_T], None]) -> Callable[Concatenate[_T, _P], _R]:
                return implementation

            return decorator

        return implement_by

    @staticmethod
    def create_implement_by_no_self() -> Callable[
        [Callable[_P, _R]],
        Callable[
            [Callable[[_T], None]],
            Callable[Concatenate[_T, _P], _R],
        ],
    ]:
        def implement_by_no_self(
            m: Callable[_P, _R],
        ) -> Callable[
            [Callable[[_T], None]],
            Callable[Concatenate[_T, _P], _R],
        ]:
            def implementation(_self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _R:
                return m(*args, **kwargs)

            def decorator(_: Callable[[_T], None]) -> Callable[Concatenate[_T, _P], _R]:
                return implementation

            return decorator

        return implement_by_no_self


CRU.add
