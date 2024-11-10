from cru.config import Configuration, ConfigItem
from cru.value import (
    INTEGER_VALUE_TYPE,
    TEXT_VALUE_TYPE,
    RandomStringValueGenerator,
    UuidValueGenerator,
)

from ._base import AppFeaturePath, AppFeatureProvider, OWNER_NAME


class ConfigManager(AppFeatureProvider):
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
    def config_path(self) -> AppFeaturePath:
        return self._config_path

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def config_map(self) -> dict[str, str]:
        raise NotImplementedError()
