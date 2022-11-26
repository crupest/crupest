from rich.prompt import Prompt
import pwd
import grp
import os


class ConfigVar:
    def __init__(self, name: str, description: str, default_value_generator, /, default_value_for_ask=None):
        """Create a config var.

        Args:
            name (str): The name of the config var.
            description (str): The description of the config var.
            default_value_generator (typing.Callable([], str) | str): The default value generator of the config var. If it is a string, it will be used as the input prompt and let user input the value.
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
    ConfigVar("CRUPEST_USER", "your system account username",
              lambda: pwd.getpwuid(os.getuid()).pw_name),
    ConfigVar("CRUPEST_GROUP", "your system account group name",
              lambda: grp.getgrgid(os.getgid()).gr_name),
    ConfigVar("CRUPEST_UID", "your system account uid",
              lambda: str(os.getuid())),
    ConfigVar("CRUPEST_GID", "your system account gid",
              lambda: str(os.getgid())),
    ConfigVar("CRUPEST_HALO_DB_PASSWORD",
              "password for halo h2 database, once used never change it", lambda: os.urandom(8).hex()),
    ConfigVar("CRUPEST_IN_CHINA",
              "set to true if you are in China, some network optimization will be applied", lambda: "false"),
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
