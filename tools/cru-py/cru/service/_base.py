from __future__ import annotations

from argparse import ArgumentParser, Namespace
from abc import ABC, abstractmethod
from collections.abc import Iterable

from cru import CruIterator, CruInternalError
from cru.app import ApplicationPath, CruApplication


class AppFeatureProvider(ABC):
    def __init__(self, name: str, /, app: AppBase | None = None):
        super().__init__()
        self._name = name
        self._app = app if app else AppBase.get_instance()
        self._app_paths: list[ApplicationPath] = []
        self.app.add_app_feature(self)

    @property
    def app(self) -> AppBase:
        return self._app

    @property
    def name(self) -> str:
        return self._name

    @property
    def app_paths(self) -> list[ApplicationPath]:
        return self._app_paths

    def add_app_path(self, subpath: str, is_dir: bool) -> ApplicationPath:
        p = ApplicationPath(self.app.app_dir, subpath, is_dir)
        self._app_paths.append(p)
        return p

    @abstractmethod
    def add_arg_parser(self, arg_parser: ArgumentParser) -> None: ...

    @abstractmethod
    def run_command(self, args: Namespace) -> None: ...


class AppBase(CruApplication):
    _instance: AppBase | None = None

    @staticmethod
    def get_instance() -> AppBase:
        if AppBase._instance is None:
            raise CruInternalError("App instance not initialized")
        return AppBase._instance

    def __init__(self, name: str, app_dir: str):
        super().__init__(name)
        AppBase._instance = self
        self._app_dir = app_dir
        self._app_features: list[AppFeatureProvider] = []

    @property
    def app_dir(self) -> str:
        return self._app_dir

    @property
    def app_features(self) -> list[AppFeatureProvider]:
        return self._app_features

    @property
    def app_paths(self) -> Iterable[ApplicationPath]:
        return (
            CruIterator(self._app_features).transform(lambda x: x.app_paths).flatten(1)
        )

    def add_app_feature(self, feature: AppFeatureProvider) -> None:
        self._app_features.append(feature)
