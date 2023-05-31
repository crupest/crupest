from typing import ClassVar, Optional
from .config_var import ConfigVar, config_var_list, check_config_vars
from .config_map import ConfigMap, ConfigItem
from ..common import UserFriendlyException, Paths, MY_NAME, ensure_file, console
from ..ui_base import var_style, warning_style, print_with_indent


ConfigVar = ConfigVar
config_var_list = config_var_list
check_config_vars = check_config_vars
ConfigMap = ConfigMap

_old_prefix = MY_NAME.upper() + "_"


class Configuration(ConfigMap):
    configuration: ClassVar[Optional["Configuration"]] = None

    def __init__(self, config_vars: list[ConfigVar] = config_var_list):
        super().__init__()
        check_config_vars(config_vars)
        self.vars = config_vars
        self.old_prefix_items: list[ConfigItem] = []

    def _add_item_hook(self, item: ConfigItem):
        if item.name.startswith(_old_prefix):
            self.old_prefix_items.append(item)
            item.name = item.name[len(_old_prefix):]
        var = self.get_optional_config_var(item.name)
        if var is not None:
            item.config_var = var
            if isinstance(item.value, str):
                try:
                    item.value = var.convert_str_to_value(item.value)
                except UserFriendlyException as e:
                    raise UserFriendlyException(
                        f"Invalid value format with key {var.name}.") from e

    def get_optional_config_var(self, name: str) -> ConfigVar | None:
        for var in self.vars:
            if var.name == name:
                return var
        return None

    def load(self) -> "Configuration":
        self.load_from_file(Paths.config_file_path)
        return self

    def save(self) -> "Configuration":
        self.write_to_file(Paths.config_file_path)
        return self

    @property
    def undefined_vars(self) -> list[ConfigVar]:
        return [var for var in self.vars if self.get_optional_item(var.name) is None]

    @property
    def unused_items(self) -> list[ConfigItem]:
        return [item for item in self.items if item.config_var is None]

    def __str__(self):
        return self.write_to_str()

    def get_domain(self) -> str:
        item = self.get_optional_item("DOMAIN")
        if item is None:
            raise UserFriendlyException(
                "No domain is set! Please set it in the config file!")
        return item.value


_config_file_exists = ensure_file(Paths.config_file_path, must_exist=False)
configuration: Configuration | None = None
if _config_file_exists:
    configuration = Configuration().load()
    Configuration.configuration = configuration


def print_old_prefix_message():
    if configuration is not None:
        if len(configuration.old_prefix_items) > 0:
            console.print(
                f"Looks like some config items in the config file are still started with prefix [{var_style}]{_old_prefix}[/] in old style. You may wish to remove the prefix. They are ", style=warning_style)
            for item in configuration.old_prefix_items:
                print_with_indent(_old_prefix + item.name, var_style, 2)
