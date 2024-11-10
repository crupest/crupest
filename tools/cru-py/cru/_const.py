from enum import Enum, auto
from typing import Self, TypeGuard, TypeVar

from ._base import CRU

_T = TypeVar("_T")


class CruConstantBase(Enum):
    @classmethod
    def check(cls, v: _T | Self) -> TypeGuard[Self]:
        return isinstance(v, cls)

    @classmethod
    def check_not(cls, v: _T | Self) -> TypeGuard[_T]:
        return not cls.check(v)

    @classmethod
    def value(cls) -> Self:
        return cls.VALUE  # type: ignore


class CruNotFound(CruConstantBase):
    VALUE = auto()


class CruUseDefault(CruConstantBase):
    VALUE = auto()


class CruDontChange(CruConstantBase):
    VALUE = auto()


class CruNoValue(CruConstantBase):
    VALUE = auto()


class CruPlaceholder(CruConstantBase):
    VALUE = auto()


CRU.add_objects(
    CruNotFound,
    CruUseDefault,
    CruDontChange,
    CruNoValue,
    CruPlaceholder,
)
