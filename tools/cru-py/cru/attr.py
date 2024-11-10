import copy
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .util import CanBeList, TypeSet, L, ListOperations


@dataclass
class CruAttr:
    name: str
    value: Any
    description: str


class _CruAttrVoid:
    _i = False

    def __init__(self):
        if self._i:
            raise ValueError("CruAttrNotSet is a singleton!")
        self._i = True

    def __copy__(self):
        return self


CRU_ATTR_NOT_SET = _CruAttrVoid()
CRU_ATTR_USE_DEFAULT = CRU_ATTR_NOT_SET.__copy__()


def _is_attr_void(v: Any) -> bool:
    return isinstance(v, _CruAttrVoid)


@dataclass
class CruAttrDef:
    name: str
    description: str
    default_factory: Callable[[], Any]
    transformer: Callable[[Any], Any]
    validator: Callable[[Any], None]

    def __init__(self, name: str, description: str, default_factory: Callable[[], Any],
                 transformer: Callable[[Any], Any], validator: Callable[[Any], None]) -> None:
        self.name = name
        self.description = description
        self.default_factory = default_factory
        self.transformer = transformer
        self.validator = validator

    def transform(self, value: Any) -> Any:
        if self.transformer is not None:
            return self.transformer(value)
        return value

    def validate(self, value: Any, /, force_allow_none: bool = False) -> None:
        if force_allow_none is value is None:
            return
        if self.validator is not None:
            self.validator(value)

    def transform_and_validate(self, value: Any = CRU_ATTR_USE_DEFAULT, /, force_allow_none: bool = False) -> Any:
        value = self.transform(value)
        self.validate(value, force_allow_none)
        return value

    def make_default_value(self) -> Any:
        return self.transform_and_validate(self.default_factory())

    def adopt(self, attr: CruAttr) -> CruAttr:
        attr = copy.deepcopy(attr)

        if attr.name is None:
            attr.name = self.name
        elif attr.name != self.name:
            raise ValueError(f"Attr name is not match: {attr.name} != {self.name}")

        if attr.value is CRU_ATTR_NOT_SET:
            attr.value = self.make_default_value()
        else:
            attr.value = self.transform_and_validate(attr.value)

        if attr.description is None:
            attr.description = self.description

        return attr

    def make(self, value: Any = CRU_ATTR_USE_DEFAULT, description: None | str = None) -> CruAttr:
        value = self.default_factory() if _is_attr_void(value) else value
        value = self.default_factory() if value is CRU_ATTR_USE_DEFAULT else value
        value = self.transform_and_validate(value)
        return CruAttr(self.name, value,
                       description if description is not None else self.description)


