from typing import Literal, cast
import os
from os.path import join
import subprocess
from cryptography.x509 import load_pem_x509_certificate, DNSName, SubjectAlternativeName
from cryptography.x509.oid import ExtensionOID
from .tui import Paths, ensure_file, create_dir_if_not_exists, console

CertbotAction = Literal['create', 'expand', 'shrink', 'renew']


class Certbot:
    def __init__(self, root_domain: str, subdomains: list[str]) -> None:
        """
        subdomain: like ["a", "b.c", ...]
        """
        self.root_domain = root_domain
        self.subdomains = subdomains
        self.domains = [
            root_domain, *[f"{subdomain}.{root_domain}" for subdomain in subdomains]]

    def generate_command(self, action: CertbotAction, /, test=False, no_docker=False, *, standalone=None, email=None, agree_tos=False) -> str:
        add_domain_option = True
        if action == 'create':
            if standalone == None:
                standalone = True
            certbot_action = "certonly"
        elif action == 'expand' or action == 'shrink':
            if standalone == None:
                standalone = False
            certbot_action = "certonly"
        elif action == 'renew':
            if standalone == None:
                standalone = False
            add_domain_option = False
            certbot_action = "renew"
        else:
            raise ValueError('Invalid action')

        if no_docker:
            command = "certbot "
        else:
            expose_segment = ' -p "0.0.0.0:80:80"'
            web_root_segment = f' -v "{Paths.project_abs_path}/data/certbot/webroot:/var/www/certbot"'
            command = f'docker run -it --rm --name certbot -v "{Paths.project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{Paths.project_abs_path}/data/certbot/data:/var/lib/letsencrypt"{ expose_segment if  standalone else web_root_segment} certbot/certbot '

        command += certbot_action

        if standalone:
            command += " --standalone"
        else:
            command += ' --webroot -w /var/www/certbot'

        if add_domain_option:
            command += f' -d {" -d ".join(self.domains)}'

        if email is not None:
            command += f' --email {email}'

        if agree_tos:
            command += ' --agree-tos'

        if test:
            command += " --test-cert --dry-run"

        return command

    def get_cert_path(self) -> str:
        return join(Paths.data_dir, "certbot", "certs", "live", self.root_domain, "fullchain.pem")

    def get_cert_actual_domains(self, cert_path: str | None = None) -> None | list[str]:
        if cert_path is None:
            cert_path = self.get_cert_path()

        if not ensure_file(cert_path):
            return None

        with open(cert_path, 'rb') as f:
            cert = load_pem_x509_certificate(f.read())
            ext = cert.extensions.get_extension_for_oid(
                ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            domains: list[str] = cast(
                SubjectAlternativeName, ext.value).get_values_for_type(DNSName)

            # This weird code is to make sure the root domain is the first one
            if self.root_domain in domains:
                domains.remove(self.root_domain)
                domains = [self.root_domain, *domains]

            return domains

    def print_create_cert_message(self):
        console.print(
            "Looks like you haven't run certbot to get the init ssl certificates. You may want to run following code to get one:", style="cyan")
        console.print(self.generate_command("create"),
                      soft_wrap=True, highlight=False)

    def check_ssl_cert(self, tmp_dir: str = Paths.tmp_dir):
        cert_path = self.get_cert_path()
        tmp_cert_path = join(tmp_dir, "fullchain.pem")
        console.print("Temporarily copy cert to tmp...", style="yellow")
        create_dir_if_not_exists(tmp_dir)
        subprocess.run(
            ["sudo", "cp", cert_path, tmp_cert_path], check=True)
        subprocess.run(["sudo", "chown", str(
            os.geteuid()), tmp_cert_path], check=True)
        cert_domains = self.get_cert_actual_domains(tmp_cert_path)
        if cert_domains is None:
            self.print_create_cert_message()
        else:
            cert_domain_set = set(cert_domains)
            domains = set(self.domains)
            if not cert_domain_set == domains:
                console.print(
                    "Cert domains are not equal to host domains. Run following command to recreate it with nginx stopped.", style="red")
                console.print(self.generate_command(
                    "create", standalone=True), soft_wrap=True, highlight=False)
            console.print("Remove tmp cert...", style="yellow")
            os.remove(tmp_cert_path)
