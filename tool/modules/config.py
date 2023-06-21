from .common import Paths, ensure_file
from .config2.configuration import config_var_list, ConfigMap, configuration


config_var_name_set = set([config_var.name for config_var in config_var_list])


def check_config_var_set(needed_config_var_set: set[str]) -> tuple[bool, list[str], list[str]]:
    more = []
    less = []
    for var_name in needed_config_var_set:
        if var_name not in config_var_name_set:
            more.append(var_name)
    for var_name in config_var_name_set:
        if var_name not in needed_config_var_set:
            less.append(var_name)
    return (True if len(more) == 0 else False, more, less)


def config_file_exists():
    return ensure_file(Paths.config_file_path, must_exist=False)


def parse_config(str: str) -> dict[str, str]:
    return ConfigMap().load_from_str(str).to_dict()


def get_domain() -> str:
    if configuration is None:
        raise ValueError("Config file not found!")
    return configuration.get_domain()


def config_to_str(config: dict) -> str:
    return "\n".join([f"{key}={value}" for key, value in config.items()])


def print_config(console, config: dict) -> None:
    for key, value in config.items():
        console.print(f"[magenta]{key}[/] = [cyan]{value}")
