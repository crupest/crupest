from __future__ import annotations

from argparse import ArgumentParser, Namespace
from abc import ABC, abstractmethod
import argparse
from collections.abc import Sequence
import os
from pathlib import Path
from typing import TypeVar, overload

from cru import CruException, CruInternalError, CruPath

_F = TypeVar("_F")

OWNER_NAME = "crupest"


class InternalAppException(CruInternalError):
    pass


class AppPathError(CruException):
    def __init__(self, message, _path: str | Path, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._path = str(_path)

    @property
    def path(self) -> str:
        return self._path


class AppPath(ABC):
    def __init__(
        self,
        name: str,
        is_dir: bool,
        /,
        id: str | None = None,
        description: str = "",
    ) -> None:
        self._name = name
        self._is_dir = is_dir
        self._id = id or name
        self._description = description

    @property
    @abstractmethod
    def parent(self) -> AppPath | None: ...

    @property
    def name(self) -> str:
        return self._name

    @property
    @abstractmethod
    def app(self) -> AppBase: ...

    @property
    def id(self) -> str:
        return self._id

    @property
    def description(self) -> str:
        return self._description

    @property
    def is_dir(self) -> bool:
        return self._is_dir

    @property
    def full_path(self) -> CruPath:
        if self.parent is None:
            return CruPath(self.name)
        else:
            return CruPath(self.parent.full_path, self.name)

    @property
    def full_path_str(self) -> str:
        return str(self.full_path)

    def check_parents(self, must_exist: bool = False) -> bool:
        return self.full_path.check_parents_dir(must_exist)

    def check_self(self, must_exist: bool = False) -> bool:
        if not self.check_parents(must_exist):
            return False
        if not self.full_path.exists():
            if not must_exist:
                return False
            raise AppPathError("Not exist.", self.full_path)
        if self.is_dir:
            if not self.full_path.is_dir():
                raise AppPathError("Should be a directory, but not.", self.full_path)
            else:
                return False
        else:
            if not self.full_path.is_file():
                raise AppPathError("Should be a file, but not.", self.full_path)
            else:
                return False

    def ensure(self, create_file: bool = False) -> None:
        e = self.check_self(False)
        if not e:
            os.makedirs(self.full_path.parent, exist_ok=True)
            if self.is_dir:
                os.mkdir(self.full_path)
            elif create_file:
                with open(self.full_path, "w") as f:
                    f.write("")

    def add_subpath(
        self,
        name: str,
        is_dir: bool,
        /,
        id: str | None = None,
        description: str = "",
    ) -> AppFeaturePath:
        return self.app.add_path(name, is_dir, self, id, description)


class AppFeaturePath(AppPath):
    def __init__(
        self,
        parent: AppPath,
        name: str,
        is_dir: bool,
        /,
        id: str | None = None,
        description: str = "",
    ) -> None:
        super().__init__(name, is_dir, id, description)
        self._parent = parent

    @property
    def parent(self) -> AppPath:
        return self._parent

    @property
    def app(self) -> AppBase:
        return self.parent.app


class AppRootPath(AppPath):
    def __init__(self, app: AppBase, path: str):
        super().__init__(path, True, "root", "Application root path.")
        self._app = app

    @property
    def parent(self) -> None:
        return None

    @property
    def app(self) -> AppBase:
        return self._app


class AppFeatureProvider(ABC):
    def __init__(self, name: str, /, app: AppBase | None = None):
        super().__init__()
        self._name = name
        self._app = app if app else AppBase.get_instance()
        self.app.add_feature(self)

    @property
    def app(self) -> AppBase:
        return self._app

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def setup(self) -> None: ...


class AppCommandFeatureProvider(AppFeatureProvider):
    @abstractmethod
    def get_command_info(self) -> tuple[str, str]: ...

    @abstractmethod
    def setup_arg_parser(self, arg_parser: ArgumentParser): ...

    @abstractmethod
    def run_command(self, args: Namespace) -> None: ...


DATA_DIR_NAME = "data"


class CommandDispatcher(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("command-dispatcher")

    def _setup_arg_parser(self) -> None:
        self._map: dict[str, AppCommandFeatureProvider] = {}
        arg_parser = argparse.ArgumentParser(description="Service management")
        subparsers = arg_parser.add_subparsers(dest="command")
        for feature in self.app.features:
            if isinstance(feature, AppCommandFeatureProvider):
                info = feature.get_command_info()
                command_subparser = subparsers.add_parser(info[0], help=info[1])
                feature.setup_arg_parser(command_subparser)
                self._map[info[0]] = feature
        self._arg_parser = arg_parser

    def setup(self):
        self._setup_arg_parser()

    @property
    def arg_parser(self) -> argparse.ArgumentParser:
        return self._arg_parser

    @property
    def map(self) -> dict[str, AppCommandFeatureProvider]:
        return self._map

    def run_command(self, _args: Sequence[str] | None = None) -> None:
        args = self.arg_parser.parse_args(_args)
        self.map[args.command].run_command(args)


class AppBase:
    _instance: AppBase | None = None

    @staticmethod
    def get_instance() -> AppBase:
        if AppBase._instance is None:
            raise CruInternalError("App instance not initialized")
        return AppBase._instance

    def __init__(self, name: str, root: str):
        AppBase._instance = self
        self._name = name
        self._root = AppRootPath(self, root)
        self._paths: list[AppFeaturePath] = []
        self._features: list[AppFeatureProvider] = []

    @property
    def name(self) -> str:
        return self._name

    @property
    def root(self) -> AppRootPath:
        return self._root

    @property
    def features(self) -> list[AppFeatureProvider]:
        return self._features

    @property
    def paths(self) -> list[AppFeaturePath]:
        return self._paths

    def add_feature(self, feature: AppFeatureProvider) -> AppFeatureProvider:
        self._features.append(feature)
        return feature

    def add_path(
        self,
        name: str,
        is_dir: bool,
        /,
        parent: AppPath | None = None,
        id: str | None = None,
        description: str = "",
    ) -> AppFeaturePath:
        p = AppFeaturePath(
            parent or self.root, name, is_dir, id=id, description=description
        )
        self._paths.append(p)
        return p

    @overload
    def get_feature(self, feature: str) -> AppFeatureProvider: ...

    @overload
    def get_feature(self, feature: type[_F]) -> _F: ...

    def get_feature(self, feature: str | type[_F]) -> AppFeatureProvider | _F:
        if isinstance(feature, str):
            for f in self._features:
                if f.name == feature:
                    return f
        elif isinstance(feature, type):
            for f in self._features:
                if isinstance(f, feature):
                    return f
        else:
            raise InternalAppException(
                "Argument must be the name of feature or its class."
            )

        raise InternalAppException(f"Feature {feature} not found.")

    def get_path(self, name: str) -> AppFeaturePath:
        for p in self._paths:
            if p.id == name or p.name == name:
                return p
        raise InternalAppException(f"Application path {name} not found.")
