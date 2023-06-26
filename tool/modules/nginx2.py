from typing import Literal, Any, cast, ClassVar
import os
from os.path import join, basename, dirname
import shutil
import subprocess
import re
from re import Pattern
from cryptography.x509 import *
from cryptography.x509.oid import ExtensionOID
import json
import jsonschema

from tool.modules.nginx2 import NginxSourceFile
from .template2 import Template2
from .common import Paths, UserFriendlyException

_server_data_template_filename = "server.json.template"
_server_schema_filename = "server.schema.json"

with open(join(Paths.nginx2_template_dir, _server_schema_filename)) as f:
    server_json_schema = json.load(f)


_domain_template_filename = "domain.conf.template"

NginxSourceFileType = Literal["global", "domain", "http", "https"]


class NginxSourceFile:
    def __init__(self, path: str) -> None:
        """
        path: relative to nginx2_template_dir
        """
        self._path = path
        is_template = path.endswith(".template")
        self._is_template = is_template
        if is_template:
            self._template = Template2.from_file(
                join(Paths.nginx2_template_dir, path))
        else:
            with open(join(Paths.nginx2_template_dir, path)) as f:
                self._content = f.read()

        self._scope: NginxSourceFileType = self._calc_scope()

    @property
    def is_template(self) -> bool:
        return self._is_template

    @property
    def content(self) -> str:
        if self._is_template:
            raise Exception(f"{self._path} is a template file")
        return self._content

    @property
    def template(self) -> Template2:
        if not self._is_template:
            raise Exception(f"{self._path} is not a template file")
        return cast(Template2, self._template)

    @property
    def global_target_filename(self) -> str:
        if self.scope != "global":
            raise Exception(f"{self._path} is not a global file")
        if self.is_template:
            return basename(self._path)[:-len(".template")]
        else:
            return basename(self._path)

    def _calc_scope(self) -> NginxSourceFileType:
        f = basename(self._path)
        d = basename(dirname(self._path))
        if f == _domain_template_filename:
            return "domain"
        elif d in ["global", "http", "https"]:
            return cast(Literal["global", "http", "https"], d)
        else:
            raise Exception(f"Unknown scope for {self._path}")

    @property
    def scope(self) -> NginxSourceFileType:
        return self._scope


_domain_template_source = NginxSourceFile(_domain_template_filename)

_client_max_body_size_source = NginxSourceFile(
    "global/client-max-body-size.conf")
_forbid_unknown_domain_source = NginxSourceFile(
    "global/forbid-unknown-domain.conf")
_ssl_template_source = NginxSourceFile("global/ssl.conf.template")
_websocket_source = NginxSourceFile("global/websocket.conf")

_global_source_files = [
    _client_max_body_size_source,
    _forbid_unknown_domain_source,
    _ssl_template_source,
    _websocket_source
]

_global_target_files = [f.global_target_filename for f in _global_source_files]

_http_444_source = NginxSourceFile("http/444.segment")
_http_redirect_to_https_source = NginxSourceFile(
    "http/redirect-to-https.segment")

_http_source_files = [_http_444_source, _http_redirect_to_https_source]

_https_redirect_template_source = NginxSourceFile(
    "https/redirect.segment.template")
_https_reverse_proxy_template_source = NginxSourceFile(
    "https/reverse-proxy.segment.template")
_https_static_file_template_source = NginxSourceFile(
    "https/static-file.segment.template")
_https_static_file_no_strip_prefix_template_source = NginxSourceFile(
    "https/static-file.no-strip-prefix.segment.template")

_https_source_files = [
    _https_redirect_template_source,
    _https_reverse_proxy_template_source,
    _https_static_file_template_source,
    _https_static_file_no_strip_prefix_template_source
]


class NginxService:
    def __init__(self, type: str, path: str) -> None:
        self.type = type
        self.path = path
        self._check_path(path)

    @staticmethod
    def _check_path(path: str) -> None:
        assert isinstance(path, str)
        if path == "" or path == "/":
            return
        if not path.startswith("/"):
            raise UserFriendlyException("Service path should start with '/'.")
        if path.endswith("/"):
            raise UserFriendlyException(
                "Service path should not end with '/'.")

    def generate_https_segment(self) -> str:
        raise NotImplementedError()


