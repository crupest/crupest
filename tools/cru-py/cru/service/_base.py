from argparse import ArgumentParser, Namespace
from typing import Protocol
from cru.app import ApplicationPath, CruApplication


class AppFunction(Protocol):
    @property
    def name(self) -> str: ...

    def add_arg_parser(self, arg_parser: ArgumentParser) -> None: ...

    def run_command(self, args: Namespace) -> None: ...


class AppBase(CruApplication):
    def __init__(self, name: str, app_dir: str):
        super().__init__(name)
        self._app_dir = app_dir
        self._template_dir = ApplicationPath(app_dir, "templates", True)

    @property
    def app_dir(self) -> str:
        return self._app_dir
