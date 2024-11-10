import os
from pathlib import Path

from ._error import CruException
from ._path import CruPath


class CruApplication:
    def __init__(self, name: str) -> None:
        self._name = name


class ApplicationPathError(CruException):
    def __init__(self, message, _path: Path, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._path = _path

    @property
    def path(self) -> Path:
        return self._path


class ApplicationPath:
    def __init__(self, p: str | Path, is_dir: bool) -> None:
        self._path = CruPath(p)
        self._is_dir = is_dir

    @property
    def path(self) -> CruPath:
        return self._path

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    def check_parents(self, must_exist: bool = False) -> bool:
        return self._path.check_parents_dir(must_exist)

    def check_self(self, must_exist: bool = False) -> bool:
        if not self.check_parents(must_exist):
            return False
        if not self.path.exists():
            if not must_exist:
                return False
            raise ApplicationPathError("Not exist.", self.path)
        if self.is_dir:
            if not self.path.is_dir():
                raise ApplicationPathError("Should be a directory, but not.", self.path)
            else:
                return False
        else:
            if not self.path.is_file():
                raise ApplicationPathError("Should be a file, but not.", self.path)
            else:
                return False

    def ensure(self, create_file: bool = False) -> None:
        e = self.check_self(False)
        if not e:
            os.makedirs(self.path.parent, exist_ok=True)
            if self.is_dir:
                os.mkdir(self.path)
            elif create_file:
                with open(self.path, "w") as f:
                    f.write("")
