from collections.abc import Callable
from dataclasses import dataclass
from types import NoneType
from typing import Any

from cru.attr import CruAttrDefRegistry

CRU_EXCEPTION_ATTR_DEF_REGISTRY = CruAttrDefRegistry()


class CruException(Exception):
    @staticmethod
    def transform_inner(inner: Exception | list[Exception] | None):
        if inner is None:
            return None
        if isinstance(inner, Exception):
            return [inner]
        if isinstance(inner, list):
            return inner

    @staticmethod
    def validate_inner(inner: list[Exception]):
        for i in inner:
            if not isinstance(i, Exception):
                raise TypeError(f"Invalid inner exception: {i}")

    MESSAGE_DEF = CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_required("message", "Message describing the exception.",
                                                                allow_types=str, default_value="")
    INNER_DEF = CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_required("inner", "Inner exception.",
                                                  allow_types=list, default_value=[],
                                                  transformer=transform_inner, validator=validate_inner)
    INTERNAL_DEF = CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_required("internal",
                                                  "True if the exception is caused by wrong internal logic. False if it is caused by user's wrong input.",
                                                  allow_types=bool, default_value=False)
    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_optional("name", "Name of the object that causes the exception.",
                                                  allow_types=str)
    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_optional("value", "Value that causes the exception.",
                                                  allow_types=[])
    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_with("path", "Path that causes the exception.",)
    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_with("type", "Python type related to the exception.")

    def __init__(self, message: str, *args,
                 inner: Exception | list[Exception] | None = None,
                 internal: bool = False,
                 name: str | None = None,
                 value: Any | None = None,
                 path: str | None = None,
                 type_: type | None = None,
                 init_attrs: dict[str, Any] | None = None,
                 attrs: dict[str, Any] | None = None, **kwargs) -> None:
        super().__init__(message, *args)

        self._attrs = {
            CruException.MESSAGE_KEY: message,
            CruException.INTERNAL_KEY: internal,
            CruException.INNER_KEY: inner,
            CruException.NAME_KEY: name,
            CruException.VALUE_KEY: value,
            CruException.PATH_KEY: path,
            CruException.TYPE_KEY: type_,
        }
        if init_attrs is not None:
            self._attrs.update(init_attrs)
        if attrs is not None:
            self._attrs.update(attrs)
        self._attrs.update(kwargs)

    @property
    def message(self) -> str:
        return self[CruException.MESSAGE_KEY]

    @property
    def internal(self) -> bool:
        return self[CruException.INTERNAL_KEY]

    @property
    def inner(self) -> list[Exception]:
        return self[CruException.INNER_KEY]

    @property
    def name(self) -> str | None:
        return self[CruException.NAME_KEY]

    @property
    def value(self) -> Any | None:
        return self[CruException.VALUE_KEY]

    @property
    def path(self) -> str | None:
        return self[CruException.PATH_KEY]

    @property
    def type(self) -> type | None:
        return self[CruException.TYPE_KEY]

    def _get_attr_list_recursive(self, name: str, depth: int, max_depth: int, l: list[Any]):
        if 0 < max_depth < depth + 1:
            return
        a = self._attrs.get(name, None)
        if a is not None:
            l.append(a)
        for i in self.inner:
            if isinstance(i, CruException):
                i._get_attr_list_recursive(name, depth + 1, max_depth, l)

    def get_attr_list_recursive(self, name: str, /, max_depth: int = -1) -> list[Any]:
        l = []
        self._get_attr_list_recursive(name, 0, max_depth, l)
        return l

    def get_optional_attr(self, name: str, max_depth: int = -1) -> Any | None:
        l = self.get_attr_list_recursive(name, max_depth)
        return l[0] if len(l) > 0 else None

    def __getitem__(self, name: str) -> Any | None:
        return self.get_optional_attr(name)


class CruInternalLogicError(CruException):
    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(message, *args, internal=True, **kwargs)


class UserFriendlyException(CruException):
    USER_MESSAGE_KEY = "user_message"

    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register(
        CruExceptionAttrDef(USER_MESSAGE_KEY, "Message describing the exception, but with user-friendly language."))

    def __init__(self, message: str, user_message: str | None = None, *args, **kwargs) -> None:
        if user_message is None:
            user_message = message
        super().__init__(message, *args, init_attrs={UserFriendlyException.USER_MESSAGE_KEY: user_message}, **kwargs)

    @property
    def user_message(self) -> str:
        return self[UserFriendlyException.USER_MESSAGE_KEY]
