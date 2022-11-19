import os.path
from .path import config_file_path

config_file_exist = os.path.isfile(config_file_path)


def parse_config(str: str) -> dict:
    config = {}
    for line_number, line in enumerate(str.splitlines()):
        # check if it's a comment
        if line.startswith("#"):
            continue
        # check if there is a '='
        if line.find("=") == -1:
            raise ValueError(
                f"Invalid config string. Please check line {line_number + 1}. There is even no '='!")
        # split at first '='
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        config[key] = value
    return config


def get_domain() -> str:
    if not config_file_exist:
        raise ValueError("Config file not found!")
    with open(config_file_path) as f:
        config = parse_config(f.read())
    if "CRUPEST_DOMAIN" not in config:
        raise ValueError("Domain not found in config file!")
    return config["CRUPEST_DOMAIN"]


def config_to_str(config: dict) -> str:
    return "\n".join([f"{key}={value}" for key, value in config.items()])


def print_config(console, config: dict) -> None:
    for key, value in config.items():
        console.print(f"[magenta]{key}[/] = [cyan]{value}")


__all__ = ["config_file_exist", "parse_config",
           "get_domain", "config_to_str", "print_config"]
