from cru import CruException, CruUserFriendlyException
from cru.config import Configuration, ConfigItem
from cru.value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    RandomStringValueGenerator,
    UuidValueGenerator,
)
from cru.parsing import SimpleLineConfigParser

from ._base import AppFeaturePath, AppCommandFeatureProvider, OWNER_NAME


class AppConfigError(CruException):
    pass


class AppConfigDuplicateItemsError(AppConfigError):
    def __init__(
        self, message: str, items: list[SimpleLineConfigParser.Item], *args, **kwargs
    ) -> None:
        super().__init__(message, *args, **kwargs)
        self._items = items

    @property
    def duplicate_items(self) -> list[SimpleLineConfigParser.Item]:
        return self._items

    @staticmethod
    def duplicate_items_to_friendly_message(
        items: list[SimpleLineConfigParser.Item],
    ) -> str:
        return "".join(
            f"line {item.line_number}: {item.key}={item.value}\n" for item in items
        )

    def to_friendly_error(self) -> CruUserFriendlyException:
        e = CruUserFriendlyException(
            f"Duplicate configuration items detected:\n"
            f"{self.duplicate_items_to_friendly_message(self.duplicate_items)}"
        )
        e.__cause__ = self
        return e


class ConfigManager(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("config-manager")
        configuration = Configuration()
        self._configuration = configuration
        self._add_text_item("DOMAIN", "domain name")
        self._add_text_item("EMAIL", "admin email address")
        self._add_text_item(
            "AUTO_BACKUP_COS_SECRET_ID",
            "access key id for Tencent COS, used for auto backup",
        )
        self._add_text_item(
            "AUTO_BACKUP_COS_SECRET_KEY",
            "access key secret for Tencent COS, used for auto backup",
        )
        self._add_text_item(
            "AUTO_BACKUP_COS_REGION", "region for Tencent COS, used for auto backup"
        )
        self._add_text_item(
            "AUTO_BACKUP_BUCKET_NAME",
            "bucket name for Tencent COS, used for auto backup",
        )
        self._add_text_item("GITHUB_USERNAME", "github username for fetching todos")
        self._add_int_item(
            "GITHUB_PROJECT_NUMBER", "github project number for fetching todos"
        )
        self._add_text_item("GITHUB_TOKEN", "github token for fetching todos")
        self._add_text_item("GITHUB_TODO_COUNT", "github todo count")
        self._add_uuid_item("V2RAY_TOKEN", "v2ray user id")
        self._add_uuid_item("V2RAY_PATH", "v2ray path, which will be prefixed by _")
        self._add_text_item("FORGEJO_MAILER_USER", "Forgejo SMTP user")
        self._add_text_item("FORGEJO_MAILER_PASSWD", "Forgejo SMTP password")
        self._add_random_string_item("2FAUTH_APP_KEY", "2FAuth App Key")
        self._add_text_item("2FAUTH_MAIL_USERNAME", "2FAuth SMTP user")
        self._add_text_item("2FAUTH_MAIL_PASSWORD", "2FAuth SMTP password")

    def _add_text_item(self, name: str, description: str) -> None:
        self.configuration.add(
            ConfigItem(f"{OWNER_NAME}_{name}", description, TEXT_VALUE_TYPE)
        )

    def _add_uuid_item(self, name: str, description: str) -> None:
        self.configuration.add(
            ConfigItem(
                f"{OWNER_NAME}_{name}",
                description,
                TEXT_VALUE_TYPE,
                default=UuidValueGenerator(),
            )
        )

    def _add_random_string_item(
        self, name: str, description: str, length: int = 32, secure: bool = True
    ) -> None:
        self.configuration.add(
            ConfigItem(
                f"{OWNER_NAME}_{name}",
                description,
                TEXT_VALUE_TYPE,
                default=RandomStringValueGenerator(length, secure),
            )
        )

    def _add_int_item(self, name: str, description: str) -> None:
        self.configuration.add(
            ConfigItem(f"{OWNER_NAME}_{name}", description, INTEGER_VALUE_TYPE)
        )

    def setup(self) -> None:
        self._config_path = self.app.data_dir.add_subpath(
            "config", False, description="Configuration file path."
        )

    @property
    def config_file_path(self) -> AppFeaturePath:
        return self._config_path

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def config_keys(self) -> list[str]:
        return [item.name for item in self.configuration]

    @property
    def config_map(self) -> dict[str, str]:
        raise NotImplementedError()

    def _parse_config_file(self) -> SimpleLineConfigParser.Result | None:
        if not self.config_file_path.check_self():
            return None
        parser = SimpleLineConfigParser()
        return parser.parse(self.config_file_path.full_path.read_text())

    def _check_duplicate(
        self,
        result: SimpleLineConfigParser.Result
        | dict[str, list[SimpleLineConfigParser.Item]],
    ) -> dict[str, str]:
        if isinstance(result, SimpleLineConfigParser.Result):
            result = result.cru_iter().group_by(lambda i: i.key)

        config = {}
        error_items = []
        for key, items in result.items():
            config[key] = items[0].value
            for item in items[1:]:
                error_items.append(item)

        if len(error_items) > 0:
            raise AppConfigDuplicateItemsError("Duplicate items found.", error_items)

        return config

    def _check_config_file(self) -> dict[str, str]:
        # TODO: Continue here!
        raise NotImplementedError()

    def reload_config_file(self) -> bool:
        self.configuration.reset_all()
        if not self.config_file_path.check_self():
            return False
        parser = SimpleLineConfigParser()
        parse_result = parser.parse(self.config_file_path.full_path.read_text())
        config_dict = parse_result.cru_iter().group_by(lambda i: i.key)
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
