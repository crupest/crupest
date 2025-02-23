from __future__ import annotations

from typing import Any, TypeVar, Generic

from ._error import CruException
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
            raise CruConfigError(
                "Config value is not set.",
                self,
                user_message=f"Config item {self.name} is not set.",
            )
        return self._value

    @property
    def value_str(self) -> str:
        return self.value_type.convert_value_to_str(self.value)

    def set_value(self, v: _T | str, allow_convert_from_str=False):
        if allow_convert_from_str:
            self._value = self.value_type.check_value_or_try_convert_from_str(v)
        else:
            self._value = self.value_type.check_value(v)

    def reset(self):
        self._value = None

    @property
    def default(self) -> ValueGeneratorBase[_T] | _T | None:
        return self._default

    @property
    def can_generate_default(self) -> bool:
        return self.default is not None

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
            raise CruConfigError(
                "Config value generator returns an invalid value.", self
            ) from e

    def copy(self) -> "ConfigItem":
        return ConfigItem(
            self.name,
            self.description,
            self.value_type,
            self.value,
            self.default,
        )

    @property
    def description_str(self) -> str:
        return f"{self.name} ({self.value_type.name}): {self.description}"


class Configuration(CruUniqueKeyList[ConfigItem[Any], str]):
    def __init__(self):
        super().__init__(lambda c: c.name)

    def get_set_items(self) -> list[ConfigItem[Any]]:
        return [item for item in self if item.is_set]

    def get_unset_items(self) -> list[ConfigItem[Any]]:
        return [item for item in self if not item.is_set]

    @property
    def all_set(self) -> bool:
        return len(self.get_unset_items()) == 0

    @property
    def all_not_set(self) -> bool:
        return len(self.get_set_items()) == 0

    def add_text_config(
        self,
        name: str,
        description: str,
        value: str | None = None,
        default: ValueGeneratorBase[str] | str | None = None,
    ) -> ConfigItem[str]:
        item = ConfigItem(name, description, TEXT_VALUE_TYPE, value, default)
        self.add(item)
        return item

    def add_int_config(
        self,
        name: str,
        description: str,
        value: int | None = None,
        default: ValueGeneratorBase[int] | int | None = None,
    ) -> ConfigItem[int]:
        item = ConfigItem(name, description, INTEGER_VALUE_TYPE, value, default)
        self.add(item)
        return item

    def set_config_item(
        self,
        name: str,
        value: Any | str,
        allow_convert_from_str=True,
    ) -> None:
        item = self.get(name)
        item.set_value(
            value,
            allow_convert_from_str=allow_convert_from_str,
        )

    def reset_all(self) -> None:
        for item in self:
            item.reset()

    def to_dict(self) -> dict[str, Any]:
        return {item.name: item.value for item in self}

    def to_str_dict(self) -> dict[str, str]:
        return {
            item.name: item.value_type.convert_value_to_str(item.value) for item in self
        }

    def set_value_dict(
        self,
        value_dict: dict[str, Any],
        allow_convert_from_str: bool = False,
    ) -> None:
        for name, value in value_dict.items():
            item = self.get(name)
            item.set_value(
                value,
                allow_convert_from_str=allow_convert_from_str,
            )
