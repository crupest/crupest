from typing import Any

from .attr import CruAttrDefRegistry, CruAttr, CruAttrTable
from ._util import CRU_NOT_FOUND, CruList, CRU_USE_DEFAULT

CRU_EXCEPTION_ATTR_DEF_REGISTRY = CruAttrDefRegistry()


class CruException(Exception):
    ATTR_REGISTRY = CRU_EXCEPTION_ATTR_DEF_REGISTRY

    MESSAGE_KEY = "message"
    INNER_KEY = "inner"
    INTERNAL_KEY = "internal"
    NAME_KEY = "name"
    VALUE_KEY = "value"
    PATH_KEY = "path"
    TYPE_KEY = "type_"

    ATTR_REGISTRY.make_builder(MESSAGE_KEY, "Message describing the exception.").with_constraint(True, str,
                                                                                                 "").build()
    ATTR_REGISTRY.make_builder(INNER_KEY, "Inner exception.").with_constraint(True, Exception,
                                                                              auto_list=True).build()
    ATTR_REGISTRY.make_builder(INTERNAL_KEY,
                               "True if the exception is caused by wrong internal logic. False if it is caused by user's wrong input.").with_constraint(
        True, bool, False).build()
    ATTR_REGISTRY.make_builder(NAME_KEY, "Name of the object that causes the exception.").with_types(str).build()
    ATTR_REGISTRY.make_builder(VALUE_KEY, "Value that causes the exception.").build()
    ATTR_REGISTRY.make_builder(PATH_KEY, "Path that causes the exception.").with_types(str).build()
    ATTR_REGISTRY.make_builder(TYPE_KEY, "Python type related to the exception.").with_types(type).build()

    def __init__(self, message: str, *args,
                 init_attrs: list[CruAttr] | dict[str, Any] | None = None,
                 attrs: list[CruAttr] | dict[str, Any] | None = None, **kwargs) -> None:
        super().__init__(message, *args)

        self._attrs: CruAttrTable = CruAttrTable(self.ATTR_REGISTRY)

        self._attrs.add_value(CruException.MESSAGE_KEY, message)
        if init_attrs is not None:
            self._attrs.extend_with(init_attrs, True)
        if attrs is not None:
            self._attrs.extend_with(attrs, True)
        self._attrs.extend_with(dict(kwargs), True)

    @property
    def attrs(self) -> CruAttrTable:
        return self._attrs

    def get_attr(self, name: str) -> Any:
        return self._attrs.get_value_or(name, None)

    @property
    def message(self) -> str:
        return self.get_attr(CruException.MESSAGE_KEY)

    @property
    def internal(self) -> bool:
        return self.get_attr(CruException.INTERNAL_KEY)

    @property
    def inner(self) -> list[Exception]:
        return self.get_attr(CruException.INNER_KEY)

    @property
    def name(self) -> str | None:
        return self.get_attr(CruException.NAME_KEY)

    @property
    def value(self) -> Any | None:
        return self.get_attr(CruException.VALUE_KEY)

    @property
    def path(self) -> str | None:
        return self.get_attr(CruException.PATH_KEY)

    @property
    def type_(self) -> type | None:
        return self.get_attr(CruException.TYPE_KEY)

    def _get_attr_list_recursive(self, name: str, depth: int, max_depth: int, l: list[Any]):
        if 0 < max_depth < depth + 1:
            return
        a = self._attrs.get_or(name)
        if a is not CRU_NOT_FOUND:
            l.append(a)
        for i in self.inner:
            if isinstance(i, CruException):
                i._get_attr_list_recursive(name, depth + 1, max_depth, l)

    def get_attr_list_recursive(self, name: str, /, max_depth: int = -1, des: type = CruList) -> list[Any]:
        l = []
        self._get_attr_list_recursive(name, 0, max_depth, l)
        return des(l)


class CruInternalLogicError(CruException):
    def __init__(self, message: str, *args, **kwargs) -> None:
        super().__init__(message, *args, internal=True, **kwargs)


class UserFriendlyException(CruException):
    USER_MESSAGE_KEY = "user_message"

    CruException.ATTR_REGISTRY.make_builder(USER_MESSAGE_KEY,
                                            "Message describing the exception, but with user-friendly language.").with_types(
        str).build()

    def __init__(self, message: str, user_message: str | None = CRU_USE_DEFAULT, *args, **kwargs) -> None:
        if user_message is None:
            user_message = message
        super().__init__(message, *args, init_attrs={UserFriendlyException.USER_MESSAGE_KEY: user_message}, **kwargs)

    @property
    def user_message(self) -> str:
        return self.get_attr(UserFriendlyException.USER_MESSAGE_KEY)
