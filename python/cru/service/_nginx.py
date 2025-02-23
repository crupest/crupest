from argparse import Namespace
from enum import Enum, auto
import re
import subprocess
from typing import TypeAlias

from cru import CruInternalError

from ._base import AppCommandFeatureProvider
from ._template import TemplateManager


class CertbotAction(Enum):
    CREATE = auto()
    EXPAND = auto()
    SHRINK = auto()
    RENEW = auto()


class NginxManager(AppCommandFeatureProvider):
    CertbotAction: TypeAlias = CertbotAction

    def __init__(self) -> None:
        super().__init__("nginx-manager")
        self._domains_cache: list[str] | None = None

    def setup(self) -> None:
        pass

    @property
    def _template_manager(self) -> TemplateManager:
        return self.app.get_feature(TemplateManager)

    @property
    def root_domain(self) -> str:
        return self._template_manager.get_domain()

    @property
    def domains(self) -> list[str]:
        if self._domains_cache is None:
            self._domains_cache = self._get_domains()
        return self._domains_cache

    @property
    def subdomains(self) -> list[str]:
        suffix = "." + self.root_domain
        return [d[: -len(suffix)] for d in self.domains if d.endswith(suffix)]

    def _get_domains_from_text(self, text: str) -> set[str]:
        domains: set[str] = set()
        regex = re.compile(r"server_name\s+(\S+)\s*;")
        for match in regex.finditer(text):
            domains.add(match[1])
        return domains

    def _join_generated_nginx_conf_text(self) -> str:
        result = ""
        for path, text in self._template_manager.generate():
            if "nginx" in str(path):
                result += text
        return result

    def _get_domains(self) -> list[str]:
        text = self._join_generated_nginx_conf_text()
        domains = self._get_domains_from_text(text)
        domains.remove(self.root_domain)
        return [self.root_domain, *domains]

    def _print_domains(self) -> None:
        for domain in self.domains:
            print(domain)

    def _certbot_command(
        self,
        action: CertbotAction | str,
        test: bool,
        *,
        docker=True,
        standalone=None,
        email=None,
        agree_tos=True,
    ) -> str:
        if isinstance(action, str):
            action = CertbotAction[action.upper()]

        command_args = []

        add_domain_option = True
        if action is CertbotAction.CREATE:
            if standalone is None:
                standalone = True
            command_action = "certonly"
        elif action in [CertbotAction.EXPAND, CertbotAction.SHRINK]:
            if standalone is None:
                standalone = False
            command_action = "certonly"
        elif action is CertbotAction.RENEW:
            if standalone is None:
                standalone = False
            add_domain_option = False
            command_action = "renew"
        else:
            raise CruInternalError("Invalid certbot action.")

        data_dir = self.app.data_dir.full_path.as_posix()

        if not docker:
            command_args.append("certbot")
        else:
            command_args.extend(
                [
                    "docker run -it --rm --name certbot",
                    f'-v "{data_dir}/certbot/certs:/etc/letsencrypt"',
                    f'-v "{data_dir}/certbot/data:/var/lib/letsencrypt"',
                ]
            )
            if standalone:
                command_args.append('-p "0.0.0.0:80:80"')
            else:
                command_args.append(f'-v "{data_dir}/certbot/webroot:/var/www/certbot"')

            command_args.append("certbot/certbot")

        command_args.append(command_action)

        command_args.append(f"--cert-name {self.root_domain}")

        if standalone:
            command_args.append("--standalone")
        else:
            command_args.append("--webroot -w /var/www/certbot")

        if add_domain_option:
            command_args.append(" ".join([f"-d {domain}" for domain in self.domains]))

        if email is not None:
            command_args.append(f"--email {email}")

        if agree_tos:
            command_args.append("--agree-tos")

        if test:
            command_args.append("--test-cert --dry-run")

        return " ".join(command_args)

    def print_all_certbot_commands(self, test: bool):
        print("### COMMAND: (standalone) create certs")
        print(
            self._certbot_command(
                CertbotAction.CREATE,
                test,
                email=self._template_manager.get_email(),
            )
        )
        print()
        print("### COMMAND: (webroot+nginx) expand or shrink certs")
        print(
            self._certbot_command(
                CertbotAction.EXPAND,
                test,
                email=self._template_manager.get_email(),
            )
        )
        print()
        print("### COMMAND: (webroot+nginx) renew certs")
        print(
            self._certbot_command(
                CertbotAction.RENEW,
                test,
                email=self._template_manager.get_email(),
            )
        )

    @property
    def _cert_path_str(self) -> str:
        return str(
            self.app.data_dir.full_path
            / "certbot/certs/live"
            / self.root_domain
            / "fullchain.pem"
        )

    def get_command_info(self):
        return "nginx", "Manage nginx related things."

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="nginx_command", required=True, metavar="NGINX_COMMAND"
        )
        _list_parser = subparsers.add_parser("list", help="list domains")
        certbot_parser = subparsers.add_parser("certbot", help="print certbot commands")
        certbot_parser.add_argument(
            "--no-test",
            action="store_true",
            help="remove args making certbot run in test mode",
        )

    def run_command(self, args: Namespace) -> None:
        if args.nginx_command == "list":
            self._print_domains()
        elif args.nginx_command == "certbot":
            self.print_all_certbot_commands(not args.no_test)

    def _generate_dns_zone(
        self,
        ip: str,
        /,
        ttl: str | int = 600,
        *,
        enable_mail: bool = True,
        dkim: str | None = None,
    ) -> str:
        # TODO: Not complete and test now.
        root_domain = self.root_domain
        result = f"$ORIGIN {root_domain}.\n\n"
        result += "; A records\n"
        result += f"@ {ttl} IN A {ip}\n"
        for subdomain in self.subdomains:
            result += f"{subdomain} {ttl} IN A {ip}\n"

        if enable_mail:
            result += "\n; MX records\n"
            result += f"@ {ttl} IN MX 10 mail.{root_domain}.\n"
            result += "\n; SPF record\n"
            result += f'@ {ttl} IN TXT "v=spf1 mx ~all"\n'
            if dkim is not None:
                result += "\n; DKIM record\n"
                result += f'mail._domainkey {ttl} IN TEXT "{dkim}"'
                result += "\n; DMARC record\n"
                dmarc_options = [
                    "v=DMARC1",
                    "p=none",
                    f"rua=mailto:dmarc.report@{root_domain}",
                    f"ruf=mailto:dmarc.report@{root_domain}",
                    "sp=none",
                    "ri=86400",
                ]
                result += f'_dmarc {ttl} IN TXT "{"; ".join(dmarc_options)}"\n'
        return result

    def _get_dkim_from_mailserver(self) -> str | None:
        # TODO: Not complete and test now.
        dkim_path = (
            self.app.data_dir.full_path
            / "dms/config/opendkim/keys"
            / self.root_domain
            / "mail.txt"
        )
        if not dkim_path.exists():
            return None

        p = subprocess.run(["sudo", "cat", dkim_path], capture_output=True, check=True)
        value = ""
        for match in re.finditer('"(.*)"', p.stdout.decode("utf-8")):
            value += match.group(1)
        return value

    def _generate_dns_zone_with_dkim(self, ip: str, /, ttl: str | int = 600) -> str:
        # TODO: Not complete and test now.
        return self._generate_dns_zone(
            ip, ttl, enable_mail=True, dkim=self._get_dkim_from_mailserver()
        )
