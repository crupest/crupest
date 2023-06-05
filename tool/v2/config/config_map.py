from typing import Any, cast
import os.path
from config_var import ConfigVar, config_var_list, check_config_vars
from ..common import Paths, UserFriendlyException


class ConfigItem:
    """
    Item has two types.
    1. With ConfigVar, then value must be of the type required by the ConfigVar.
    2. Without ConfigVar, then value must be a str

    NOTE: This won't parse the str value to the type required by the ConfigVar. Please parse yourself and then init with it.
    """

    def __init__(self, config_var_or_name: ConfigVar | str, value: Any,  *, line_number: int | None = None):
        if isinstance(config_var_or_name, ConfigVar):
            config_var_or_name.check_value_type(value)
        else:
            if not isinstance(value, str):
                raise Exception(
                    f"Non-config-var item can only have a str value.")

        self.config_var_or_name = config_var_or_name
        self.value = value
        self.line_number = line_number

    @property
    def is_config_var(self) -> bool:
        return isinstance(self.config_var_or_name, ConfigVar)

    @property
    def config_var(self) -> ConfigVar:
        if self.is_config_var:
            return cast(ConfigVar, self.config_var_or_name)
        else:
            raise Exception("This config item is not a config var item!")

    @property
    def optional_config_var(self) -> ConfigVar | None:
        if self.is_config_var:
            return self.config_var
        else:
            return None

    @property
    def name(self) -> str:
        if self.is_config_var:
            return self.config_var.name
        else:
            return cast(str, self.config_var_or_name)

    @property
    def value_str(self) -> str:
        if self.is_config_var:
            return self.config_var.convert_value_to_str(self.value)
        else:
            return self.value

    def __str__(self):
        return f"{self.name}={self.value_str}"

    def __getitem__(self, key) -> Any:
        match key:
            case "name":
                return self.name
            case "value":
                return self.value
            case "config_var":
                return self.optional_config_var
            case 0:
                return self.name
            case 1:
                return self.value
            case 2:
                return self.optional_config_var
            case _:
                raise KeyError(f"Invalid key: {key}")


class ConfigMap:
    @ staticmethod
    def parse_config_items(s: str) -> list[tuple[str, str, int]]:
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

    def __init__(self, config_vars: list[ConfigVar] = config_var_list):
        check_config_vars(config_vars)
        self.vars = config_vars
        self.items: list[ConfigItem] = []

    def clear(self) -> None:
        self.items.clear()

    def load_from_str(self, s: str) -> "ConfigMap":
        l = ConfigMap.parse_config_items(s)
        for name, value, line_number in l:
            self.add_item(name, value, line_number=line_number)
        return self

    def load_from_file(self, path: str | None = None) -> "ConfigMap":
        if path is None:
            path = Paths.config_file_path
        with open(path, 'r') as f:
            return self.load_from_str(f.read())

    def write_to_str(self) -> str:
        return "\n".join([str(item) for item in self.items])

    def write_to_file(self, path: str | None = None, raise_on_exist: bool = True):
        if path is None:
            path = Paths.config_file_path

        if raise_on_exist and os.path.exists(path):
            raise Exception(
                f"Config file {path} already exists, be careful to overwrite it!")

        with open(path, 'w') as f:
            f.write(self.write_to_str())

    def get_optional_config_var(self, v: str | ConfigVar) -> ConfigVar | None:
        if isinstance(v, ConfigVar):
            name = v.name
        else:
            name = v
        for var in self.vars:
            if var.name == name:
                return var
        return None

    def get_optional_item(self, v: str | ConfigVar) -> ConfigItem | None:
        if isinstance(v, ConfigVar):
            name = v.name
        else:
            name = v
        for item in self.items:
            if item.name == name:
                return item
        return None

    def add_item(self, name: str, value: str | Any, *, line_number=None) -> ConfigItem:

        i = self.get_optional_item(name)
        if i is not None:
            raise UserFriendlyException(
                f"Config item with name {name} already exists, which is at line {line_number}. The one trying to add is at line {i.line_number}!")

        v = self.get_optional_config_var(name)
        if v is None:
            item = ConfigItem(name, value, line_number=line_number)
        else:
            if isinstance(value, str):
                try:
                    value = v.convert_str_to_value(value)
                except UserFriendlyException as e:
                    raise UserFriendlyException(
                        f"Invalid value with key {v.name} at line {line_number}! Reason: {e.message}")

            item = ConfigItem(v, value, line_number=line_number)
        self.items.append(item)
        return item

    @property
    def undefined_vars(self) -> list[ConfigVar]:
        return [var for var in self.vars if self.get_optional_item(var) is None]

    @property
    def unused_items(self) -> list[ConfigItem]:
        return [item for item in self.items if not item.is_config_var]

    def __str__(self):
        return self.write_to_str()
