from pathlib import Path

from cru import CruException

from ._base import AppBase, DATA_DIR_NAME, CommandDispatcher
from ._config import ConfigManager
from ._data import DataManager
from ._template import TemplateManager


class App(AppBase):
    def __init__(self, root: str):
        super().__init__("crupest-service", root)
        self.add_feature(DataManager())
        self.add_feature(ConfigManager())
        self.add_feature(TemplateManager())
        self.add_feature(CommandDispatcher())

    def setup(self):
        for feature in self.features:
            feature.setup()

    def run_command(self):
        command_dispatcher = self.get_feature(CommandDispatcher)
        command_dispatcher.run_command()


def _find_root() -> Path:
    cwd = Path.cwd()
    data_dir = cwd / DATA_DIR_NAME
    if data_dir.is_dir():
        return data_dir
    raise CruException(
        "No valid data directory found. Please run 'init' to create one."
    )


def create_app() -> App:
    root = _find_root()
    app = App(str(root))
    app.setup()
    return app


def main():
    app = create_app()
    app.run_command()


if __name__ == "__main__":
    main()
