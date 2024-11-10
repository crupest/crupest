from ._base import AppFeaturePath, AppFeatureProvider


class DataManager(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("data-manager")

    def setup(self) -> None:
        self._dir = self.app.add_path("data", True)

    @property
    def data_dir(self) -> AppFeaturePath:
        return self._dir
