import os.path
from ._base import AppFeatureProvider
from ._data import DataManager


class ConfigManager(AppFeatureProvider):
    def __init__(self, config_file_name="config") -> None:
        super().__init__("config-manager")
        self._file_name = config_file_name

    @property
    def config_file_path(self) -> str:
        return os.path.join(
            self.app.get_feature(DataManager).data_dir.full_path, self._file_name
        )
