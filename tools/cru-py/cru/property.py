import json
from typing import Any


class PropertyItem:
    def __init__(self, value: Any):
        self._value = value

    @property
    def value(self) -> Any:
        return self._value

    @value.setter
    def value(self, value: Any):
        self._value = value


class PropertyTreeSection:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}

class PropertyTree:
    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data = data or {}