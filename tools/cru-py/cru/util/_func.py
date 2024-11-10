from collections.abc import Callable
from typing import TypeVar

from ._cru import CRU
from ._const import CRU_PLACEHOLDER

T = TypeVar("T")

_PLACEHOLDER = CRU_PLACEHOLDER

class CruRawFunctions:
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
    def only_you(v: T, *_v, **_kwargs) -> T:
        return v

    @staticmethod
    def equal(a, b) -> bool:
        return a == b

    @staticmethod
    def not_equal(a, b) -> bool:
        return a != b

    @staticmethod
    def not_(v):
        return not v


class CruFunctionMeta:
    @staticmethod
    def bind(func: Callable, *bind_args, **bind_kwargs) -> Callable:
        def bound_func(*args, **kwargs):
            popped = 0
            real_args = []
            for arg in bind_args:
                if arg is _PLACEHOLDER:
                    real_args.append(args[popped])
                    popped += 1
                else:
                    real_args.append(arg)
            real_args.extend(args[popped:])
            return func(*real_args, **(bind_kwargs | kwargs))

        return bound_func

    @staticmethod
    def chain(*funcs: Callable) -> Callable:
        if len(funcs) == 0:
            raise ValueError("At least one function is required!")

        final_func = funcs[0]
        for func in funcs[1:]:
            func_copy = func

            def chained_func(*args, **kwargs):
                results = final_func(*args, **kwargs)
                results = results if isinstance(results, tuple) else (results,)
                return func_copy(*results)

            final_func = chained_func

        return final_func


# Advanced Function Wrapper
class CruFunction:
    def __init__(self, f: Callable):
        self._f = f

    @property
    def f(self) -> Callable:
        return self._f

    @property
    def func(self) -> Callable:
        return self.f

    def bind(self, *bind_args, **bind_kwargs) -> "CruFunction":
        self._f = CruFunctionMeta.bind(self._f, *bind_args, **bind_kwargs)
        return self

    def chain(self, *funcs: Callable) -> "CruFunction":
        self._f = CruFunctionMeta.chain(self._f, *funcs)
        return self

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)

    @staticmethod
    def make_chain(base_func: Callable, *funcs: Callable) -> "CruFunction":
        return CruFunction(base_func).chain(*funcs)


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

CRU.add_objects(CruRawFunctions, CruFunctionMeta, CruFunction, CruWrappedFunctions, CruFunctionGenerators)
