import copy
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from typing import Any, ClassVar

from .util import CanBeList, TypeSet, F, L, WF, CruUniqueKeyInplaceList, CRU_NOT_FOUND, CRU_USE_DEFAULT, \
    CRU_DONT_CHANGE, CRU_PLACEHOLDER


@dataclass
class CruAttr:
    USE_DEFAULT: ClassVar = CRU_USE_DEFAULT

    name: str
    value: Any
    description: str

    @staticmethod
    def make(name: str, value: Any = USE_DEFAULT, description: str | None = None) -> "CruAttr":
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

    def __init__(self, name: str, description: str, default_factory: CruAttrDefaultFactory,
                 transformer: CruAttrTransformer, validator: CruAttrValidator) -> None:
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

    def transform_and_validate(self, value: Any, /, force_allow_none: bool = False) -> Any:
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

        if attr.value is CruAttr.USE_DEFAULT:
            attr.value = self.make_default_value()
        else:
            attr.value = self.transform_and_validate(attr.value)

        if attr.description is None:
            attr.description = self.description

        return attr

    def make(self, value: Any = CruAttr.USE_DEFAULT, description: None | str = None) -> CruAttr:
        value = self.make_default_value() if value is CruAttr.USE_DEFAULT else value
        value = self.transform_and_validate(value)
        return CruAttr(self.name, value,
                       description if description is not None else self.description)


@dataclass
class CruAttrDefBuilder:
    DONT_CHANGE: ClassVar = CRU_DONT_CHANGE

    name: str
    description: str
    types: CanBeList[type] = field(default=None)
    allow_none: bool = field(default=True)
    default: Any = field(default=CruAttr.USE_DEFAULT)
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

    def auto_adjust_default(self) -> "CruAttrDefBuilder":
        if self.default is not CruAttr.USE_DEFAULT and self.default is not None:
            return self
        if self.allow_none and self.default is CruAttr.USE_DEFAULT:
            self.default = None
        if not self.allow_none and self.default is None:
            self.default = CruAttr.USE_DEFAULT
        if self.auto_list and not self.allow_none:
            self.default = []

    def with_name(self, name: str) -> "CruAttrDefBuilder":
        self.name = name
        return self

    def with_description(self, default_description: str) -> "CruAttrDefBuilder":
        self.description = default_description
        return self

    def with_default(self, /, default: Any | DONT_CHANGE = DONT_CHANGE,
                     default_factory: CruAttrDefaultFactory | DONT_CHANGE = DONT_CHANGE) -> "CruAttrDefBuilder":
        if default is not CruAttrDefBuilder.DONT_CHANGE:
            self.default = default
        if default_factory is not CruAttrDefBuilder.DONT_CHANGE:
            self.default_factory = default_factory
        return self

    def with_default_value(self, default: Any) -> "CruAttrDefBuilder":
        self.default = default
        return self

    def with_default_factory(self, default_factory: CruAttrDefaultFactory) -> "CruAttrDefBuilder":
        self.default_factory = default_factory
        return self

    def with_types(self, allowed_types: CanBeList[type], default: Any = DONT_CHANGE) -> "CruAttrDefBuilder":
        self.types = allowed_types
        if default is not CruAttrDefBuilder.DONT_CHANGE:
            self.default = default
        return self

    def with_allow_none(self, allow_none: bool, default: Any = DONT_CHANGE) -> "CruAttrDefBuilder":
        self.allow_none = allow_none
        if default is not CruAttrDefBuilder.DONT_CHANGE:
            self.default = default
        return self

    def with_optional(self, default: Any = DONT_CHANGE) -> "CruAttrDefBuilder":
        return self.with_allow_none(True, default)

    def with_required(self, default: Any = DONT_CHANGE) -> "CruAttrDefBuilder":
        return self.with_allow_none(False, default)

    def with_constraint(self, /, required: bool = DONT_CHANGE, allowed_types: CanBeList[type] = DONT_CHANGE,
                        default: Any = DONT_CHANGE, default_factory: CruAttrDefaultFactory = DONT_CHANGE,
                        auto_list: bool = DONT_CHANGE) -> "CruAttrDefBuilder":
        def should_change(v):
            return v is not CruAttrDefBuilder.DONT_CHANGE

        if should_change(required):
            self.allow_none = not required
        if should_change(allowed_types):
            self.types = allowed_types
        if should_change(default):
            self.default = default
        if should_change(default_factory):
            self.default_factory = default_factory
        if should_change(auto_list):
            self.auto_list = auto_list
        return self

    def with_auto_list(self, transform_auto_list: bool = True) -> "CruAttrDefBuilder":
        self.auto_list = transform_auto_list
        return self

    def add_transformer(self, transformer: Callable[[Any, "CruAttrDef"], Any] | None) -> "CruAttrDefBuilder":
        if transformer is not None:
            self.transformers.append(transformer)
        return self

    def clear_transformers(self) -> "CruAttrDefBuilder":
        self.transformers.clear()
        return self

    def add_validator(self, validator: Callable[[Any, "CruAttrDef"], None] | None) -> "CruAttrDefBuilder":
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

        def composed_transformer(v: Any, d_):
            transformers = L(b.transformers)
            transformers.transform(lambda f: F(f).bind(CRU_PLACEHOLDER, d_))
            transformer = F.make_chain(*transformers) if not transformers.is_empty else WF.only_you
            if b.auto_list:
                v = L.make(v)
                v = v.transform(transformer)
            else:
                v = transformer(v)
            return v

        type_set = TypeSet(b.types)

        def composed_validator(v: Any, d_):
            validators = L(b.validators)
            validators.transform(lambda f: F(f).bind(CRU_PLACEHOLDER, d_))
            validator = F.make_chain(*validators) if not validators.is_empty else WF.true
            if b.auto_list:
                type_set.check_value_list(v, allow_none=b.allow_none)
                L(v).foreach(validator)
            else:
                type_set.check_value(v, allow_none=b.allow_none)
                validator(v)

        real_transformer = b.override_transformer or composed_transformer
        real_validator = b.override_validator or composed_validator

        default_factory = b.default_factory
        if default_factory is None:
            default_factory = lambda _d: copy.deepcopy(b.default)

        d = CruAttrDef(b.name, b.description, default_factory, real_transformer, real_validator)
        if b.build_hook: b.build_hook(d)
        return d

    def build(self, auto_adjust_default=True) -> CruAttrDef:
        c = copy.deepcopy(self)
        self.build_hook = None
        return CruAttrDefBuilder._build(c, auto_adjust_default)


