from typing import Any

from .attr import CruAttrDefRegistry, CRU_ATTR_USE_DEFAULT, CruAttr, CruAttrTable
from .util import CanBeList

CRU_EXCEPTION_ATTR_DEF_REGISTRY = CruAttrDefRegistry()
_REGISTRY = CRU_EXCEPTION_ATTR_DEF_REGISTRY


class CruException(Exception, CruAttrTable):
    MESSAGE_KEY = "message"
    INNER_KEY = "inner"
    INTERNAL_KEY = "internal"
    NAME_KEY = "name"
    VALUE_KEY = "value"
    PATH_KEY = "path"
    TYPE_KEY = "type_"

    _REGISTRY.make_builder(MESSAGE_KEY, "Message describing the exception.").with_constraint(True, str,
                                                                                             "").build()
    _REGISTRY.make_builder("inner", "Inner exception.").with_constraint(True, Exception,
                                                                        auto_list=True).build()
    _REGISTRY.make_builder("internal",
                           "True if the exception is caused by wrong internal logic. False if it is caused by user's wrong input.").with_constraint(
        True, bool, False).build()
    _REGISTRY.make_builder(NAME_KEY, "Name of the object that causes the exception.").with_types(str).build()
    _REGISTRY.make_builder(VALUE_KEY, "Value that causes the exception.").build()
    _REGISTRY.make_builder(PATH_KEY, "Path that causes the exception.").with_types(str).build()
    _REGISTRY.make_builder(TYPE_KEY, "Python type related to the exception.").with_types(type).build()

    # TODO: CONTINUE HERE TOMORROW!
    def __init__(self, message: str, *args,
                 init_attrs: dict[str, Any] | None = None,
                 attrs: dict[str, Any] | None = None, **kwargs) -> None:
        super().__init__(message, *args)

        self._attrs = {
            CruException.MESSAGE_KEY: message,
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
