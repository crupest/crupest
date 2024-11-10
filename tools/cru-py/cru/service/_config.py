from ._base import AppFeaturePath, AppFeatureProvider
from ._data import DataManager


class ConfigManager(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("config-manager")

    def setup(self) -> None:
        self._config_path = self.app.get_feature(DataManager).data_dir.add_subpath(
            "config", False, description="Configuration file path."
        )

    @property
    def config_path(self) -> AppFeaturePath:
        return self._config_path

    @property
    def config_map(self) -> dict[str, str]:
        raise NotImplementedError()
