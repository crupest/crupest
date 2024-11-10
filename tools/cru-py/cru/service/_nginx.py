from argparse import Namespace

from ._base import AppCommandFeatureProvider
from ._config import ConfigManager


class NginxManager(AppCommandFeatureProvider):
    def __init__(self):
        super().__init__("nginx-manager")

    def setup(self) -> None:
        pass

    @property
    def _template_domain_variable(self) -> str:
        return self.app.get_feature(ConfigManager).get_domain_item_name()

    def _create_domain_regex(self):
        raise NotImplementedError()

    def _get_domains(self) -> list[str]:
        raise NotImplementedError()

    def get_command_info(self):
        raise NotImplementedError()

    def setup_arg_parser(self, arg_parser):
        raise NotImplementedError()

    def run_command(self, args: Namespace) -> None:
        raise NotImplementedError()
