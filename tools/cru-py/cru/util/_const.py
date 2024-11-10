from typing import Any


def make_unique_object() -> Any:
    class _CruUnique:
        _i = False

        def __init__(self):
            if self._i:
                raise ValueError("_CruAttrNotSet is a singleton!")
            self._i = True

        def __copy__(self):
            return self

        def __eq__(self, other):
            return isinstance(other, _CruUnique)

    v = _CruUnique()

    return v


def make_bool_unique_object(b: bool) -> Any:
    class _CruBoolUnique:
        _i = False

        def __init__(self):
            super().__init__(b)
            if self._i:
                raise ValueError("_CruAttrNotSet is a singleton!")
            self._i = True

        def __copy__(self):
            return self

        def __eq__(self, other):
            return isinstance(other, _CruBoolUnique) or b == other

        def __bool__(self):
            return b

    v = _CruBoolUnique()

    return v


CRU_NOT_FOUND = make_bool_unique_object(False)
CRU_USE_DEFAULT = make_unique_object()
CRU_DONT_CHANGE = make_unique_object()
CRU_PLACEHOLDER = make_unique_object()
