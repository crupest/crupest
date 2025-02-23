from __future__ import annotations

import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any

from .list import CruUniqueKeyList
from ._type import CruTypeSet
from ._const import CruNotFound, CruUseDefault, CruDontChange
from ._iter import CruIterator


@dataclass
class CruAttr:

    name: str
    value: Any
    description: str | None

    @staticmethod
    def make(
        name: str, value: Any = CruUseDefault.VALUE, description: str | None = None
    ) -> CruAttr:
        return CruAttr(name, value, description)


CruAttrDefaultFactory = Callable[["CruAttrDef"], Any]
CruAttrTransformer = Callable[[Any, "CruAttrDef"], Any]
CruAttrValidator = Callable[[Any, "CruAttrDef"], None]


@dataclass
class CruAttrDef:
    name: str
    description: str
    default_factory: CruAttrDefaultFactory
    transformer: CruAttrTransformer
    validator: CruAttrValidator

    def __init__(
        self,
        name: str,
        description: str,
        default_factory: CruAttrDefaultFactory,
        transformer: CruAttrTransformer,
        validator: CruAttrValidator,
    ) -> None:
        self.name = name
        self.description = description
        self.default_factory = default_factory
        self.transformer = transformer
        self.validator = validator

    def transform(self, value: Any) -> Any:
        if self.transformer is not None:
            return self.transformer(value, self)
        return value

    def validate(self, value: Any, /, force_allow_none: bool = False) -> None:
        if force_allow_none is value is None:
            return
        if self.validator is not None:
            self.validator(value, self)

    def transform_and_validate(
        self, value: Any, /, force_allow_none: bool = False
    ) -> Any:
        value = self.transform(value)
        self.validate(value, force_allow_none)
        return value

    def make_default_value(self) -> Any:
        return self.transform_and_validate(self.default_factory(self))

    def adopt(self, attr: CruAttr) -> CruAttr:
        attr = copy.deepcopy(attr)

        if attr.name is None:
            attr.name = self.name
        elif attr.name != self.name:
            raise ValueError(f"Attr name is not match: {attr.name} != {self.name}")

        if attr.value is CruUseDefault.VALUE:
            attr.value = self.make_default_value()
        else:
            attr.value = self.transform_and_validate(attr.value)

        if attr.description is None:
            attr.description = self.description

        return attr

    def make(
        self, value: Any = CruUseDefault.VALUE, description: None | str = None
    ) -> CruAttr:
        value = self.make_default_value() if value is CruUseDefault.VALUE else value
        value = self.transform_and_validate(value)
        return CruAttr(
            self.name,
            value,
            description if description is not None else self.description,
        )


