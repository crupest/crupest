from ._base import AppFeatureProvider


class DataManager(AppFeatureProvider):
    def __init__(self) -> None:
        super().__init__("data-manager")

    def setup(self) -> None:
        pass
