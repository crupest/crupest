import os
import typing
import uuid
from rich.prompt import Prompt
from .path import config_file_path

def generate_uuid():
    return str(uuid.uuid4())

class ConfigVar:
    def __init__(self, name: str, description: str, default_value_generator: typing.Callable[[], str] | str, /, default_value_for_ask=str | None):
        """Create a config var.

        Args:
            name (str): The name of the config var.
            description (str): The description of the config var.
            default_value_generator (typing.Callable[[], str] | str): The default value generator of the config var. If it is a string, it will be used as the input prompt and let user input the value.
        """
        self.name = name
        self.description = description
        self.default_value_generator = default_value_generator
        self.default_value_for_ask = default_value_for_ask

    def get_default_value(self, /, console):
        if isinstance(self.default_value_generator, str):
            return Prompt.ask(self.default_value_generator, console=console, default=self.default_value_for_ask)
        else:
            return self.default_value_generator()


config_var_list: list = [
    ConfigVar("CRUPEST_DOMAIN", "domain name",
              "Please input your domain name"),
    ConfigVar("CRUPEST_EMAIL", "admin email address",
              "Please input your email address"),
    ConfigVar("CRUPEST_AUTO_BACKUP_COS_SECRET_ID",
              "access key id for Tencent COS, used for auto backup", "Please input your Tencent COS access key id for backup"),
    ConfigVar("CRUPEST_AUTO_BACKUP_COS_SECRET_KEY",
              "access key secret for Tencent COS, used for auto backup", "Please input your Tencent COS access key for backup"),
    ConfigVar("CRUPEST_AUTO_BACKUP_COS_REGION",
              "region for Tencent COS, used for auto backup", "Please input your Tencent COS region for backup", "ap-hongkong"),
    ConfigVar("CRUPEST_AUTO_BACKUP_BUCKET_NAME",
              "bucket name for Tencent COS, used for auto backup", "Please input your Tencent COS bucket name for backup"),
    ConfigVar("CRUPEST_GITHUB_USERNAME",
              "github username for fetching todos", "Please input your github username for fetching todos", "crupest"),
    ConfigVar("CRUPEST_GITHUB_PROJECT_NUMBER",
              "github project number for fetching todos", "Please input your github project number for fetching todos", "2"),
    ConfigVar("CRUPEST_GITHUB_TOKEN",
              "github token for fetching todos", "Please input your github token for fetching todos"),
    ConfigVar("CRUPEST_GITHUB_TODO_COUNT",
              "github todo count", "Please input your github todo count", 10),
    ConfigVar("CRUPEST_GITHUB_TODO_COUNT",
              "github todo count", "Please input your github todo count", 10),
    ConfigVar("CRUPEST_V2RAY_TOKEN",
              "v2ray user id", generate_uuid),
    ConfigVar("CRUPEST_V2RAY_PATH",
              "v2ray path, which will be prefixed by _", generate_uuid),
]

config_var_name_set = set([config_var.name for config_var in config_var_list])


def check_config_var_set(needed_config_var_set: set):
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
    return os.path.isfile(config_file_path)


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
    if not config_file_exists():
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
