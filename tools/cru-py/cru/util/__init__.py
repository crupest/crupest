from typing import Any

from ._const import cru_make_unique_object, cru_make_bool_unique_object, CRU_NOT_FOUND, CRU_USE_DEFAULT, \
    CRU_DONT_CHANGE, \
    CRU_PLACEHOLDER
from ._func import CruFunction, CruFunctionMeta, CruRawFunctions, CruWrappedFunctions, CruFunctionGenerators
from ._list import CruList, CruInplaceList, CruUniqueKeyInplaceList, ListOperations, CanBeList, ElementOperation, \
    ElementPredicate, ElementTransformer, OptionalElementOperation, ElementPredicate, OptionalElementTransformer
from ._type import TypeSet

F = CruFunction
WF = CruWrappedFunctions
FG = CruFunctionGenerators
L = CruList


__all__ = [
    "CRU_NOT_FOUND", "CRU_USE_DEFAULT", "CRU_DONT_CHANGE", "CRU_PLACEHOLDER",
    "CruFunction", "CruFunctionMeta", "CruRawFunctions", "CruWrappedFunctions", "CruFunctionGenerators",
    "CruList", "CruInplaceList", "CruUniqueKeyInplaceList", "ListOperations",
    "CanBeList", "ElementOperation", "ElementPredicate", "ElementTransformer",
    "OptionalElementOperation", "ElementPredicate", "OptionalElementTransformer",
    "TypeSet",
    "F", "WF", "FG", "L"
]