class NginxRedirectService(NginxService):
    def __init__(self, path: str, redirect_url: str, redirect_code: int = 307) -> None:
        if redirect_url.endswith("/"):
            raise UserFriendlyException(
                "Redirect URL should not end with '/'.")

        super().__init__("redirect", path)

        self.redirect_url = redirect_url
        self.redirect_code = redirect_code

    def generate_https_segment(self) -> str:
        vars = {
            "PATH": self.path,
            "REDIRECT_CODE": self.redirect_code,
            "REDIRECT_URL": self.redirect_url
        }
        return _https_redirect_template_source.template.render(vars)

    @staticmethod
    def from_json(json: dict[str, Any]) -> "NginxRedirectService":
        path = json["path"]
        redirect_url = json["to"]
        redirect_code = json.get("code", 307)
        assert isinstance(path, str)
        assert isinstance(redirect_url, str)
        assert isinstance(redirect_code, int)
        return NginxRedirectService(path, redirect_url, redirect_code)


class NginxReverseProxyService(NginxService):

    _upstream_regex: ClassVar[Pattern[str]] = re.compile(
        r"^[-_0-9a-zA-Z]+:[0-9]+$")

    def __init__(self, path: str, upstream: str) -> None:
        if not self._upstream_regex.match(upstream):
            raise UserFriendlyException(
                f"Invalid upstream format: {upstream}.")

        super().__init__("reverse-proxy", path)

        self.upstream = upstream

    def generate_https_segment(self) -> str:
        vars = {
            "PATH": self.path,
            "UPSTREAM": self.upstream
        }
        return _https_reverse_proxy_template_source.template.render(vars)

    @staticmethod
    def from_json(json: dict[str, Any]) -> "NginxReverseProxyService":
        path = json["path"]
        upstream = json["upstream"]
        assert isinstance(path, str)
        assert isinstance(upstream, str)
        return NginxReverseProxyService(path, upstream)


class NginxStaticFileService(NginxService):
    def __init__(self, path: str, root: str, no_strip_prefix: bool = False) -> None:
        super().__init__("static-file", path)

        self.root = root
        self.no_strip_prefix = no_strip_prefix

    def generate_https_segment(self) -> str:
        vars = {
            "PATH": self.path,
            "ROOT": self.root,
        }
        if self.no_strip_prefix:
            return _https_static_file_no_strip_prefix_template_source.template.render(vars)
        else:
            return _https_static_file_template_source.template.render(vars)

    @staticmethod
    def from_json(json: dict[str, Any]) -> "NginxStaticFileService":
        path = json["path"]
        root = json["root"]
        no_strip_prefix = json.get("no_strip_prefix", False)
        assert isinstance(path, str)
        assert isinstance(root, str)
        assert isinstance(no_strip_prefix, bool)
        return NginxStaticFileService(path, root, no_strip_prefix)


def nginx_service_from_json(json: dict[str, Any]) -> NginxService:
    type = json["type"]
    if type == "redirect":
        return NginxRedirectService.from_json(json)
    elif type == "reverse-proxy":
        return NginxReverseProxyService.from_json(json)
    elif type == "static-file":
        return NginxStaticFileService.from_json(json)
    else:
        raise UserFriendlyException(f"Invalid service type: {type}.")


def _prepend_indent(text: str, indent: str = " " * 4) -> str:
    lines = text.split("\n")
    for i in range(len(lines)):
        if lines[i] != "":
            lines[i] = indent + lines[i]
    return "\n".join(lines)


class NginxDomain:
    def __init__(self, domain: str, services: list[NginxService] = []) -> None:
        self.domain = domain
        self.services = services

    def add_service(self, service: NginxService) -> None:
        self.services.append(service)

    def generate_http_segment(self) -> str:
        if len(self.services) == 0:
            return _http_444_source.content
        else:
            return _http_redirect_to_https_source.content

    def generate_https_segment(self) -> str:
        return "\n\n".join([s.generate_https_segment() for s in self.services])

    def generate(self) -> str:
        vars = {
            "DOMAIN": self.domain,
            "HTTP_SEGMENT": _prepend_indent(self.generate_http_segment()),
            "HTTPS_SEGMENT": _prepend_indent(self.generate_https_segment()),
        }
        return _domain_template_source.template.render(vars)

    @staticmethod
    def from_json(root_domain, json: dict[str, Any]) -> "NginxDomain":
        name = json["name"]
        assert isinstance(name, str)
        if name == "@" or name == "":
            domain = root_domain
        else:
            domain = f"{name}.{root_domain}"
        assert isinstance(json["services"], list)
        services = [nginx_service_from_json(s) for s in json["services"]]
        return NginxDomain(domain, services)


