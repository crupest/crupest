from __future__ import annotations

from argparse import ArgumentParser, Namespace
from abc import ABC, abstractmethod
import argparse
import os
from pathlib import Path
from typing import TypeVar, overload

from cru import CruException, CruLogicError, CruPath

_Feature = TypeVar("_Feature", bound="AppFeatureProvider")


class AppError(CruException):
    pass


class AppFeatureError(AppError):
    def __init__(self, message, feature: type | str, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._feature = feature

    @property
    def feature(self) -> type | str:
        return self._feature


class AppPathError(CruException):
    def __init__(self, message, _path: str | Path, *args, **kwargs):
        super().__init__(message, *args, **kwargs)
        self._path = str(_path)

    @property
    def path(self) -> str:
        return self._path


class AppPath(ABC):
    def __init__(self, id: str, is_dir: bool, description: str) -> None:
        self._is_dir = is_dir
        self._id = id
        self._description = description

    @property
    @abstractmethod
    def parent(self) -> AppPath | None: ...

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
    @abstractmethod
    def full_path(self) -> CruPath: ...

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
                return True
        else:
            if not self.full_path.is_file():
                raise AppPathError("Should be a file, but not.", self.full_path)
            else:
                return True

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

    @property
    def app_relative_path(self) -> CruPath:
        return self.full_path.relative_to(self.app.root.full_path)


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
        super().__init__(id or name, is_dir, description)
        self._name = name
        self._parent = parent

    @property
    def name(self) -> str:
        return self._name

    @property
    def parent(self) -> AppPath:
        return self._parent

    @property
    def app(self) -> AppBase:
        return self.parent.app

    @property
    def full_path(self) -> CruPath:
        return CruPath(self.parent.full_path, self.name).resolve()


class AppRootPath(AppPath):
    def __init__(self, app: AppBase):
        super().__init__("root", True, "Application root path.")
        self._app = app
        self._full_path: CruPath | None = None

    @property
    def parent(self) -> None:
        return None

    @property
    def app(self) -> AppBase:
        return self._app

    @property
    def full_path(self) -> CruPath:
        if self._full_path is None:
            raise AppError("App root path is not set yet.")
        return self._full_path

    def setup(self, path: os.PathLike) -> None:
        if self._full_path is not None:
            raise AppError("App root path is already set.")
        self._full_path = CruPath(path).resolve()


class AppFeatureProvider(ABC):
    def __init__(self, name: str, /, app: AppBase | None = None):
        super().__init__()
        self._name = name
        self._app = app if app else AppBase.get_instance()

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


class PathCommandProvider(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("path-command-provider")

    def setup(self):
        pass

    def get_command_info(self):
        return ("path", "Get information about paths used by app.")

    def setup_arg_parser(self, arg_parser: ArgumentParser) -> None:
        subparsers = arg_parser.add_subparsers(
            dest="path_command", required=True, metavar="PATH_COMMAND"
        )
        _list_parser = subparsers.add_parser(
            "list", help="list special paths used by app"
        )

    def run_command(self, args: Namespace) -> None:
        if args.path_command == "list":
            for path in self.app.paths:
                print(f"{path.app_relative_path.as_posix()}: {path.description}")


class CommandDispatcher(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("command-dispatcher")
        self._parsed_args: argparse.Namespace | None = None

    def setup_arg_parser(self) -> None:
        epilog = """
==> to start,
./tools/manage init
./tools/manage config init
ln -s generated/docker-compose.yaml .
# Then edit config file.

==> to update
git pull
./tools/manage template generate --no-dry-run
docker compose up
        """.strip()

        self._map: dict[str, AppCommandFeatureProvider] = {}
        arg_parser = argparse.ArgumentParser(
            description="Service management",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog=epilog,
        )
        arg_parser.add_argument(
            "--project-dir",
            help="The path of the project directory.",
            required=True,
            type=str,
        )
        subparsers = arg_parser.add_subparsers(
            dest="command",
            help="The management command to execute.",
            metavar="COMMAND",
        )
        for feature in self.app.features:
            if isinstance(feature, AppCommandFeatureProvider):
                info = feature.get_command_info()
                command_subparser = subparsers.add_parser(info[0], help=info[1])
                feature.setup_arg_parser(command_subparser)
                self._map[info[0]] = feature
        self._arg_parser = arg_parser

    def setup(self):
        pass

    @property
    def arg_parser(self) -> argparse.ArgumentParser:
        return self._arg_parser

    @property
    def map(self) -> dict[str, AppCommandFeatureProvider]:
        return self._map

    def get_program_parsed_args(self) -> argparse.Namespace:
        if self._parsed_args is None:
            self._parsed_args = self.arg_parser.parse_args()
        return self._parsed_args

    def run_command(self, args: argparse.Namespace | None = None) -> None:
        real_args = args or self.get_program_parsed_args()
        if real_args.command is None:
            self.arg_parser.print_help()
            return
        self.map[real_args.command].run_command(real_args)


class AppInitializer(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("app-initializer")

    def _init_app(self) -> bool:
        if self.app.app_initialized:
            return False
        self.app.data_dir.ensure()
        return True

    def setup(self):
        pass

    def get_command_info(self):
        return ("init", "Initialize the app.")

    def setup_arg_parser(self, arg_parser):
        pass

    def run_command(self, args):
        init = self._init_app()
        if init:
            print("App initialized successfully.")
        else:
            print("App is already initialized. Do nothing.")


class AppBase:
    _instance: AppBase | None = None

    @staticmethod
    def get_instance() -> AppBase:
        if AppBase._instance is None:
            raise AppError("App instance not initialized")
        return AppBase._instance

    def __init__(self, app_id: str, name: str):
        AppBase._instance = self
        self._app_id = app_id
        self._name = name
        self._root = AppRootPath(self)
        self._paths: list[AppFeaturePath] = []
        self._features: list[AppFeatureProvider] = []

    def setup(self) -> None:
        command_dispatcher = self.get_feature(CommandDispatcher)
        command_dispatcher.setup_arg_parser()
        program_args = command_dispatcher.get_program_parsed_args()
        self.setup_root(program_args.project_dir)
        self._data_dir = self.add_path(DATA_DIR_NAME, True, id="data")
        for feature in self.features:
            feature.setup()
        for path in self.paths:
            path.check_self()

    @property
    def app_id(self) -> str:
        return self._app_id

    @property
    def name(self) -> str:
        return self._name

    @property
    def root(self) -> AppRootPath:
        return self._root

    def setup_root(self, path: os.PathLike) -> None:
        self._root.setup(path)

    @property
    def data_dir(self) -> AppFeaturePath:
        return self._data_dir

    @property
    def app_initialized(self) -> bool:
        return self.data_dir.check_self()

    def ensure_app_initialized(self) -> AppRootPath:
        if not self.app_initialized:
            raise AppError(
                user_message="Root directory does not exist. "
                "Please run 'init' to create one."
            )
        return self.root

    @property
    def features(self) -> list[AppFeatureProvider]:
        return self._features

    @property
    def paths(self) -> list[AppFeaturePath]:
        return self._paths

    def add_feature(self, feature: _Feature) -> _Feature:
        for f in self.features:
            if f.name == feature.name:
                raise AppFeatureError(
                    f"Duplicate feature name: {feature.name}.", feature.name
                )
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
    def get_feature(self, feature: type[_Feature]) -> _Feature: ...

    def get_feature(
        self, feature: str | type[_Feature]
    ) -> AppFeatureProvider | _Feature:
        if isinstance(feature, str):
            for f in self._features:
                if f.name == feature:
                    return f
        elif isinstance(feature, type):
            for f in self._features:
                if isinstance(f, feature):
                    return f
        else:
            raise CruLogicError("Argument must be the name of feature or its class.")

        raise AppFeatureError(f"Feature {feature} not found.", feature)

    def get_path(self, name: str) -> AppFeaturePath:
        for p in self._paths:
            if p.id == name or p.name == name:
                return p
        raise AppPathError(f"Application path {name} not found.", name)
