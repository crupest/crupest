from cru.app import ApplicationPath
from ._base import AppFeatureProvider


class DataManager(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("data-manager")
        self._dir = self.add_app_path("data", True)

    @property
    def data_dir(self) -> ApplicationPath:
        return self._dir
