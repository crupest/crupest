import json
import os
import re
import subprocess
from typing import Literal, Any, cast, ClassVar

import jsonschema


def restart_nginx(force=False) -> bool:
    if not force:
        p = subprocess.run(['docker', "container", "ls",
                            "-f", "name=nginx", "-q"], capture_output=True)
        container: str = p.stdout.decode("utf-8")
        if len(container.strip()) == 0:
            return False
    subprocess.run(['docker', 'restart', 'nginx'])
    return True


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
        filename = basename(path)
        self.name = filename[:-len(".template")] if is_template else filename
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

_http_444_source = NginxSourceFile("http/444.segment")
_http_redirect_to_https_source = NginxSourceFile(
    "http/redirect-to-https.segment")

_https_redirect_template_source = NginxSourceFile(
    "https/redirect.segment.template")
_https_reverse_proxy_template_source = NginxSourceFile(
    "https/reverse-proxy.segment.template")
_https_static_file_template_source = NginxSourceFile(
    "https/static-file.segment.template")
_https_static_file_no_strip_prefix_template_source = NginxSourceFile(
    "https/static-file.no-strip-prefix.segment.template")


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

    _upstream_regex: ClassVar[re.Pattern[str]] = re.compile(
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
        raise UserFriendlyException(f"Invalid crupest type: {type}.")


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

    def generate_config(self) -> str:
        vars = {
            "DOMAIN": self.domain,
            "HTTP_SEGMENT": _prepend_indent(self.generate_http_segment()),
            "HTTPS_SEGMENT": _prepend_indent(self.generate_https_segment()),
        }
        return _domain_template_source.template.render(vars)

    def generate_config_file(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.generate_config())

    @staticmethod
    def from_json(root_domain: str, json: dict[str, Any]) -> "NginxDomain":
        name = json["name"]
        assert isinstance(name, str)
        if name == "@" or name == "":
            domain = root_domain
        else:
            domain = f"{name}.{root_domain}"
        assert isinstance(json["services"], list)
        services = [nginx_service_from_json(s) for s in json["services"]]
        return NginxDomain(domain, services)


def check_nginx_config_schema(json: Any) -> None:
    jsonschema.validate(json, server_json_schema)


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

    def generate_ssl(self) -> str:
        return _ssl_template_source.template.render({
            "ROOT_DOMAIN": self.root_domain
        })

    def generate_global_files(self, d: str) -> None:
        for source in [_client_max_body_size_source, _forbid_unknown_domain_source, _websocket_source]:
            with open(join(d, source.name), "w") as f:
                f.write(source.content)
        with open(join(d, _ssl_template_source.name), "w") as f:
            f.write(self.generate_ssl())

    def generate_domain_files(self, d: str) -> None:
        for domain in self.domains:
            domain.generate_config_file(join(d, f"{domain.domain}.conf"))

    def generate_config(self, d: str) -> None:
        create_dir_if_not_exists(d)
        self.generate_global_files(d)

    def get_allowed_files(self) -> list[str]:
        files = []
        for source in [_client_max_body_size_source, _forbid_unknown_domain_source, _ssl_template_source, _websocket_source]:
            files.append(source.name)
        for domain in self.domains:
            files.append(f"{domain.domain}.conf")
        return files

    def check_bad_files(self, d: str) -> list[str]:
        allowed_files = self.get_allowed_files()
        bad_files = []
        if not ensure_dir(d, must_exist=False):
            return []
        for path in os.listdir(d):
            if path not in allowed_files:
                bad_files.append(path)
        return bad_files

    @staticmethod
    def from_json(root_domain: str, json: dict[str, Any]) -> "NginxServer":
        check_nginx_config_schema(json)
        server = NginxServer(root_domain)
        sub_domains = json["domains"]
        assert isinstance(sub_domains, list)
        server.domains = [NginxDomain.from_json(
            root_domain, d) for d in sub_domains]
        return server

    @staticmethod
    def from_json_str(root_domain: str, json_str: str) -> "NginxServer":
        return NginxServer.from_json(root_domain, json.loads(json_str))

    def go(self):
        bad_files = self.check_bad_files(Paths.nginx_generated_dir)
        if len(bad_files) > 0:
            console.print(
                "WARNING: It seems there are some bad conf files in the nginx config directory:", style="yellow")
            for bad_file in bad_files:
                console.print(bad_file, style=file_name_style)
            to_delete = Confirm.ask(
                "They will affect nginx in a [red]bad[/] way. Do you want to delete them?", default=True, console=console)
            if to_delete:
                for file in bad_files:
                    os.remove(join(Paths.nginx_generated_dir, file))
        create_dir_if_not_exists(Paths.generated_dir)
        if not ensure_dir(Paths.nginx_generated_dir, must_exist=False):
            os.mkdir(Paths.nginx_generated_dir)
            console.print(
                f"Nginx config directory created at [magenta]{Paths.nginx_generated_dir}[/]", style="green")
        self.generate_config(Paths.nginx_generated_dir)
        console.print("Nginx config generated.", style="green")
        if restart_nginx():
            console.print('Nginx restarted.', style="green")
