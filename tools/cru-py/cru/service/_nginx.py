from argparse import Namespace
import re

from ._base import AppCommandFeatureProvider
from ._config import ConfigManager
from ._template import TemplateManager


class NginxManager(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("nginx-manager")
        self._domains_cache: list[str] | None = None
        self._domain_config_value_cache: str | None = None

    def setup(self) -> None:
        pass

    @property
    def domains(self) -> list[str]:
        if self._domains_cache is None:
            self._domains_cache = self._get_domains()
        return self._domains_cache

    @property
    def _domain_config_name(self) -> str:
        return self.app.get_feature(ConfigManager).get_domain_item_name()

    def _get_domain_config_value(self) -> str:
        if self._domain_config_value_cache is None:
            self._domain_config_value_cache = self.app.get_feature(
                ConfigManager
            ).get_item_value_str(self._domain_config_name)
        return self._domain_config_value_cache

    def _get_domains_from_text(self, text: str) -> set[str]:
        domains: set[str] = set()
        regex = re.compile(r"server_name\s+(\S+)\s*;")
        domain_variable_str = f"${self._domain_config_name}"
        brace_domain_variable_regex = re.compile(
            r"\$\{\s*" + self._domain_config_name + r"\s*\}"
        )
        for match in regex.finditer(text):
            domain_part = match.group(1)
            if domain_variable_str in domain_part:
                domains.add(
                    domain_part.replace(
                        domain_variable_str, self._get_domain_config_value()
                    )
                )
                continue
            m = brace_domain_variable_regex.search(domain_part)
            if m:
                domains.add(
                    domain_part.replace(m.group(0), self._get_domain_config_value())
                )
                continue
            domains.add(domain_part)
        return domains

    def _get_nginx_conf_template_text(self) -> str:
        template_manager = self.app.get_feature(TemplateManager)
        text = ""
        for path, template in template_manager.template_tree.templates:
            if path.as_posix().startswith("nginx/"):
                text += template.raw_text
        return text

    def _get_domains(self) -> list[str]:
        text = self._get_nginx_conf_template_text()
        domains = list(self._get_domains_from_text(text))
        domains.remove(self._get_domain_config_value())
        return [self._get_domain_config_value(), *domains]

    def _print_domains(self) -> None:
        for domain in self.domains:
            print(domain)

    def get_command_info(self):
        return "nginx", "Manage nginx related things."

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="nginx_command", required=True, metavar="NGINX_COMMAND"
        )
        _list_parser = subparsers.add_parser("list", help="list domains")

    def run_command(self, args: Namespace) -> None:
        if args.nginx_command == "list":
            self._print_domains()
