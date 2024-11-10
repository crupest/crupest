from pathlib import Path

from ._error import CruException


class CruPathError(CruException):
    def __init__(self, message, _path: Path, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._path = _path

    @property
    def path(self) -> Path:
        return self._path


class CruPath(Path):
    def check_parents_dir(self, must_exist: bool = False) -> bool:
        for p in reversed(self.parents):
            if not p.exists() and not must_exist:
                return False
            if not p.is_dir():
                raise CruPathError("Parents path must be a dir.", self)
        return True
