from ._base import AppFeaturePath, AppFeatureProvider
from ._data import DataManager


class ConfigManager(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("config-manager")
        self._config_path = self.app.get_feature(DataManager).data_dir.add_subpath(
            "config", False, description="Configuration file path."
        )

    @property
    def config_path(self) -> AppFeaturePath:
        return self._config_path
