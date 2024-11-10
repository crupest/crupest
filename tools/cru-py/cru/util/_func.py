from collections.abc import Callable, Iterable
from typing import TypeVar, Any, ParamSpec

from ._list import ListOperations, CruList

T = TypeVar("T")
R = TypeVar("R")
R1 = TypeVar("R1")
P = ParamSpec("P")
P1 = ParamSpec("P1")


class _Placeholder:
    pass


PLACEHOLDER = _Placeholder()


class RawFunctions:
    @staticmethod
    def ignore(*_v, **_kwargs) -> None:
        return None

    @staticmethod
    def true_(*_v, **_kwargs) -> True:
        return True

    @staticmethod
    def false_(*_v, **_kwargs) -> False:
        return False

    @staticmethod
    def i_dont_care(r: T, *_v, **_kwargs) -> T:
        return r

    @staticmethod
    def identity(v: T) -> T:
        return v

    @staticmethod
    def equal(a: Any, b: Any) -> bool:
        return a == b

    @staticmethod
    def not_equal(a: Any, b: Any) -> bool:
        return a != b

    @staticmethod
    def not_(v):
        return not v


class MetaFunction:
    @staticmethod
    def bind(f: Callable[P, R], *bind_args, **bind_kwargs) -> Callable[P1, R1]:
        def bound(*args, **kwargs):
            popped = 0
            real_args = []
            for a in bind_args:
                if isinstance(a, _Placeholder):
                    real_args.append(args[popped])
                    popped += 1
                else:
                    real_args.append(a)
            real_args.extend(args[popped:])
            return f(*real_args, **(bind_kwargs | kwargs))

        return bound

    @staticmethod
    def chain(*fs: Callable) -> Callable:
        if len(fs) == 0:
            raise ValueError("At least one function is required!")
        rf = fs[0]
        for f in fs[1:]:
            def n(*args, **kwargs):
                r = rf(*args, **kwargs)
                r = r if isinstance(r, tuple) else (r,)
                return f(*r)

            rf = n
        return rf

    @staticmethod
    def chain_single(f: Callable[P, R], f1: Callable[P1, R1], *bind_args, **bind_kwargs) -> \
            Callable[
                P, R1]:
        return MetaFunction.chain(f, MetaFunction.bind(f1, *bind_args, **bind_kwargs))

    convert_r = chain_single

    @staticmethod
    def neg(f: Callable[P, bool]) -> Callable[P, bool]:
        return MetaFunction.convert_r(f, RawFunctions.not_)


# Advanced Function Wrapper
class CruFunction:
    def __init__(self, f):
        self._f = f

    @property
    def f(self) -> Callable:
        return self._f

    def bind(self, *bind_args, **bind_kwargs) -> "CruFunction":
        self._f = MetaFunction.bind(self._f, *bind_args, **bind_kwargs)
        return self

    def chain(self, *fs: Callable) -> "CruFunction":
        self._f = MetaFunction.chain(self._f, *fs)
        return self

    def chain_single(self, f: Callable[P, R], f1: Callable[P1, R1], *bind_args,
                     **bind_kwargs) -> "CruFunction":
        self._f = MetaFunction.chain_single(self._f, f, f1, *bind_args, **bind_kwargs)
        return self

    def convert_r(self, f: Callable[P, R], f1: Callable[P1, R1], *bind_args,
                  **bind_kwargs) -> "CruFunction":
        self._f = MetaFunction.convert_r(self._f, f, f1, *bind_args, **bind_kwargs)
        return self

    def neg(self) -> "CruFunction":
        self._f = MetaFunction.neg(self._f)
        return self

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)

    def list_transform(self, l: Iterable[T]) -> CruList[T]:
        return CruList(l).transform(self)

    def list_all(self, l: Iterable[T]) -> bool:
        return ListOperations.all(l, self)

    def list_any(self, l: Iterable[T]) -> bool:
        return ListOperations.any(l, self)

    def list_remove_all_if(self, l: Iterable[T]) -> CruList[T]:
        return CruList(ListOperations.remove_all_if(l, self))


class WrappedFunctions:
    identity = CruFunction(RawFunctions.identity)
    ignore = CruFunction(RawFunctions.ignore)
    equal = CruFunction(RawFunctions.equal)
    not_equal = CruFunction(RawFunctions.not_equal)
    not_ = CruFunction(RawFunctions.not_)
