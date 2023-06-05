from typing import Optional, Union, Tuple, Any
from config_var import ConfigVar, check_config_vars
from ..paths import config_file_path
import os.path


class ConfigItem:
    def __init__(self, config_var: ConfigVar, value: Any,  *, line_number: Optional[int] = None):
        config_var.check_value_type(value)
        self.config_var = config_var
        self.value = value
        self.line_number = line_number

    @property
    def name(self) -> str:
        return self.config_var.name

    @property
    def value_str(self) -> str:
        return self.config_var.convert_value_to_str(self.value)

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
    def parse_config_items(s: str) -> list[Tuple[str, str, int]]:
        config_items: list[Tuple[str, str, int]] = []
        for line_number, line in enumerate(s.splitlines()):
            # check if it's a comment
            if line.strip().startswith("#"):
                continue
            # check if there is a '='
            if line.find("=") == -1:
                raise Exception(
                    f"Invalid config string. Please check line {line_number + 1}. There is even no '='!")
            # split at first '='
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            config_items.append((key, value, line_number))
        return config_items

    def __init__(self, config_vars: list[ConfigVar]):
        check_config_vars(config_vars)
        self.vars = config_vars
        self.items: list[ConfigItem] = []

    def clear(self) -> None:
        self.items.clear()

    def load_from_str(self, s: str) -> None:
        l = ConfigMap.parse_config_items(s)
        for name, value, line_number in l:
            self.add_item(name, value, line_number=line_number)

    def load_from_file(self, path: Optional[str] = None):
        if path is None:
            path = config_file_path
        with open(path, 'r') as f:
            self.load_from_str(f.read())

    def write_to_str(self) -> str:
        return "\n".join([str(item) for item in self.items])

    def write_to_file(self, path: Optional[str] = None, raise_on_exist: bool = True):
        if path is None:
            path = config_file_path

        if raise_on_exist and os.path.exists(path):
            raise Exception(f"Config file {path} already exists!")

        with open(path, 'w') as f:
            f.write(self.write_to_str())

    def get_optional_config_var(self, v: Union[str, ConfigVar]) -> Optional[ConfigVar]:
        if isinstance(v, ConfigVar):
            name = v.name
        else:
            name = v
        for var in self.vars:
            if var.name == name:
                return var
        return None

    def get_optional_item(self, v: Union[str, ConfigVar]) -> Optional[ConfigItem]:
        if isinstance(v, ConfigVar):
            name = v.name
        else:
            name = v
        for item in self.items:
            if item.name == name:
                return item
        return None

    def add_item(self, name: str, value: Union[str, Any], *, line_number=None) -> ConfigItem:
        v = self.get_optional_config_var(name)
        if v is None:
            raise Exception(
                f"Invalid config item name: {name} at line {line_number}!")
        i = self.get_optional_item(name)
        if i is not None:
            raise Exception(
                f"Config item with name {name} already exists, exist one at line {line_number}, the one trying to add is at line {i.line_number}!")

        if isinstance(value, str):
            value = v.convert_str_to_value(value)
        else:
            v.check_value_type(value)

        item = ConfigItem(v, value, line_number=line_number)
        self.items.append(item)
        return item

    @property
    def undefined_vars(self) -> list[ConfigVar]:
        return [var for var in self.vars if self.get_optional_item(var) is None]

    def __str__(self):
        return self.write_to_str()