class CruAttrDefRegistry(CruUniqueKeyInplaceList[CruAttrDef, str]):

    def __init__(self) -> None:
        super().__init__(lambda d: d.name)

    def make_builder(self, name: str, default_description: str) -> CruAttrDefBuilder:
        b = CruAttrDefBuilder(name, default_description)
        b.build_hook = lambda a: self.add(a)
        return b

    def adopt(self, attr: CruAttr) -> CruAttr:
        d = self.get(attr.name)
        return d.adopt(attr)


class CruAttrTable(CruUniqueKeyInplaceList[CruAttr, str]):
    def __init__(self, registry: CruAttrDefRegistry) -> None:
        self._registry: CruAttrDefRegistry = registry
        super().__init__(lambda a: a.name, before_add=registry.adopt)

    @property
    def registry(self) -> CruAttrDefRegistry:
        return self._registry

    def get_value_or(self, name: str, fallback: Any = CRU_NOT_FOUND) -> Any:
        a = self.get_or(name, CRU_NOT_FOUND)
        if a is CRU_NOT_FOUND:
            return fallback
        return a.value

    def get_value(self, name: str) -> Any:
        a = self.get(name)
        return a.value

    def make_attr(self, name: str, value: Any = CruAttr.USE_DEFAULT, /, description: str | None = None) -> CruAttr:
        d = self._registry.get(name)
        return d.make(value, description or d.description)

    def add_value(self, name: str, value: Any = CruAttr.USE_DEFAULT, /, description: str | None = None, *,
                  replace: bool = False) -> CruAttr:
        attr = self.make_attr(name, value, description)
        self.add(attr, replace)
        return attr

    def extend_values(self, *t: tuple[str, Any, str | None], replace: bool = False) -> None:
        t = [self.make_attr(n, v, d) for n, v, d in t]
        self.extend(t, replace)

    def extend_with(self, a: CruAttr | Iterable[CruAttr | tuple[str, Any, str | None]] | dict[
        str, Any | tuple[Any, str]] | None = None, replace: bool = False):
        if a is None: return

        if isinstance(a, CruAttr):
            self.add(a, replace)
            return

        if isinstance(a, dict):
            l = L()
            for k, v in a.items():
                if isinstance(v, tuple):
                    v, d = v
                else:
                    d = None
                l.append(self.make_attr(k, v, d))
            self.extend(l, replace)
            return

        if isinstance(a, Iterable):
            l = L(a)
            l.transform_if(lambda n_, v_, d_: self.make_attr(n_, v_, d_), F(isinstance).bind(CRU_PLACEHOLDER, tuple))
            self.extend(l, replace)
            return

        raise TypeError(f"Unsupported type: {type(a)}")
