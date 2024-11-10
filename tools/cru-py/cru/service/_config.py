from collections.abc import Iterable
from typing import Any, Literal, overload

from cru import CruException
from cru.config import Configuration, ConfigItem
from cru.value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    CruValueTypeError,
    RandomStringValueGenerator,
    UuidValueGenerator,
)
from cru.parsing import ParseError, SimpleLineConfigParser

from ._base import AppFeaturePath, AppCommandFeatureProvider


class AppConfigError(CruException):
    def __init__(
        self, message: str, configuration: Configuration, *args, **kwargs
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._configuration = configuration

    @property
    def configuration(self) -> Configuration:
        return self._configuration


class AppConfigFileError(AppConfigError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)


class AppConfigFileNotFoundError(AppConfigFileError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        file_path: str,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)
        self._file_path = file_path

    @property
    def file_path(self) -> str:
        return self._file_path


class AppConfigFileParseError(AppConfigFileError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        file_content: str,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)
        self._file_content = file_content
        self.__cause__: ParseError

    @property
    def file_content(self) -> str:
        return self._file_content

    def get_user_message(self) -> str:
        return f"Error while parsing config file at line {self.__cause__.line_number}."


class AppConfigFileEntryError(AppConfigFileError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        entries: Iterable[SimpleLineConfigParser.Entry],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)
        self._entries = list(entries)

    @property
    def error_entries(self) -> list[SimpleLineConfigParser.Entry]:
        return self._entries

    @staticmethod
    def entries_to_friendly_message(
        entries: Iterable[SimpleLineConfigParser.Entry],
    ) -> str:
        return "\n".join(
            f"line {entry.line_number}: {entry.key}={entry.value}" for entry in entries
        )

    @property
    def friendly_message_head(self) -> str:
        return "Error entries found in config file"

    def get_user_message(self) -> str:
        return (
            f"{self.friendly_message_head}:\n"
            f"{self.entries_to_friendly_message(self.error_entries)}"
        )


class AppConfigDuplicateEntryError(AppConfigFileEntryError):
    @property
    def friendly_message_head(self) -> str:
        return "Duplicate entries found in config file"


class AppConfigEntryValueFormatError(AppConfigFileEntryError):
    @property
    def friendly_message_head(self) -> str:
        return "Invalid value format for entries"


class AppConfigItemNotSetError(AppConfigError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        items: list[ConfigItem],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)
        self._items = items


class ConfigManager(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("config-manager")
        configuration = Configuration()
        self._configuration = configuration
        self._init_app_defined_items()

    def _init_app_defined_items(self) -> None:
        prefix = self.config_name_prefix

        def _add_text(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(f"{prefix}_{name}", description, TEXT_VALUE_TYPE)
            )

        def _add_uuid(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(
                    f"{prefix}_{name}",
                    description,
                    TEXT_VALUE_TYPE,
                    default=UuidValueGenerator(),
                )
            )

        def _add_random_string(
            name: str, description: str, length: int = 32, secure: bool = True
        ) -> None:
            self.configuration.add(
                ConfigItem(
                    f"{prefix}_{name}",
                    description,
                    TEXT_VALUE_TYPE,
                    default=RandomStringValueGenerator(length, secure),
                )
            )

        def _add_int(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(f"{prefix}_{name}", description, INTEGER_VALUE_TYPE)
            )

        _add_text("DOMAIN", "domain name")
        _add_text("EMAIL", "admin email address")
        _add_text(
            "AUTO_BACKUP_COS_SECRET_ID",
            "access key id for Tencent COS, used for auto backup",
        )
        _add_text(
            "AUTO_BACKUP_COS_SECRET_KEY",
            "access key secret for Tencent COS, used for auto backup",
        )
        _add_text(
            "AUTO_BACKUP_COS_REGION", "region for Tencent COS, used for auto backup"
        )
        _add_text(
            "AUTO_BACKUP_BUCKET_NAME",
            "bucket name for Tencent COS, used for auto backup",
        )
        _add_text("GITHUB_USERNAME", "github username for fetching todos")
        _add_int("GITHUB_PROJECT_NUMBER", "github project number for fetching todos")
        _add_text("GITHUB_TOKEN", "github token for fetching todos")
        _add_text("GITHUB_TODO_COUNT", "github todo count")
        _add_uuid("V2RAY_TOKEN", "v2ray user id")
        _add_uuid("V2RAY_PATH", "v2ray path, which will be prefixed by _")
        _add_text("FORGEJO_MAILER_USER", "Forgejo SMTP user")
        _add_text("FORGEJO_MAILER_PASSWD", "Forgejo SMTP password")
        _add_random_string("2FAUTH_APP_KEY", "2FAuth App Key")
        _add_text("2FAUTH_MAIL_USERNAME", "2FAuth SMTP user")
        _add_text("2FAUTH_MAIL_PASSWORD", "2FAuth SMTP password")

    def setup(self) -> None:
        self._config_file_path = self.app.data_dir.add_subpath(
            "config", False, description="Configuration file path."
        )

    @property
    def config_name_prefix(self) -> str:
        return self.app.app_id.upper()

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def config_file_path(self) -> AppFeaturePath:
        return self._config_file_path

    @property
    def all_set(self) -> bool:
        return self.configuration.all_set

    def get_item(self, name: str) -> ConfigItem[Any]:
        if not name.startswith(self.config_name_prefix + "_"):
            name = f"{self.config_name_prefix}_{name}"

        item = self.configuration.get_or(name, None)
        if item is None:
            raise AppConfigError(f"Config item '{name}' not found.", self.configuration)
        return item

    @overload
    def get_item_value_str(self, name: str) -> str: ...

    @overload
    def get_item_value_str(self, name: str, ensure_set: Literal[True]) -> str: ...

    @overload
    def get_item_value_str(self, name: str, ensure_set: bool = True) -> str | None: ...

    def get_item_value_str(self, name: str, ensure_set: bool = True) -> str | None:
        self.reload_config_file()
        item = self.get_item(name)
        if ensure_set and not item.is_set:
            raise AppConfigItemNotSetError(
                f"Config item '{name}' is not set.", self.configuration, [item]
            )
        return item.value_str

    def get_str_dict(self, ensure_all_set: bool = True) -> dict[str, str]:
        self.reload_config_file()
        if ensure_all_set and not self.configuration.all_set:
            raise AppConfigItemNotSetError(
                "Some config items are not set.",
                self.configuration,
                self.configuration.get_unset_items(),
            )
        return self.configuration.to_str_dict()

    def get_domain_item_name(self) -> str:
        return f"{self.config_name_prefix}_DOMAIN"

    def _set_with_default(self) -> None:
        if not self.configuration.all_not_set:
            raise AppConfigError(
                "Config is not clean. "
                "Some config items are already set. "
                "Can't set again with default value.",
                self.configuration,
            )
        for item in self.configuration:
            if item.can_generate_default:
                item.set_value(item.generate_default_value())

    def _to_config_file_content(self) -> str:
        content = "".join(
            [
                f"{item.name}={item.value_str if item.is_set else ''}\n"
                for item in self.configuration
            ]
        )
        return content

    def _create_init_config_file(self) -> None:
        if self.config_file_path.check_self():
            raise AppConfigError(
                "Config file already exists.",
                self.configuration,
                user_message=f"The config file at "
                f"{self.config_file_path.full_path_str} already exists.",
            )
        self._set_with_default()
        self.config_file_path.ensure()
        with open(
            self.config_file_path.full_path, "w", encoding="utf-8", newline="\n"
        ) as file:
            file.write(self._to_config_file_content())

    def _parse_config_file(self) -> SimpleLineConfigParser.Result:
        if not self.config_file_path.check_self():
            raise AppConfigFileNotFoundError(
                "Config file not found.",
                self.configuration,
                self.config_file_path.full_path_str,
                user_message=f"The config file at "
                f"{self.config_file_path.full_path_str} does not exist. "
                f"You can create an initial one with 'init' command.",
            )

        text = self.config_file_path.full_path.read_text()
        try:
            parser = SimpleLineConfigParser()
            return parser.parse(text)
        except ParseError as e:
            raise AppConfigFileParseError(
                "Failed to parse config file.", self.configuration, text
            ) from e

    def _parse_and_print_config_file(self) -> None:
        parse_result = self._parse_config_file()
        for entry in parse_result:
            print(f"{entry.key}={entry.value}")

    def _check_duplicate(
        self,
        parse_result: dict[str, list[SimpleLineConfigParser.Entry]],
    ) -> dict[str, SimpleLineConfigParser.Entry]:
        entry_dict: dict[str, SimpleLineConfigParser.Entry] = {}
        duplicate_entries: list[SimpleLineConfigParser.Entry] = []
        for key, entries in parse_result.items():
            entry_dict[key] = entries[0]
            if len(entries) > 1:
                duplicate_entries.extend(entries)
        if len(duplicate_entries) > 0:
            raise AppConfigDuplicateEntryError(
                "Duplicate entries found.", self.configuration, duplicate_entries
            )

        return entry_dict

    def _check_type(
        self, entry_dict: dict[str, SimpleLineConfigParser.Entry]
    ) -> dict[str, Any]:
        value_dict: dict[str, Any] = {}
        error_entries: list[SimpleLineConfigParser.Entry] = []
        errors: list[CruValueTypeError] = []
        for key, entry in entry_dict.items():
            config_item = self.configuration.get(key)
            try:
                if entry.value == "":
                    value_dict[key] = None
                else:
                    value_dict[key] = config_item.value_type.convert_str_to_value(
                        entry.value
                    )
            except CruValueTypeError as e:
                error_entries.append(entry)
                errors.append(e)
        if len(error_entries) > 0:
            raise AppConfigEntryValueFormatError(
                "Entry value format is not correct.",
                self.configuration,
                error_entries,
            ) from ExceptionGroup("Multiple format errors occurred.", errors)
        return value_dict

    def _read_config_file(self) -> dict[str, Any]:
        parsed = self._parse_config_file()
        entry_groups = parsed.cru_iter().group_by(lambda e: e.key)
        entry_dict = self._check_duplicate(entry_groups)
        value_dict = self._check_type(entry_dict)
        return value_dict

    def reload_config_file(self):
        self.configuration.reset_all()
        value_dict = self._read_config_file()
        for key, value in value_dict.items():
            if value is None:
                continue
            self.configuration.set_config_item(key, value)

    def _print_app_config_info(self):
        for item in self.configuration:
            print(item.description_str)

    def get_command_info(self):
        return "config", "Manage configuration."

    def setup_arg_parser(self, arg_parser) -> None:
        subparsers = arg_parser.add_subparsers(
            dest="config_command", required=True, metavar="CONFIG_COMMAND"
        )
        _init_parser = subparsers.add_parser(
            "init", help="create an initial config file"
        )
        _print_app_parser = subparsers.add_parser(
            "print-app",
            help="print information of the config items defined by app",
        )
        _print_parser = subparsers.add_parser("print", help="print current config")
        _check_config_parser = subparsers.add_parser(
            "check",
            help="check the validity of the config file",
        )
        _check_config_parser.add_argument(
            "-f",
            "--format-only",
            action="store_true",
            help="only check content format, not app config item requirements.",
        )

    def run_command(self, args) -> None:
        if args.config_command == "init":
            self._create_init_config_file()
        elif args.config_command == "print-app":
            self._print_app_config_info()
        elif args.config_command == "print":
            self._parse_and_print_config_file()
        elif args.config_command == "check":
            if args.format_only:
                self._parse_config_file()
            else:
                self._read_config_file()
