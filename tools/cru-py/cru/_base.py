from typing import Any

from ._helper import remove_none
from ._error import CruException


class CruNamespaceError(CruException):
    """Raised when a namespace is not found."""


class _Cru:
    NAME_PREFIXES = ("CRU_", "Cru", "cru_")

    def __init__(self) -> None:
        self._d: dict[str, Any] = {}

    def all_names(self) -> list[str]:
        return list(self._d.keys())

    def get(self, name: str) -> Any:
        return self._d[name]

    def has_name(self, name: str) -> bool:
        return name in self._d

    @staticmethod
    def _maybe_remove_prefix(name: str) -> str | None:
        for prefix in _Cru.NAME_PREFIXES:
            if name.startswith(prefix):
                return name[len(prefix) :]
        return None

    def _check_name_exist(self, *names: str | None) -> None:
        for name in names:
            if name is None:
                continue
            if self.has_name(name):
                raise CruNamespaceError(f"Name {name} exists in CRU.")

    @staticmethod
    def check_name_format(name: str) -> tuple[str, str]:
        no_prefix_name = _Cru._maybe_remove_prefix(name)
        if no_prefix_name is None:
            raise CruNamespaceError(
                f"Name {name} is not prefixed with any of {_Cru.NAME_PREFIXES}."
            )
        return name, no_prefix_name

    @staticmethod
    def _check_object_name(o) -> tuple[str, str]:
        return _Cru.check_name_format(o.__name__)

    def _do_add(self, o, *names: str | None) -> list[str]:
        name_list: list[str] = remove_none(names)
        for name in name_list:
            self._d[name] = o
        return name_list

    def add(self, o, name: str | None) -> tuple[str, str | None]:
        no_prefix_name: str | None
        if name is None:
            name, no_prefix_name = self._check_object_name(o)
        else:
            no_prefix_name = self._maybe_remove_prefix(name)

        self._check_name_exist(name, no_prefix_name)
        self._do_add(o, name, no_prefix_name)
        return name, no_prefix_name

    def add_with_alias(self, o, name: str | None = None, *aliases: str) -> list[str]:
        final_names: list[str | None] = []
        no_prefix_name: str | None
        if name is None:
            name, no_prefix_name = self._check_object_name(o)
            self._check_name_exist(name, no_prefix_name)
            final_names.extend([name, no_prefix_name])
        for alias in aliases:
            no_prefix_name = self._maybe_remove_prefix(alias)
            self._check_name_exist(alias, no_prefix_name)
            final_names.extend([alias, no_prefix_name])

        return self._do_add(o, *final_names)

    def add_objects(self, *objects):
        final_list = []
        for o in objects:
            name, no_prefix_name = self._check_object_name(o)
            self._check_name_exist(name, no_prefix_name)
            final_list.append((o, name, no_prefix_name))
        for o, name, no_prefix_name in final_list:
            self._do_add(o, name, no_prefix_name)

    def __getitem__(self, item):
        return self.get(item)

    def __getattr__(self, item):
        return self.get(item)


CRU_NAME_PREFIXES = _Cru.NAME_PREFIXES
CRU = _Cru()
