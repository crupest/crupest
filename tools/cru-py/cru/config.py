from __future__ import annotations

from typing import TypeVar, Generic

from ._error import CruInternalError, CruException
from .list import CruUniqueKeyList
from .value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    CruValueTypeError,
    ValueGeneratorBase,
    ValueType,
)

_T = TypeVar("_T")


class CruConfigError(CruException):
    def __init__(self, message: str, item: ConfigItem, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._item = item

    @property
    def item(self) -> ConfigItem:
        return self._item


class ConfigItem(Generic[_T]):
    def __init__(
        self,
        name: str,
        description: str,
        value_type: ValueType[_T],
        value: _T | None = None,
        /,
        default: ValueGeneratorBase[_T] | _T | None = None,
    ) -> None:
        self._name = name
        self._description = description
        self._value_type = value_type
        self._value = value
        self._default = default
        self._default_value: _T | None = None

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
    def is_set(self) -> bool:
        return self._value is not None

    @property
    def value(self) -> _T:
        if self._value is None:
            raise CruConfigError("Config value is not set.", self)
        return self._value

    @property
    def value_or_default(self) -> _T:
        if self._value is not None:
            return self._value
        elif self._default_value is not None:
            return self._default_value
        else:
            self._default_value = self.generate_default_value()
            return self._default_value

    @property
    def default(self) -> ValueGeneratorBase[_T] | _T | None:
        return self._default

    @property
    def can_generate_default(self) -> bool:
        return self.default is not None

    def set_value(
        self, v: _T | str, *, empty_is_default=True, allow_convert_from_str=True
    ):
        if empty_is_default and v == "":
            self._value = None
        elif allow_convert_from_str:
            self._value = self.value_type.check_value_or_try_convert_from_str(v)
        else:
            self._value = self.value_type.check_value(v)

    def reset(self, clear_default_cache=False):
        if clear_default_cache:
            self._default_value = None
        self._value = None

    def generate_default_value(self) -> _T:
        if self.default is None:
            raise CruConfigError(
                "Config item does not support default value generation.", self
            )
        elif isinstance(self.default, ValueGeneratorBase):
            v = self.default.generate()
        else:
            v = self.default
        try:
            self.value_type.check_value(v)
            return v
        except CruValueTypeError as e:
            raise CruInternalError(
                "Config value generator returns an invalid value."
            ) from e

    def copy(self) -> "ConfigItem":
        return ConfigItem(
            self.name,
            self.description,
            self.value_type,
            self.value,
            self.default,
        )


class Configuration(CruUniqueKeyList[ConfigItem, str]):
    def __init__(self):
        super().__init__(lambda c: c.name)

    def add_text_config(
        self,
        name: str,
        description: str,
        value: str | None = None,
        default: ValueGeneratorBase[str] | str | None = None,
    ) -> ConfigItem:
        item = ConfigItem(name, description, TEXT_VALUE_TYPE, value, default)
        self.add(item)
        return item

    def add_int_config(
        self,
        name: str,
        description: str,
        value: int | None = None,
        default: ValueGeneratorBase[int] | int | None = None,
    ) -> ConfigItem:
        item = ConfigItem(name, description, INTEGER_VALUE_TYPE, value, default)
        self.add(item)
        return item

    def reset_all(self, clear_default_cache=False) -> None:
        for item in self:
            item.reset(clear_default_cache)
