import os
from pathlib import Path

from .error import CruException


class ApplicationPathError(CruException):
    def __init__(self, message: str, p: str | Path, *args, **kwargs):
        super().__init__(message, *args, path=str(p), **kwargs)


def check_parents_dir(p: str | Path, /, must_exist: bool = False) -> bool:
    p = Path(p) if isinstance(p, str) else p
    for p in reversed(p.parents):
        if not p.exists() and not must_exist:
            return False
        if not p.is_dir():
            raise ApplicationPathError("Parents path should be a dir.", p)
    return True


class ApplicationPath:
    def __init__(self, p: str | Path, is_dir: bool) -> None:
        self._path = Path(p) if isinstance(p, str) else p
        self._is_dir = is_dir

    @property
    def path(self) -> Path:
        return self._path

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    def check_parents(self, must_exist: bool = False) -> bool:
        return check_parents_dir(self._path.parent, must_exist)

    def check_self(self, must_exist: bool = False) -> bool:
        if not self.check_parents(must_exist):
            return False
        if not self.path.exists():
            if not must_exist:
                return False
            raise ApplicationPathError("Mot exist.", self.path)
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
