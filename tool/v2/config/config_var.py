import uuid
from rich.prompt import Prompt
from ..console import console


def _generate_uuid():
    return str(uuid.uuid4())


def get_config_var_prefix():
    """
    The prefix of config var.
    TODO: Make this configurable.
    """
    return "CRUPEST"


class ConfigVar:
    """
    Represents a variable item in config file.

    Fields:
        name: the name also the koy of the config var
        description: the description of the config var, aka the config var decides what
    """

    def __init__(self, name, description, default_value_generator):
        """
        Create a config var.
        The name will be prefixed by return value of get_config_var_prefix() and a '_'.

        Args:
            name (str): The name of the config var.
            description (str): The description of the config var.
            default_value_generator (() -> str): The default value generator of the config var.
        """
        self.name = get_config_var_prefix() + "_" + name
        self.description = description
        self.default_value_generator = default_value_generator

    def str_var(name, description, default_value):
        """
        A var with a string as default value.

        Args:
            name (str): The name of the config var.
            description (str): The description of the config var.
            default_str (str | () -> str): The default string of the config var. Can be a function, which will be called to generate a default value.
        """
        def default_value_generator():
            return default_value() if callable(default_value) else default_value

        return ConfigVar(name, description, default_value_generator)

    def ask_var(name, description, prompt_str, /, default_value=None):
        """
        Default generator is ask the user to input one.

        Args:
            prompt_str (str): The prompt string for the user.
            default_value (str | () -> str): The default value for the user to choose to use or not. Cam be function, which will be called to generate a default value.
        """

        def default_value_generator():
            d = default_value() if callable(default_value) else default_value
            return Prompt.ask(prompt_str, console=console, default=d)

        return ConfigVar(name, description, default_value_generator)


config_var_list: list = [
    ConfigVar.ask_var("DOMAIN", "domain name",
                      "Please input your domain name"),
    ConfigVar.ask_var("EMAIL",
                      "admin email address",
                      "Please input your email address"),
    ConfigVar.ask_var("AUTO_BACKUP_COS_SECRET_ID",
                      "access key id for COS, used for auto backup",
                      "Please input your COS access key id for backup"),
    ConfigVar.ask_var("AUTO_BACKUP_COS_SECRET_KEY",
                      "access key secret for COS, used for auto backup",
                      "Please input your COS access key for backup"),
    # TODO: Region? Should be a domain. So we can use another COS provider.
    ConfigVar.ask_var("AUTO_BACKUP_COS_REGION",
                      "region for COS, used for auto backup",
                      "Please input your COS region for backup"),
    ConfigVar.ask_var("AUTO_BACKUP_BUCKET_NAME",
                      "bucket name for COS, used for auto backup",
                      "Please input your COS bucket name for backup"),
    ConfigVar.ask_var("GITHUB_USERNAME",
                      "github username for fetching todos",
                      "Please input your github username for fetching todos"),
    ConfigVar.ask_var("GITHUB_PROJECT_NUMBER",
                      "github project number for fetching todos",
                      "Please input your github project number for fetching todos"),
    ConfigVar.ask_var("GITHUB_TOKEN",
                      "github token for fetching todos",
                      "Please input your github token for fetching todos"),
    ConfigVar.ask_var("GITHUB_TODO_COUNT",
                      "github todo count",
                      "Please input your github todo count",
                      10),
    ConfigVar.str_var("V2RAY_TOKEN",
                      "v2ray user id",
                      _generate_uuid),
    ConfigVar.str_var("V2RAY_PATH",
                      "v2ray path, which will be prefixed by _",
                      _generate_uuid),
]