class NginxServer:
    def __init__(self, root_domain: str) -> None:
        self.root_domain = root_domain
        self.domains: list[NginxDomain] = []

    def add_sub_domain(self, sub_domain: str, services: list[NginxService]) -> None:
        if sub_domain == "" or sub_domain == "@":
            domain = self.root_domain
        else:
            domain = f"{sub_domain}.{self.root_domain}"
        self.domains.append(NginxDomain(domain, services))

    @staticmethod
    def from_json(root_domain: str, json: dict[str, Any]) -> "NginxServer":
        server = NginxServer(root_domain)
        sub_domains = json["domains"]
        assert isinstance(sub_domains, list)
        server.domains = [NginxDomain.from_json(
            root_domain, d) for d in sub_domains]
        return server


def generate_nginx_config(domain: str, original_config, dest: str) -> None:
    if not isdir(dest):
        raise ValueError('dest must be a directory')
    # copy ssl.conf and https-redirect.conf which need no variable substitution
    for filename in non_template_files:
        src = join(nginx_template_dir, filename)
        dst = join(dest, filename)
        shutil.copyfile(src, dst)
    config = {
        "CRUPEST_DOMAIN": domain,
        "CRUPEST_V2RAY_TOKEN": original_config["CRUPEST_V2RAY_TOKEN"],
        "CRUPEST_V2RAY_PATH": original_config["CRUPEST_V2RAY_PATH"]
    }
    # generate ssl.conf
    with open(join(dest, 'ssl.conf'), 'w') as f:
        f.write(ssl_template.generate(config))
    # generate root.conf
    with open(join(dest, f'{domain}.conf'), 'w') as f:
        root_config = config.copy()
        root_config["CRUPEST_V2RAY_TOKEN"] = config["CRUPEST_V2RAY_TOKEN"]
        root_config["CRUPEST_V2RAY_PATH"] = config["CRUPEST_V2RAY_PATH"]
        f.write(root_template.generate(config))
    # generate nginx config for each site
    sites: list = server["sites"]
    for site in sites:
        subdomain = site["subdomain"]
        local_config = config.copy()
        local_config['CRUPEST_NGINX_SUBDOMAIN'] = subdomain
        if site["type"] == 'static-file':
            template = static_file_template
            local_config['CRUPEST_NGINX_ROOT'] = site["root"]
        elif site["type"] == 'reverse-proxy':
            template = reverse_proxy_template
            local_config['CRUPEST_NGINX_UPSTREAM_NAME'] = site["upstream"]["name"]
            local_config['CRUPEST_NGINX_UPSTREAM_SERVER'] = site["upstream"]["server"]
        elif site["type"] == 'redirect':
            template = redirect_template
            local_config['CRUPEST_NGINX_URL'] = site["url"]
        elif site["type"] == 'cert-only':
            template = cert_only_template
        else:
            raise Exception('Invalid site type')
        with open(join(dest, f'{subdomain}.{domain}.conf'), 'w') as f:
            f.write(template.generate(local_config))


def check_nginx_config_dir(dir_path: str, domain: str) -> list:
    if not exists(dir_path):
        return []
    good_files = [*non_template_files, "ssl.conf", *
                  [f"{full_domain}.conf" for full_domain in list_domains(domain)]]
    bad_files = []
    for path in os.listdir(dir_path):
        file_name = basename(path)
        if file_name not in good_files:
            bad_files.append(file_name)
    return bad_files


def restart_nginx(force=False) -> bool:
    if not force:
        p = subprocess.run(['docker', "container", "ls",
                            "-f", "name=nginx", "-q"], capture_output=True)
        container: str = p.stdout.decode("utf-8")
        if len(container.strip()) == 0:
            return False
    subprocess.run(['docker', 'restart', 'nginx'])
    return True


