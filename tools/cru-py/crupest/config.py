import os
import typing
import uuid
import random
import string
from dataclasses import dataclass

from rich.prompt import Prompt

from cru.config import Configuration
from cru.parsing import SimpleLineConfigParser
from .path import config_file_path


@dataclass
class ConfigurationMigrationInfo:
    duplicate_item_in_old_config: list[str]
    item


class OldConfiguration:
    def __init__(self, items: None | dict[str, str] = None) -> None:
        self._items = items or {}

    @staticmethod
    def load_from_str(s: str) -> tuple["OldConfiguration", list[str, str]]:
        d, duplicate = SimpleLineConfigParser().parse_to_dict(s, True)
        return OldConfiguration(d), duplicate

    def convert_to_new_config(self) -> Configuration:


class ConfigVar:
    def __init__(self, name: str, description: str, default_value_generator: typing.Callable[[], str] | str, /,
                 default_value_for_ask=str | None):
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
              "access key id for Tencent COS, used for auto backup",
              "Please input your Tencent COS access key id for backup"),
    ConfigVar("CRUPEST_AUTO_BACKUP_COS_SECRET_KEY",
              "access key secret for Tencent COS, used for auto backup",
              "Please input your Tencent COS access key for backup"),
    ConfigVar("CRUPEST_AUTO_BACKUP_COS_REGION",
              "region for Tencent COS, used for auto backup", "Please input your Tencent COS region for backup",
              "ap-hongkong"),
    ConfigVar("CRUPEST_AUTO_BACKUP_BUCKET_NAME",
              "bucket name for Tencent COS, used for auto backup",
              "Please input your Tencent COS bucket name for backup"),
    ConfigVar("CRUPEST_GITHUB_USERNAME",
              "github username for fetching todos", "Please input your github username for fetching todos", "crupest"),
    ConfigVar("CRUPEST_GITHUB_PROJECT_NUMBER",
              "github project number for fetching todos", "Please input your github project number for fetching todos",
              "2"),
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
    ConfigVar("CRUPEST_FORGEJO_MAILER_USER",
              "Forgejo SMTP user.", "Please input your Forgejo SMTP user."),
    ConfigVar("CRUPEST_FORGEJO_MAILER_PASSWD",
              "Forgejo SMTP password.", "Please input your Forgejo SMTP password."),
    ConfigVar("CRUPEST_2FAUTH_APP_KEY",
              "2FAuth App Key.", generate_random_string_32),
    ConfigVar("CRUPEST_2FAUTH_MAIL_USERNAME",
              "2FAuth SMTP user.", "Please input your 2FAuth SMTP user."),
    ConfigVar("CRUPEST_2FAUTH_MAIL_PASSWORD",
              "2FAuth SMTP password.", "Please input your 2FAuth SMTP password."),
]

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
