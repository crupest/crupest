from types import NoneType
from typing import Any

from ._list import CanBeList, CruList

DEFAULT_NONE_ERR = ValueError
DEFAULT_NONE_ERR_MSG = "None is not allowed here."
DEFAULT_TYPE_ERR = ValueError
DEFAULT_TYPE_ERR_MSG = "Type of object is not allowed here."


class TypeSet(set[type]):
    def __init__(self, *l: type):
        l = CruList.make(l).remove_all_value(None, NoneType)
        if not l.all_is_instance(type):
            raise TypeError("t must be a type or None.")
        super().__init__(l)

    def check_value(self, v: Any, /, allow_none: bool, empty_allow_all: bool = True, *,
                    none_err: type[Exception] = DEFAULT_NONE_ERR,
                    none_err_msg: str = DEFAULT_NONE_ERR_MSG,
                    type_err: type[Exception] = DEFAULT_TYPE_ERR,
                    type_err_msg: str = DEFAULT_TYPE_ERR_MSG) -> None:
        if v is None:
            if allow_none:
                return
            else:
                raise none_err(none_err_msg)
        if len(self) == 0 and empty_allow_all:
            return
        if type(v) not in self:
            raise type_err(type_err_msg)

    def check_value_list(self, l: CanBeList, /, allow_none: bool, empty_allow_all: bool = True, *,
                         none_err: type[Exception] = DEFAULT_NONE_ERR,
                         none_err_msg: str = DEFAULT_NONE_ERR_MSG,
                         type_err: type[Exception] = DEFAULT_TYPE_ERR,
                         type_err_msg: str = DEFAULT_TYPE_ERR_MSG) -> None:
        l = CruList.make(l)
        for v in l:
            self.check_value(v, allow_none, empty_allow_all, none_err=none_err, none_err_msg=none_err_msg,
                             type_err=type_err, type_err_msg=type_err_msg)
