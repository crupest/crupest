from collections.abc import Iterable
from typing import Any, NoReturn

from cru import CruException, CruUserFriendlyException
from cru.config import Configuration, ConfigItem
from cru.value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    CruValueTypeError,
    RandomStringValueGenerator,
    UuidValueGenerator,
)
from cru.parsing import ParseError, SimpleLineConfigParser

from ._base import AppFeaturePath, AppCommandFeatureProvider, OWNER_NAME


class AppConfigError(CruException):
    def __init__(
        self, message: str, configuration: Configuration, *args, **kwargs
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._configuration = configuration

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def friendly_error_message(self) -> str:
        raise NotImplementedError("Subclasses must implement this method.")

    def to_friendly_error(self) -> CruUserFriendlyException:
        return CruUserFriendlyException(self.friendly_error_message)

    def raise_friendly_error(self) -> NoReturn:
        raise self.to_friendly_error() from self


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

    @property
    def friendly_error_message(self) -> str:
        return f"Config file not found at {self.file_path}. You may need to create one."


class AppConfigFileParseError(AppConfigFileError):
    def __init__(
        self,
        message: str,
        configuration: Configuration,
        file_content: str,
        *args,
        cause: ParseError | None = None,
        **kwargs,
    ) -> None:
        super().__init__(message, configuration, *args, **kwargs)
        self._file_content = file_content
        if cause is not None:
            self._cause = cause
        self._cause = self.__cause__  # type: ignore

    @property
    def file_content(self) -> str:
        return self._file_content

    @property
    def friendly_error_message(self) -> str:
        return f"Error while parsing config file at line {self._cause.line_number}."


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
        return "".join(
            f"line {entry.line_number}: {entry.key}={entry.value}\n"
            for entry in entries
        )

    @property
    def friendly_message_head(self) -> str:
        return "Error entries found in config file"

    @property
    def friendly_error_message(self) -> str:
        return (
            f"{self.friendly_message_head}:\n"
            f"{self.entries_to_friendly_message(self.error_entries)}"
        )


class AppConfigDuplicateEntryError(AppConfigFileEntryError):
    @property
    def friendly_message_head(self) -> str:
        return "Duplicate entries found in config file"


class AppConfigEntryKeyNotDefinedError(AppConfigFileEntryError):
    @property
    def friendly_message_head(self) -> str:
        return "Entry key not defined in app config"


class AppConfigEntryValueFormatError(AppConfigFileEntryError):
    @property
    def friendly_message_head(self) -> str:
        return "Invalid value format for entries"


class AppConfigItemNotSetError(AppConfigError):
    def __init__(
        self,
        message: str,
        items: list[ConfigItem],
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._items = items


class ConfigManager(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("config-manager")
        configuration = Configuration()
        self._configuration = configuration
        self._init_app_defined_items()

    def _init_app_defined_items(self) -> None:
        def _add_text(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(f"{OWNER_NAME}_{name}", description, TEXT_VALUE_TYPE)
            )

        def _add_uuid(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(
                    f"{OWNER_NAME}_{name}",
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
                    f"{OWNER_NAME}_{name}",
                    description,
                    TEXT_VALUE_TYPE,
                    default=RandomStringValueGenerator(length, secure),
                )
            )

        def _add_int(name: str, description: str) -> None:
            self.configuration.add(
                ConfigItem(f"{OWNER_NAME}_{name}", description, INTEGER_VALUE_TYPE)
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
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def config_file_path(self) -> AppFeaturePath:
        return self._config_file_path

    def _parse_config_file(self) -> SimpleLineConfigParser.Result:
        if not self.config_file_path.check_self():
            raise AppConfigFileNotFoundError(
                "Config file not found.",
                self.configuration,
                self.config_file_path.full_path_str,
            )

        text = self.config_file_path.full_path.read_text()
        try:
            parser = SimpleLineConfigParser()
            return parser.parse(text)
        except ParseError as e:
            raise AppConfigFileParseError(
                "Failed to parse config file.", self.configuration, text
            ) from e

    def _check_duplicate(
        self,
        parse_result: dict[str, list[SimpleLineConfigParser.Entry]],
    ) -> dict[str, SimpleLineConfigParser.Entry]:
        entry_dict: dict[str, SimpleLineConfigParser.Entry] = {}
        duplicate_entries: list[SimpleLineConfigParser.Entry] = []
        for key, entries in parse_result.items():
            entry_dict[key] = entries[0]
            for entry in entries[1:]:
                duplicate_entries.append(entry)

        if len(duplicate_entries) > 0:
            raise AppConfigDuplicateEntryError(
                "Duplicate entries found.", self.configuration, duplicate_entries
            )

        return entry_dict

    def _check_defined(
        self, entry_dict: dict[str, SimpleLineConfigParser.Entry]
    ) -> dict[str, SimpleLineConfigParser.Entry]:
        undefined: list[SimpleLineConfigParser.Entry] = []
        for key, entry in entry_dict.items():
            if not self.configuration.has_key(key):
                undefined.append(entry)
        if len(undefined) > 0:
            raise AppConfigEntryKeyNotDefinedError(
                "Entry keys are not defined in app config.",
                self.configuration,
                undefined,
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

    def _read_config_file(self, friendly: bool = False) -> dict[str, Any]:
        try:
            parsed = self._parse_config_file()
            entry_groups = parsed.cru_iter().group_by(lambda e: e.key)
            entry_dict = self._check_duplicate(entry_groups)
            entry_dict = self._check_defined(entry_dict)
            value_dict = self._check_type(entry_dict)
            return value_dict
        except AppConfigError as e:
            if friendly:
                e.raise_friendly_error()
            raise

    def reload_config_file(self) -> bool:
        self.configuration.reset_all()
        value_dict = self._read_config_file()
        # TODO: Continue here!
        for key, value in config_dict.items():
            self.configuration.set(key, value)
        return True

    def print_app_config_info(self):
        for item in self.configuration:
            print(f"{item.name} ({item.value_type.name}): {item.description}")

    def get_command_info(self):
        return "config", "Manage configuration."

    def setup_arg_parser(self, arg_parser) -> None:
        subparsers = arg_parser.add_subparsers(dest="config_command")
        _print_app_parser = subparsers.add_parser(
            "print-app",
            help="Print application configuration information "
            "of the items defined in the application.",
        )
        _check_config_parser = subparsers.add_parser(
            "check",
            help="Check the validity of the configuration file.",
        )
        _check_config_parser.add_argument(
            "-f",
            "--format-only",
            action="store_true",
            help="Only check content format, not "
            "for application configuration requirements.",
        )

    def run_command(self, args) -> None:
        if args.config_command == "print-app":
            self.print_app_config_info()
