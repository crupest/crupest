from collections.abc import Callable
from dataclasses import dataclass
from types import NoneType
from typing import Any
from copy import deepcopy


@dataclass
class CruAttr:
    name: str
    value: Any
    description: str


@dataclass
class CruAttrDef:
    name: str
    default_description: str
    allow_types: None | set[type]
    allow_none: bool
    default_value: Any
    transformer: Callable[[Any], Any] | None
    validator: Callable[[Any], None]

    def __init__(self, name: str, default_description: str, *,
                 allow_types: list[type] | type | None, allow_none: bool, default_value: Any = None,
                 transformer: Callable[[Any], Any] | None = None,
                 validator: Callable[[Any], None] | None = None) -> None:
        self.name = name
        self.default_description = default_description
        self.default_value = default_value
        #TODO: CONTINUE TOMORROW
        if allow_types is None:
            allow_types = []
        elif isinstance(allow_types, type):
            allow_types = [allow_types]
        else:
            for t in allow_types:
                if not isinstance(t, type):
                    raise TypeError(f"Invalid value of python type : {t}")
        self.allow_types = set(filter(lambda tt: tt is not NoneType, allow_types))
        self.allow_none = allow_none
        self.transformer = transformer
        self.validator = validator
        self.default_value = self.transform_and_validate(self.default_value)
        self.default_value = deepcopy(self.default_value)

    def transform(self, value: Any) -> Any:
        if self.transformer is not None:
            return self.transformer(value)
        return value

    def validate(self, value: Any, /, override_allow_none: bool | None = None) -> None:
        allow_none = override_allow_none if override_allow_none is not None else self.allow_none
        if value is None and not allow_none:
            raise TypeError(f"None is not allowed!")
        if len(self.allow_types) != 0 and type(value) not in self.allow_types:
            raise TypeError(f"Type of {value} is not allowed!")
        if self.validator is not None:
            return self.validator(value)
        return None

    def transform_and_validate(self, value: Any, /, override_allow_none: bool | None = None) -> Any:
        value = self.transform(value)
        self.validate(value, override_allow_none)
        return value

    def make(self, value: Any, description: None | str = None) -> CruAttr:
        value = self.transform_and_validate(value)
        return CruAttr(self.name, value if value is not None else deepcopy(self.default_value),
                       description if description is not None else self.default_description)


class CruAttrDefRegistry:

    def __init__(self) -> None:
        self._def_list = []

    @property
    def items(self) -> list[CruAttrDef]:
        return self._def_list

    def register(self, def_: CruAttrDef):
        for i in self._def_list:
            if i.name == def_.name:
                raise ValueError(f"Attribute {def_.name} already exists!")
        self._def_list.append(def_)

    def register_with(self, name: str, default_description: str, *,
                      allow_types: list[type] | type | None, allow_none: bool,
                      default_value: Any = None,
                      transformer: Callable[[Any], Any] | None = None,
                      validator: Callable[[Any], None] | None = None
                      ) -> CruAttrDef:
        def_ = CruAttrDef(name, default_description, default_value=default_value, allow_types=allow_types,
                          allow_none=allow_none, transformer=transformer, validator=validator)
        self.register(def_)
        return def_

    def register_required(self, name: str, default_description: str, *,
                      allow_types: list[type] | type | None,
                      default_value: Any = None,
                      transformer: Callable[[Any], Any] | None = None,
                      validator: Callable[[Any], None] | None = None
                      ) -> CruAttrDef:
        return self.register_with(name, default_description, default_value=default_value, allow_types=allow_types,
                          allow_none=False, transformer=transformer, validator=validator)

    def register_optional(self, name: str, default_description: str, *,
                      allow_types: list[type] | type | None,
                      default_value: Any = None,
                      transformer: Callable[[Any], Any] | None = None,
                      validator: Callable[[Any], None] | None = None
                      ) -> CruAttrDef:
        return self.register_with(name, default_description, default_value=default_value, allow_types=allow_types,
                          allow_none=True, transformer=transformer, validator=validator)

    def get_item_optional(self, name: str) -> CruAttrDef | None:
        for i in self._def_list:
            if i.name == name:
                return i
        return None

    def __getitem__(self, item) -> CruAttrDef | None:
        return self.get_item_optional(item)