@dataclass
class CruAttrDefBuilder:
    name: str
    description: str
    types: CanBeList[type] = field(default=None)
    allow_none: bool = field(default=True)
    default: Any = field(default=CRU_ATTR_NOT_SET)
    default_factory: Callable[[], Any] | None = field(default=None)
    auto_list: bool = field(default=False)
    transformers: list[Callable[[Any], Any]] = field(default_factory=list)
    validators: list[Callable[[Any], None]] = field(default_factory=list)
    override_transformer: Callable[[Any], Any] | None = field(default=None)
    override_validator: Callable[[Any], None] | None = field(default=None)

    build_hook: Callable[[CruAttrDef], None] | None = field(default=None)

    def __init__(self, name: str, description: str) -> None:
        super().__init__()
        self.name = name
        self.description = description

    def auto_adjust_default(self) -> "CruAttrDefBuilder":
        if self.default is not CRU_ATTR_NOT_SET and self.default is not None:
            return self
        if self.allow_none and _is_attr_void(self.default):
            self.default = None
        if not self.allow_none and self.default is None:
            self.default = CRU_ATTR_NOT_SET
        if self.auto_list and not self.allow_none:
            self.default = []

    def with_name(self, name: str) -> "CruAttrDefBuilder":
        self.name = name
        return self

    def with_description(self, default_description: str) -> "CruAttrDefBuilder":
        self.description = default_description
        return self

    def with_default(self, default: Any, is_factory: bool = False,
                     reserve_if_not_set: bool = False) -> "CruAttrDefBuilder":
        if is_factory:
            self.default_factory = default
        else:
            if _is_attr_void(default) and reserve_if_not_set:
                return self
            else:
                self.default = default
        return self

    def with_default_factory(self, default_factory: Callable[[], Any]) -> "CruAttrDefBuilder":
        return self.with_default(default_factory, is_factory=True)

    def with_types(self, allowed_types: CanBeList[type], default: Any = CRU_ATTR_NOT_SET) -> "CruAttrDefBuilder":
        self.types = allowed_types
        if _is_attr_void(default):
            self.default = default
        return self

    def with_allow_none(self, allow_none: bool, default: Any = CRU_ATTR_NOT_SET) -> "CruAttrDefBuilder":
        self.allow_none = allow_none
        if _is_attr_void(default):
            self.default = default
        return self

    def with_optional(self, default: Any = CRU_ATTR_NOT_SET) -> "CruAttrDefBuilder":
        return self.with_allow_none(True, default)

    def with_required(self, default: Any = CRU_ATTR_NOT_SET) -> "CruAttrDefBuilder":
        return self.with_allow_none(False, default)

    def with_constraint(self, required: bool, allowed_types: CanBeList[type] = None, /,
                        default: Any = CRU_ATTR_NOT_SET, auto_list=False, *, default_is_factory: bool = False,
                        default_reserve_if_not_set: bool = True) -> "CruAttrDefBuilder":
        return (self.with_allow_none(required).with_types(allowed_types).with_auto_list(auto_list).
                with_default(default, default_is_factory, default_reserve_if_not_set))

    def with_auto_list(self, transform_auto_list: bool = True) -> "CruAttrDefBuilder":
        self.auto_list = transform_auto_list
        return self

    def add_transformer(self, transformer: Callable[[Any], Any] | None) -> "CruAttrDefBuilder":
        if transformer is not None:
            self.transformers.append(transformer)
        return self

    def clear_transformers(self) -> "CruAttrDefBuilder":
        self.transformers.clear()
        return self

    def add_validator(self, validator: Callable[[Any], None] | None) -> "CruAttrDefBuilder":
        if validator is not None:
            self.validators.append(validator)
        return self

    def clear_validators(self) -> "CruAttrDefBuilder":
        self.validators.clear()
        return self

    def with_override_transformer(self, override_transformer: Callable[[Any], Any] | None) -> "CruAttrDefBuilder":
        self.override_transformer = override_transformer
        return self

    def with_override_validator(self, override_validator: Callable[[Any], None] | None) -> "CruAttrDefBuilder":
        self.override_validator = override_validator
        return self

    def is_valid(self) -> tuple[bool, str]:
        if not isinstance(self.name, str):
            return False, "Name must be a string!"
        if not isinstance(self.description, str):
            return False, "Default description must be a string!"
        if not self.allow_none and self.default is None and self.default_factory is None:
            return False, "Default must be set if allow_none is False!"

    @staticmethod
    def _build(b: "CruAttrDefBuilder", auto_adjust_default: bool = True) -> CruAttrDef:
        if auto_adjust_default:
            b.auto_adjust_default()

        valid, err = b.is_valid()
        if not valid: raise ValueError(err)

        def composed_transformer(v: Any):
            if b.auto_list:
                v = L.make(v)
            for t in b.transformers:
                v = t(v)
            return v

        type_set = TypeSet(b.types)

        def composed_validator(v: Any):
            if b.auto_list:
                type_set.check_value_list(v, allow_none=b.allow_none)
                ListOperations.foreach(v, *b.validators)
            else:
                type_set.check_value(v, allow_none=b.allow_none)
                for vl in b.validators: vl(v)

        validator = b.override_validator or composed_validator
        transformer = b.override_transformer or composed_transformer

        default_factory = b.default_factory
        if b.default_factory is None:
            default_factory = lambda: copy.deepcopy(b.default)
        validator(default_factory())

        d = CruAttrDef(b.name, b.description, default_factory, transformer, validator)
        if b.build_hook: b.build_hook(d)
        return d

    def build(self, auto_adjust_default=True) -> CruAttrDef:
        c = copy.deepcopy(self)
        self.build_hook = None
        return CruAttrDefBuilder._build(c, auto_adjust_default)


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

    def make_builder(self, name: str, default_description: str) -> CruAttrDefBuilder:
        b = CruAttrDefBuilder(name, default_description)
        b.build_hook = lambda a: self.register(a)
        return b

    def get_item_optional(self, name: str) -> CruAttrDef | None:
        for i in self._def_list:
            if i.name == name:
                return i
        return None


class CruAttrTable:
    def __init__(self, registry: CruAttrDefRegistry) -> None:
        self._registry: CruAttrDefRegistry = registry
        self._attrs: list[CruAttr] = []

    def get_attr_or(self, name: str, fallback: Any = None) -> CruAttr | Any:
        for a in self._attrs:
            if a.name == name:
                return a
        return fallback

    def get_attr(self, name) -> CruAttr:
        a = self.get_attr_or(name, None)
        if a is None:
            raise KeyError(f"Attribute {name} not found!")
        return a

    def get_value_or(self, name: str, fallback: Any = None) -> Any:
        a = self.get_attr_or(name, None)
        if a is None:
            return fallback
        return a.value

    def get_value(self, name: str) -> Any:
        a = self.get_attr(name)
        return a.value

    def get_def_or(self, name: str, fallback: Any = None) -> CruAttrDef | Any:
        d = self._registry.get_item_optional(name)
        return d if d is not None else fallback

    def get_def(self, name: str) -> CruAttrDef:
        d = self._registry.get_item_optional(name)
        if d is None:
            raise KeyError(f"Attribute definition {name} not found!")
        return d

    def _check_already_exist(self, name: str) -> None:
        if name in self:
            raise KeyError(f"Attribute {name} already exists!")

    def add_attr(self, attr: CruAttr) -> CruAttr:
        self._check_already_exist(attr.name)
        d = self.get_def(attr.name)
        attr = d.adopt(attr)
        self._attrs.append(attr)
        return attr

    def add(self, name: str, value: Any = CRU_ATTR_USE_DEFAULT, /, description: str | None = None) -> CruAttr:
        self._check_already_exist(name)
        d = self.get_def(name)
        attr = d.make(value, description or d.description)
        self._attrs.append(attr)
        return attr

    def remove(self, name: str, /, allow_absense: bool = True) -> None:
        l = [a for a in self._attrs if a.name == name]
        if len(l) != len(self._attrs) and not allow_absense:
            raise KeyError(f"Attribute {name} not found!")
        self._attrs = l

    def __contains__(self, name):
        return any(a.name == name for a in self._attrs)