@dataclass
class CruAttrDefBuilder:

    name: str
    description: str
    types: list[type] | None = field(default=None)
    allow_none: bool = field(default=False)
    default: Any = field(default=CruUseDefault.VALUE)
    default_factory: CruAttrDefaultFactory | None = field(default=None)
    auto_list: bool = field(default=False)
    transformers: list[CruAttrTransformer] = field(default_factory=list)
    validators: list[CruAttrValidator] = field(default_factory=list)
    override_transformer: CruAttrTransformer | None = field(default=None)
    override_validator: CruAttrValidator | None = field(default=None)

    build_hook: Callable[[CruAttrDef], None] | None = field(default=None)

    def __init__(self, name: str, description: str) -> None:
        super().__init__()
        self.name = name
        self.description = description

    def auto_adjust_default(self) -> None:
        if self.default is not CruUseDefault.VALUE and self.default is not None:
            return
        if self.allow_none and self.default is CruUseDefault.VALUE:
            self.default = None
        if not self.allow_none and self.default is None:
            self.default = CruUseDefault.VALUE
        if self.auto_list and not self.allow_none:
            self.default = []

    def with_name(self, name: str | CruDontChange) -> CruAttrDefBuilder:
        if name is not CruDontChange.VALUE:
            self.name = name
        return self

    def with_description(
        self, default_description: str | CruDontChange
    ) -> CruAttrDefBuilder:
        if default_description is not CruDontChange.VALUE:
            self.description = default_description
        return self

    def with_default(self, default: Any) -> CruAttrDefBuilder:
        if default is not CruDontChange.VALUE:
            self.default = default
        return self

    def with_default_factory(
        self,
        default_factory: CruAttrDefaultFactory | CruDontChange,
    ) -> CruAttrDefBuilder:
        if default_factory is not CruDontChange.VALUE:
            self.default_factory = default_factory
        return self

    def with_types(
        self,
        types: Iterable[type] | None | CruDontChange,
    ) -> CruAttrDefBuilder:
        if types is not CruDontChange.VALUE:
            self.types = None if types is None else list(types)
        return self

    def with_allow_none(self, allow_none: bool | CruDontChange) -> CruAttrDefBuilder:
        if allow_none is not CruDontChange.VALUE:
            self.allow_none = allow_none
        return self

    def with_auto_list(
        self, auto_list: bool | CruDontChange = True
    ) -> CruAttrDefBuilder:
        if auto_list is not CruDontChange.VALUE:
            self.auto_list = auto_list
        return self

    def with_constraint(
        self,
        /,
        allow_none: bool | CruDontChange = CruDontChange.VALUE,
        types: Iterable[type] | None | CruDontChange = CruDontChange.VALUE,
        default: Any = CruDontChange.VALUE,
        default_factory: CruAttrDefaultFactory | CruDontChange = CruDontChange.VALUE,
        auto_list: bool | CruDontChange = CruDontChange.VALUE,
    ) -> CruAttrDefBuilder:
        return (
            self.with_allow_none(allow_none)
            .with_types(types)
            .with_default(default)
            .with_default_factory(default_factory)
            .with_auto_list(auto_list)
        )

    def add_transformer(self, transformer: CruAttrTransformer) -> CruAttrDefBuilder:
        self.transformers.append(transformer)
        return self

    def clear_transformers(self) -> CruAttrDefBuilder:
        self.transformers.clear()
        return self

    def add_validator(self, validator: CruAttrValidator) -> CruAttrDefBuilder:
        self.validators.append(validator)
        return self

    def clear_validators(self) -> CruAttrDefBuilder:
        self.validators.clear()
        return self

    def with_override_transformer(
        self, override_transformer: CruAttrTransformer | None | CruDontChange
    ) -> CruAttrDefBuilder:
        if override_transformer is not CruDontChange.VALUE:
            self.override_transformer = override_transformer
        return self

    def with_override_validator(
        self, override_validator: CruAttrValidator | None | CruDontChange
    ) -> CruAttrDefBuilder:
        if override_validator is not CruDontChange.VALUE:
            self.override_validator = override_validator
        return self

    def is_valid(self) -> tuple[bool, str]:
        if not isinstance(self.name, str):
            return False, "Name must be a string!"
        if not isinstance(self.description, str):
            return False, "Default description must be a string!"
        if (
            not self.allow_none
            and self.default is None
            and self.default_factory is None
        ):
            return False, "Default must be set if allow_none is False!"
        return True, ""

    @staticmethod
    def _build(
        builder: CruAttrDefBuilder, auto_adjust_default: bool = True
    ) -> CruAttrDef:
        if auto_adjust_default:
            builder.auto_adjust_default()

        valid, err = builder.is_valid()
        if not valid:
            raise ValueError(err)

        def composed_transformer(value: Any, attr_def: CruAttrDef) -> Any:
            def transform_value(single_value: Any) -> Any:
                for transformer in builder.transformers:
                    single_value = transformer(single_value, attr_def)
                return single_value

            if builder.auto_list:
                if not isinstance(value, list):
                    value = [value]
                value = CruIterator(value).transform(transform_value).to_list()

            else:
                value = transform_value(value)
            return value

        type_set = None if builder.types is None else CruTypeSet(*builder.types)

        def composed_validator(value: Any, attr_def: CruAttrDef):
            def validate_value(single_value: Any) -> None:
                if type_set is not None:
                    type_set.check_value(single_value, allow_none=builder.allow_none)
                for validator in builder.validators:
                    validator(single_value, attr_def)

            if builder.auto_list:
                CruIterator(value).foreach(validate_value)
            else:
                validate_value(value)

        real_transformer = builder.override_transformer or composed_transformer
        real_validator = builder.override_validator or composed_validator

        default_factory = builder.default_factory
        if default_factory is None:

            def default_factory(_d):
                return copy.deepcopy(builder.default)

        d = CruAttrDef(
            builder.name,
            builder.description,
            default_factory,
            real_transformer,
            real_validator,
        )
        if builder.build_hook:
            builder.build_hook(d)
        return d

    def build(self, auto_adjust_default=True) -> CruAttrDef:
        c = copy.deepcopy(self)
        self.build_hook = None
        return CruAttrDefBuilder._build(c, auto_adjust_default)


class CruAttrDefRegistry(CruUniqueKeyList[CruAttrDef, str]):

    def __init__(self) -> None:
        super().__init__(lambda d: d.name)

    def make_builder(self, name: str, default_description: str) -> CruAttrDefBuilder:
        b = CruAttrDefBuilder(name, default_description)
        b.build_hook = lambda a: self.add(a)
        return b

    def adopt(self, attr: CruAttr) -> CruAttr:
        d = self.get(attr.name)
        return d.adopt(attr)


class CruAttrTable(CruUniqueKeyList[CruAttr, str]):
    def __init__(self, registry: CruAttrDefRegistry) -> None:
        self._registry: CruAttrDefRegistry = registry
        super().__init__(lambda a: a.name, before_add=registry.adopt)

    @property
    def registry(self) -> CruAttrDefRegistry:
        return self._registry

    def get_value_or(self, name: str, fallback: Any = CruNotFound.VALUE) -> Any:
        a = self.get_or(name, CruNotFound.VALUE)
        if a is CruNotFound.VALUE:
            return fallback
        return a.value

    def get_value(self, name: str) -> Any:
        a = self.get(name)
        return a.value

    def make_attr(
        self,
        name: str,
        value: Any = CruUseDefault.VALUE,
        /,
        description: str | None = None,
    ) -> CruAttr:
        d = self._registry.get(name)
        return d.make(value, description or d.description)

    def add_value(
        self,
        name: str,
        value: Any = CruUseDefault.VALUE,
        /,
        description: str | None = None,
        *,
        replace: bool = False,
    ) -> CruAttr:
        attr = self.make_attr(name, value, description)
        self.add(attr, replace)
        return attr
