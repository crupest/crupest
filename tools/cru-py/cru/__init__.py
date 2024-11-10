import sys

from ._base import CRU, CruNamespaceError, CRU_NAME_PREFIXES
from ._error import (
    cru_unreachable,
    CruException,
    CruUserFriendlyException,
    CruInternalError,
    CruUnreachableError,
)
from ._const import (
    CruConstantBase,
    CruDontChange,
    CruNotFound,
    CruNoValue,
    CruPlaceholder,
    CruUseDefault,
)
from ._func import CruFunction
from ._iter import CruIterable, CruIterator
from ._event import CruEvent, CruEventHandlerToken
from ._path import CruPath, CruPathError
from ._type import CruTypeSet, CruTypeCheckError


class CruInitError(CruException):
    pass


def check_python_version(required_version=(3, 11)):
    if sys.version_info < required_version:
        raise CruInitError(f"Python version must be >= {required_version}!")


check_python_version()

__all__ = [
    "CRU",
    "CruNamespaceError",
    "CRU_NAME_PREFIXES",
    "check_python_version",
    "CruException",
    "cru_unreachable",
    "CruInitError",
    "CruUserFriendlyException",
    "CruInternalError",
    "CruUnreachableError",
    "CruConstantBase",
    "CruDontChange",
    "CruNotFound",
    "CruNoValue",
    "CruPlaceholder",
    "CruUseDefault",
    "CruFunction",
    "CruIterable",
    "CruIterator",
    "CruEvent",
    "CruEventHandlerToken",
    "CruPath",
    "CruPathError",
    "CruTypeSet",
    "CruTypeCheckError",
]
