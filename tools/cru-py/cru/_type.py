from collections.abc import Iterable
from typing import Any

from ._error import CruException, CruInternalError
from ._iter import CruIterator


class CruTypeCheckError(CruException):
    pass


DEFAULT_NONE_ERR_MSG = "None is not allowed here."
DEFAULT_TYPE_ERR_MSG = "Object of this type is not allowed here."


class CruTypeSet(set[type]):
    def __init__(self, *types: type):
        type_set = CruIterator(types).filter(lambda t: t is not None).to_set()
        if not CruIterator(type_set).all(lambda t: isinstance(t, type)):
            raise CruInternalError("TypeSet can only contain type.")
        super().__init__(type_set)

    def check_value(
        self,
        value: Any,
        /,
        allow_none: bool = False,
        empty_allow_all: bool = True,
    ) -> None:
        if value is None:
            if allow_none:
                return
            else:
                raise CruTypeCheckError(DEFAULT_NONE_ERR_MSG)
        if len(self) == 0 and empty_allow_all:
            return
        if not CruIterator(self).any(lambda t: isinstance(value, t)):
            raise CruTypeCheckError(DEFAULT_TYPE_ERR_MSG)

    def check_value_list(
        self,
        values: Iterable[Any],
        /,
        allow_none: bool = False,
        empty_allow_all: bool = True,
    ) -> None:
        for value in values:
            self.check_value(
                value,
                allow_none,
                empty_allow_all,
            )
