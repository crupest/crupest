from typing import Any, TypeVar, Generic

from .excp import CruInternalLogicError
from .value import ValueType, ValueGenerator, ValidationError

T = TypeVar("T")


class ConfigItem(Generic[T]):
    OptionalValueGenerator = ValueGenerator[T, []] | None

    def __init__(self, name: str, description: str, value_type: ValueType[T], value: T | None, default_value: T, *,
                 value_generator: OptionalValueGenerator = None) -> None:
        self._name = name
        self._description = description
        self._value_type = value_type
        self._default_value = default_value
        self._value_generator = value_generator
        self._value: T | None = value

    @property
    def name(self) -> str:
        return self._name

    @property
    def description(self) -> str:
        return self._description

    @property
    def value_type(self) -> ValueType[T]:
        return self._value_type

    @property
    def default_value(self) -> T:
        return self._default_value

    @property
    def is_default(self) -> bool:
        return self._value is None

    @property
    def is_set(self) -> bool:
        return not self.is_default

    @property
    def value(self) -> T:
        return self._value or self._default_value

    def set_value(self, v: T | str, /, allow_convert_from_str=False):
        if allow_convert_from_str:
            self._value = self.value_type.check_value(v)
        else:
            self._value = self.value_type.check_value_or_try_convert_from_str(v)

    @value.setter
    def value(self, v: T) -> None:
        self.set_value(v)

    @property
    def value_generator(self) -> OptionalValueGenerator:
        return self._value_generator

    def generate_value(self, allow_interactive=False) -> T | None:
        if self.value_generator is None: return None
        if self.value_generator.interactive and not allow_interactive:
            return None
        else:
            v = self.generate_value()
            try:
                self.value_type.check_value(v)
                return v
            except ValidationError as e:
                raise CruInternalLogicError("Config value generator returns invalid value.", name=self.name, inner=e)

    def copy(self) -> "ConfigItem":
        return ConfigItem(self.name, self.description, self.value_type,
                          self._value.copy() if self._value is not None else None, self._default_value.copy(),
                          value_generator=self.value_generator)


class Configuration:
    def __init__(self, items: None | list[ConfigItem] = None) -> None:
        self._items: list[ConfigItem] = items or []

    @property
    def items(self) -> list[ConfigItem]:
        return self._items

    @property
    def item_map(self) -> dict[str, ConfigItem]:
        return {i.name: i for i in self.items}

    def get_optional_item(self, name: str) -> ConfigItem | None:
        for i in self.items:
            if i.name == name:
                return i
        return None

    def clear(self) -> None:
        self._items.clear()

    def has_item(self, name: str) -> bool:
        return self.get_optional_item(name) is not None

    def add_item(self, item: ConfigItem):
        i = self.get_optional_item(item.name)
        if i is not None:
            raise CruInternalLogicError("Config item of the name already exists.", name=item.name)
        self.items.append(item)
        return item

    def set_value(self, name: str, v: Any, /, allow_convert_from_str=False):
        i = self.get_optional_item(name)
        if i is None:
            raise CruInternalLogicError("No config item of the name. Can't set value.", name=name)
        i.set_value(v, allow_convert_from_str)

    def copy(self) -> "Configuration":
        return Configuration([i.copy() for i in self.items])

    def __getitem__(self, name: str) -> ConfigItem:
        i = self.get_optional_item(name)
        if i is not None:
            return i
        raise CruInternalLogicError('No config item of the name.', name=name)

    def __contains__(self, name: str):
        return self.has_item(name)
