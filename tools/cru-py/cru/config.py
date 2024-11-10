from typing import TypeVar, Generic
import copy


from .list import CruUniqueKeyList
from ._error import CruInternalError
from .value import (
    CruValueTypeError,
    ValueGeneratorBase,
    ValueType,
)

_T = TypeVar("_T")


class ConfigItem(Generic[_T]):
    def __init__(
        self,
        name: str,
        description: str,
        value_type: ValueType[_T],
        value: _T | None,
        default_value: _T,
        *,
        value_generator: ValueGeneratorBase | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._value_type = value_type
        self._default_value = default_value
        self._value_generator = value_generator
        self._value = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def value_type(self) -> ValueType[_T]:
        return self._value_type

    @property
    def default_value(self) -> _T:
        return self._default_value

    @property
    def is_default(self) -> bool:
        return self._value is None

    @property
    def is_set(self) -> bool:
        return not self.is_default

    @property
    def value(self) -> _T:
        return self._value or self._default_value

    @property
    def value_generator(self) -> ValueGeneratorBase | None:
        return self._value_generator

    def set_value(self, v: _T | str, /, allow_convert_from_str=False):
        if allow_convert_from_str:
            self._value = self.value_type.check_value(v)
        else:
            self._value = self.value_type.check_value_or_try_convert_from_str(v)

    def generate_value(self) -> _T | None:
        if self.value_generator is None:
            return None
        v = self.generate_value()
        try:
            self.value_type.check_value(v)
            return v
        except CruValueTypeError as e:
            raise CruInternalError(
                "Config value generator returns invalid value."
            ) from e

    def copy(self) -> "ConfigItem":
        return ConfigItem(
            self.name,
            self.description,
            self.value_type,
            copy.deepcopy(self._value) if self._value is not None else None,
            copy.deepcopy(self._default_value),
            value_generator=self.value_generator,
        )


class Configuration(CruUniqueKeyList[ConfigItem, str]):
    def __init__(self):
        super().__init__(lambda c: c.name)
