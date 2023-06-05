from typing import Callable, ClassVar, Literal, Union, Any
import uuid
import re
from rich.prompt import Prompt
from ..console import console


def _generate_uuid() -> str:
    return str(uuid.uuid4())


def get_config_var_prefix() -> str:
    """
    The prefix of config var.
    TODO: Make this configurable.
    """
    return "CRUPEST"


class ConfigVarType:
    def __init__(self, name: str, value_type: type) -> None:
        self.name = name
        self.type = value_type

    def is_instance_of_value_type(self, value: Any) -> bool:
        return isinstance(value, self.type)

    def check_value_type(self, value: Any) -> None:
        if not isinstance(value, self.type):
            raise Exception(
                f"Config var {self.name} is not a {self.type}!")

    def check_str_format(self, s: str) -> None:
        raise NotImplementedError()

    def do_convert_value_to_str(self, value: Any) -> str:
        raise NotImplementedError()

    def convert_value_to_str(self, value: Any) -> str:
        self.check_value_type(value)
        return self.do_convert_value_to_str(value)

    def do_convert_str_to_value(self, value: str) -> Any:
        raise NotImplementedError()

    def convert_str_to_value(self, value: str) -> Any:
        self.check_str_format(value)
        return self.do_convert_str_to_value(value)


class TextConfigVarType(ConfigVarType):
    def __init__(self) -> None:
        super().__init__("text", str)

    def check_str_format(self, s: str) -> None:
        return

    def do_convert_value_to_str(self, value: str) -> str:
        return value

    def do_convert_str_to_value(self, value: str) -> str:
        return value


class IntegerConfigVarType(ConfigVarType):

    _int_regex: ClassVar[re.Pattern] = re.compile(r"^\d+$")

    def __init__(self) -> None:
        super().__init__("integer", int)

    def check_str_format(self, s: str) -> None:
        if not IntegerConfigVarType._int_regex.match(s):
            raise Exception(
                f"Config var {self.name} is not an integer!")

    def do_convert_value_to_str(self, value: int) -> str:
        return str(value)

    def do_convert_str_to_value(self, value: str) -> int:
        return int(value)


class BooleanConfigVarType(ConfigVarType):
    def __init__(self) -> None:
        super().__init__("boolean", bool)

    def check_str_format(self, s: str) -> None:
        if s.lower() not in ["true", "false"]:
            raise Exception(
                f"Config var {self.name} is not a boolean!")

    def do_convert_value_to_str(self, value: bool) -> str:
        return str(value).lower()

    def convert_str_to_value(self, value: str) -> bool:
        return value.lower() == "true"


config_var_text_type = TextConfigVarType()
config_var_integer_type = IntegerConfigVarType()
config_var_boolean_type = BooleanConfigVarType()

config_var_type_list = [config_var_text_type,
                        config_var_integer_type, config_var_boolean_type]
config_var_type_dict = {t.name: t for t in config_var_type_list}


def get_config_var_type(v: Union[str, ConfigVarType]) -> ConfigVarType:
    if isinstance(v, str):
        if v not in config_var_type_dict:
            raise Exception(f"Unknown config var type name {v}!")
        return config_var_type_dict[v]
    else:
        if not isinstance(v, ConfigVarType):
            raise Exception(
                f"Config var type {v} is not a ConfigVarType!")
        return v


ConfigVarDefaultGenerator = Callable[[ConfigVarType], Any]


class ConfigVar:

    def __init__(self, name: str, description: str, default_value_generator: ConfigVarDefaultGenerator, *, type: Union[str, ConfigVarType] = config_var_text_type):
        self.name = get_config_var_prefix() + "_" + name
        self.description = description
        self.default_value_generator = default_value_generator
        self.type = get_config_var_type(type)

    def check_value_type(self, value: Any):
        self.type.check_value_type(value)

    def check_str_format(self, value: str):
        self.type.check_str_format(value)

    def convert_str_to_value(self, value: str) -> Any:
        self.type.convert_str_to_value(value)

    def convert_to_value(self, value: Any) -> Any:
        if self.type.is_instance_of_value_type(value):
            return value
        return self.type.convert_str_to_value(value)

    def convert_value_to_str(self, value: Any) -> str:
        return self.type.convert_value_to_str(value)

    def generate_default_value(self) -> Any:
        d = self.default_value_generator(self.type)
        self.check_value_type(d)
        return d

    def generate_default_value_str(self) -> str:
        return self.convert_value_to_str(self.generate_default_value())

    @staticmethod
    def auto_gen_var(name: str, description: str, default_value: Union[Any, ConfigVarDefaultGenerator], *, type: Union[str, ConfigVarType] = config_var_text_type) -> "ConfigVar":
        def default_value_generator(type) -> Any:
            return default_value(type) if callable(default_value) else default_value

        return ConfigVar(name, description, default_value_generator, type=type)

    @staticmethod
    def ask_var(name: str, description: str, prompt_str: str, /, default_value: Union[None, Any, ConfigVarDefaultGenerator] = None, *, type: Union[str, ConfigVarType] = config_var_text_type) -> "ConfigVar":
        def default_value_generator(type) -> Any:
            if default_value is None:
                s = Prompt.ask(prompt_str, console=console)
                return type.convert_value_to_str(s)
            else:
                d = default_value(type) if callable(
                    default_value) else default_value
                s = Prompt.ask(prompt_str, console=console,
                               default=type.convert_value_to_str(d))
                return type.convert_value_to_str(s)

        return ConfigVar(name, description, default_value_generator, type=type)


config_var_list: list[ConfigVar] = [
    ConfigVar.ask_var("DOMAIN",
                      "domain name",
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
                      10, type=config_var_integer_type),
    ConfigVar.auto_gen_var("V2RAY_TOKEN",
                           "v2ray user id",
                           _generate_uuid),
    ConfigVar.auto_gen_var("V2RAY_PATH",
                           "v2ray path, which will be prefixed by _",
                           _generate_uuid),
]


def check_config_vars(config_vars: list[ConfigVar]):
    names = set()
    for var in config_vars:
        if var.name in names:
            raise Exception(f"Config var {var.name} already exists!")
        names.add(var.name)
