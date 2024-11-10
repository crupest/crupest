from collections.abc import Callable
from typing import TypeVar, Any, ParamSpec

from ._const import CRU_PLACEHOLDER

T = TypeVar("T")
R = TypeVar("R")
R1 = TypeVar("R1")
P = ParamSpec("P")
P1 = ParamSpec("P1")


class RawFunctions:
    @staticmethod
    def none(*_v, **_kwargs) -> None:
        return None

    @staticmethod
    def true(*_v, **_kwargs) -> True:
        return True

    @staticmethod
    def false(*_v, **_kwargs) -> False:
        return False

    @staticmethod
    def identity(v: T) -> T:
        return v

    @staticmethod
    def only_you(r: T, *_v, **_kwargs) -> T:
        return r

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
                if a is CRU_PLACEHOLDER:
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

    @staticmethod
    def make_chain(*fs: Callable) -> Callable[P, R1]:
        return CruFunction(MetaFunction.chain(*fs))


class WrappedFunctions:
    none = CruFunction(RawFunctions.none)
    true = CruFunction(RawFunctions.true)
    false = CruFunction(RawFunctions.false)
    identity = CruFunction(RawFunctions.identity)
    only_you = CruFunction(RawFunctions.only_you)
    equal = CruFunction(RawFunctions.equal)
    not_equal = CruFunction(RawFunctions.not_equal)
    not_ = CruFunction(RawFunctions.not_)
