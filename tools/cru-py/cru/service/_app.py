from ._base import AppBase, CommandDispatcher, AppInitializer, OWNER_NAME
from ._config import ConfigManager
from ._data import DataManager
from ._template import TemplateManager


class App(AppBase):
    def __init__(self):
        super().__init__(f"{OWNER_NAME}-service")
        self.add_feature(AppInitializer())
        self.add_feature(DataManager())
        self.add_feature(ConfigManager())
        self.add_feature(TemplateManager())
        self.add_feature(CommandDispatcher())

    def run_command(self):
        command_dispatcher = self.get_feature(CommandDispatcher)
        command_dispatcher.run_command()


def create_app() -> App:
    app = App()
    app.setup()
    return app
