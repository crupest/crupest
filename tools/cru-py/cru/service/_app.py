from ._base import (
    AppBase,
    CommandDispatcher,
    AppInitializer,
    PathCommandProvider,
)
from ._config import ConfigManager
from ._data import DataManager
from ._template import TemplateManager
from ._nginx import NginxManager

APP_ID = "crupest"


class App(AppBase):
    def __init__(self):
        super().__init__(APP_ID, f"{APP_ID}-service")
        self.add_feature(PathCommandProvider())
        self.add_feature(AppInitializer())
        self.add_feature(DataManager())
        self.add_feature(ConfigManager())
        self.add_feature(TemplateManager())
        self.add_feature(NginxManager())
        self.add_feature(CommandDispatcher())

    def run_command(self):
        command_dispatcher = self.get_feature(CommandDispatcher)
        command_dispatcher.run_command()


def create_app() -> App:
    app = App()
    app.setup()
    return app