def nginx(domain: str, config, /, console) -> None:
    bad_files = check_nginx_config_dir(nginx_config_dir, domain)
    if len(bad_files) > 0:
        console.print(
            "WARNING: It seems there are some bad conf files in the nginx config directory:", style="yellow")
        for bad_file in bad_files:
            console.print(bad_file, style="cyan")
        to_delete = Confirm.ask(
            "They will affect nginx in a [red]bad[/] way. Do you want to delete them?", default=True, console=console)
        if to_delete:
            for file in bad_files:
                os.remove(join(nginx_config_dir, file))
    console.print(
        "I have found following var in nginx templates:", style="green")
    for var in nginx_var_set:
        console.print(var, style="magenta")
    if not exists(nginx_config_dir):
        os.mkdir(nginx_config_dir)
        console.print(
            f"Nginx config directory created at [magenta]{nginx_config_dir}[/]", style="green")
    generate_nginx_config(domain, config, dest=nginx_config_dir)
    console.print("Nginx config generated.", style="green")
    if restart_nginx():
        console.print('Nginx restarted.', style="green")


def certbot_command_gen(domain: str, action, /, test=False, no_docker=False, *, standalone=None, email=None, agree_tos=False) -> str:
    domains = list_domains(domain)

    add_domain_option = True
    if action == 'create':
        if standalone == None:
            standalone = True
        certbot_action = "certonly"
    elif action == 'expand':
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
        web_root_segment = ' -v "{project_abs_path}/data/certbot/webroot:/var/www/certbot"'
        command = f'docker run -it --rm --name certbot -v "{project_abs_path}/data/certbot/certs:/etc/letsencrypt" -v "{project_abs_path}/data/certbot/data:/var/lib/letsencrypt"{ expose_segment if  standalone else web_root_segment} certbot/certbot '

    command += certbot_action

    if standalone:
        command += " --standalone"
    else:
        command += ' --webroot -w /var/www/certbot'

    if add_domain_option:
        command += f' -d {" -d ".join(domains)}'

    if email is not None:
        command += f' --email {email}'

    if agree_tos:
        command += ' --agree-tos'

    if test:
        command += " --test-cert --dry-run"

    return command


def get_cert_path(root_domain):
    return join(data_dir, "certbot", "certs", "live", root_domain, "fullchain.pem")


def get_cert_domains(cert_path, root_domain):

    if not exists(cert_path):
        return None

    if not isfile(cert_path):
        return None

    with open(cert_path, 'rb') as f:
        cert = load_pem_x509_certificate(f.read())
        ext = cert.extensions.get_extension_for_oid(
            ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
        domains: list = ext.value.get_values_for_type(DNSName)
        domains.remove(root_domain)
        domains = [root_domain, *domains]
        return domains


def print_create_cert_message(domain, console):
    console.print(
        "Looks like you haven't run certbot to get the init ssl certificates. You may want to run following code to get one:", style="cyan")
    console.print(certbot_command_gen(domain, "create"),
                  soft_wrap=True, highlight=False)


def check_ssl_cert(domain, console):
    cert_path = get_cert_path(domain)
    tmp_cert_path = join(tmp_dir, "fullchain.pem")
    console.print("Temporarily copy cert to tmp...", style="yellow")
    ensure_tmp_dir()
    subprocess.run(
        ["sudo", "cp", cert_path, tmp_cert_path], check=True)
    subprocess.run(["sudo", "chown", str(os.geteuid()),
                   tmp_cert_path], check=True)
    cert_domains = get_cert_domains(tmp_cert_path, domain)
    if cert_domains is None:
        print_create_cert_message(domain, console)
    else:
        cert_domain_set = set(cert_domains)
        domains = set(list_domains(domain))
        if not cert_domain_set == domains:
            console.print(
                "Cert domains are not equal to host domains. Run following command to recreate it with nginx stopped.", style="red")
            console.print(certbot_command_gen(
                domain, "create", standalone=True), soft_wrap=True, highlight=False)
        console.print("Remove tmp cert...", style="yellow")
        os.remove(tmp_cert_path)
