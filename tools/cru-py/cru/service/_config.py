from cru import CruException, CruUserFriendlyException
from cru.config import Configuration, ConfigItem
from cru.value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    RandomStringValueGenerator,
    UuidValueGenerator,
)
from cru.parsing import ParseError, SimpleLineConfigParser

from ._base import AppFeaturePath, AppCommandFeatureProvider, OWNER_NAME


class AppConfigError(CruException):
    pass


class AppConfigDuplicateEntryError(AppConfigError):
    def __init__(
        self, message: str, entries: list[SimpleLineConfigParser.Entry], *args, **kwargs
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._entries = entries

    @property
    def duplicate_entries(self) -> list[SimpleLineConfigParser.Entry]:
        return self._entries

    @staticmethod
    def duplicate_entries_to_friendly_message(
        entries: list[SimpleLineConfigParser.Entry],
    ) -> str:
        return "".join(
            f"line {entry.line_number}: {entry.key}={entry.value}\n"
            for entry in entries
        )

    def to_friendly_error(self) -> CruUserFriendlyException:
        e = CruUserFriendlyException(
            f"Duplicate entries found in config file:\n"
            f"{self.duplicate_entries_to_friendly_message(self.duplicate_entries)}"
        )
        return e


class AppConfigFileNotFoundError(AppConfigError):
    def __init__(self, message: str, file_path: str, *args, **kwargs) -> None:
        super().__init__(message, *args, **kwargs)
        self._file_path = file_path

    @property
    def file_path(self) -> str:
        return self._file_path

    def to_friendly_error(self) -> CruUserFriendlyException:
        e = CruUserFriendlyException(
            f"Config file not found at {self.file_path}. You may need to create one."
        )
        return e


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


class AppConfigItemNotDefinedError(AppConfigError):
    def __init__(
        self,
        message: str,
        undefined_names: list[str],
        configuration: Configuration,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._undefined_names = undefined_names
        self._configuration = configuration

    @property
    def undefined_names(self) -> list[str]:
        return self._undefined_names

    @property
    def configuration(self) -> Configuration:
        return self._configuration


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
                "Config file not found.", self.config_file_path.full_path_str
            )
        parser = SimpleLineConfigParser()
        return parser.parse(self.config_file_path.full_path.read_text())

    def _check_duplicate(
        self,
        parse_result: dict[str, list[SimpleLineConfigParser.Entry]],
    ) -> dict[str, str]:
        config_dict = {}
        duplicate_entries = []
        for key, entries in parse_result.items():
            config_dict[key] = entries[0].value
            for entry in entries[1:]:
                duplicate_entries.append(entry)

        if len(duplicate_entries) > 0:
            raise AppConfigDuplicateEntryError(
                "Duplicate entries found.", duplicate_entries
            )

        return config_dict

    def _check_defined(
        self,
        config_dict: dict[str, str],
        allow_extra: bool = True,
    ) -> dict[str, str]:
        # TODO: Continue here!
        raise NotImplementedError()

    def _check_config_file(self) -> dict[str, str]:
        try:
            parsed = self._parse_config_file()
            config = self._check_duplicate(parsed)
            return config
        except ParseError as e:
            raise CruUserFriendlyException("Failed to parse config file.") from e
        except AppConfigDuplicateEntryError as e:
            raise e.to_friendly_error() from e

    def reload_config_file(self) -> bool:
        self.configuration.reset_all()
        config_dict = self._check_config_file()
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
