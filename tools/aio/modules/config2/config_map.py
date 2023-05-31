from typing import Any
from .config_var import ConfigVar
from ..common import UserFriendlyException


def line_number_to_str(line_number: int | None) -> str:
    return str(line_number) if line_number is not None else "UNKNOWN"


class ConfigItem:
    def __init__(self, name: str, value: Any, *, config_var: ConfigVar | None = None, line_number: int | None = None):
        self.name = name
        self.value = value
        self.config_var = config_var
        self.line_number = line_number

    @property
    def value_str(self) -> str:
        return str(self.value)

    @property
    def line_number_str(self) -> str:
        return line_number_to_str(self.line_number)

    def __str__(self):
        return f"{self.name}={self.value_str}"

    def __getitem__(self, key) -> Any:
        match key:
            case "name":
                return self.name
            case "value":
                return self.value
            case "config_var":
                return self.config_var
            case 0:
                return self.name
            case 1:
                return self.value
            case 2:
                return self.config_var
            case _:
                raise KeyError(f"Invalid key: {key}")


class ConfigMap:
    @ staticmethod
    def parse_config_to_tuple(s: str) -> list[tuple[str, str, int]]:
        config_items: list[tuple[str, str, int]] = []
        for line_number, line in enumerate(s.splitlines()):
            # check if it's a comment
            if line.strip().startswith("#"):
                continue
            # check if there is a '='
            if line.find("=") == -1:
                raise UserFriendlyException(
                    f"Invalid config line. Please check line {line_number + 1}. There is even no '='!")
            # split at first '='
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            config_items.append((key, value, line_number + 1))
        return config_items

    def __init__(self):
        self.items: list[ConfigItem] = []

    def _add_item_hook(self, config_item: ConfigItem):
        pass

    def clear(self) -> None:
        self.items.clear()

    def load_from_str(self, s: str) -> "ConfigMap":
        l = ConfigMap.parse_config_to_tuple(s)
        for name, value, line_number in l:
            try:
                self.add_item(name, value, line_number=line_number)
            except UserFriendlyException as e:
                raise UserFriendlyException(
                    f"Invalid config line. Please check line {line_number}.") from e
        return self

    def load_from_file(self, path: str) -> "ConfigMap":
        with open(path, 'r') as f:
            return self.load_from_str(f.read())

    def write_to_str(self) -> str:
        return "\n".join([str(item) for item in self.items])

    def write_to_file(self, path: str):
        with open(path, 'w') as f:
            f.write(self.write_to_str())

    def get_optional_item(self, name: str) -> ConfigItem | None:
        for item in self.items:
            if item.name == name:
                return item
        return None

    def add_item(self, name: str, value: Any, *, line_number=None) -> ConfigItem:
        i = self.get_optional_item(name)
        if i is not None:
            raise UserFriendlyException(
                f"Config item with name {name} already exists, which is at line {i.line_number_str}.")

        item = ConfigItem(name, value, line_number=line_number)

        self._add_item_hook(item)

        self.items.append(item)
        return item

    def copy(self) -> "ConfigMap":
        new = ConfigMap()
        new.items = self.items.copy()
        return new

    def __str__(self):
        return self.write_to_str()

    def to_dict(self) -> dict[str, str]:
        return {item.name: item.value for item in self.items}
