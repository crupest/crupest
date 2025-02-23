from dataclasses import dataclass, replace
from typing import TypeAlias

from ._base import AppCommandFeatureProvider
from ._nginx import NginxManager

_Str_Or_Cmd_List: TypeAlias = str | list["_Cmd"]


@dataclass
class _Cmd:
    name: str
    desc: str
    cmd: _Str_Or_Cmd_List

    def clean(self) -> "_Cmd":
        if isinstance(self.cmd, list):
            return replace(
                self,
                cmd=[cmd.clean() for cmd in self.cmd],
            )
        elif isinstance(self.cmd, str):
            return replace(self, cmd=self.cmd.strip())
        else:
            raise ValueError("Unexpected type for cmd.")

    def generate_text(
        self,
        info_only: bool,
        *,
        parent: str | None = None,
    ) -> str:
        if parent is None:
            tag = "COMMAND"
            long_name = self.name
            indent = ""
        else:
            tag = "SUBCOMMAND"
            long_name = f"{parent}.{self.name}"
            indent = "  "

        if info_only:
            return f"{indent}[{long_name}]: {self.desc}"

        text = f"--- {tag}[{long_name}]: {self.desc}"
        if isinstance(self.cmd, str):
            text += "\n" + self.cmd
        elif isinstance(self.cmd, list):
            for sub in self.cmd:
                text += "\n" * 2 + sub.generate_text(info_only, parent=self.name)
        else:
            raise ValueError("Unexpected type for cmd.")

        lines: list[str] = []
        for line in text.splitlines():
            if len(line) == 0:
                lines.append("")
            else:
                lines.append(indent + line)
        text = "\n".join(lines)

        return text


_docker_uninstall = _Cmd(
    "uninstall",
    "uninstall apt docker",
    """
for pkg in docker.io docker-doc docker-compose \
podman-docker containerd runc; \
do sudo apt-get remove $pkg; done
""",
)

_docker_apt_certs = _Cmd(
    "apt-certs",
    "prepare apt certs",
    """
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
""",
)

_docker_docker_certs = _Cmd(
    "docker-certs",
    "add docker certs",
    """
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
-o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
""",
)

_docker_apt_repo = _Cmd(
    "apt-repo",
    "add docker apt repo",
    """
echo \\
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/debian \\
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \\
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
""",
)

_docker_install = _Cmd(
    "install",
    "update apt and install docker",
    """
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io \
docker-buildx-plugin docker-compose-plugin
""",
)

_docker_setup = _Cmd(
    "setup",
    "setup system for docker",
    """
sudo systemctl enable docker
sudo systemctl start docker
sudo groupadd -f docker
sudo usermod -aG docker $USER
# Remember to log out and log back in for the group changes to take effect
""",
)

_docker = _Cmd(
    "install-docker",
    "install docker for a fresh new system",
    [
        _docker_uninstall,
        _docker_apt_certs,
        _docker_docker_certs,
        _docker_apt_repo,
        _docker_install,
        _docker_setup,
    ],
)

_update_blog = _Cmd(
    "update-blog",
    "re-generate blog pages",
    """
docker exec -it blog /scripts/update.bash
""",
)

_git_user = _Cmd(
    "git-user",
    "add/set git server user and password",
    """
docker run -it --rm -v "$ps_file:/user-info" httpd htpasswd "/user-info" [username]
""",
)


class GenCmdProvider(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("gen-cmd-provider")
        self._cmds: dict[str, _Cmd] = {}
        self._register_cmds(_docker, _update_blog, _git_user)

    def _register_cmd(self, cmd: "_Cmd"):
        self._cmds[cmd.name] = cmd.clean()

    def _register_cmds(self, *cmds: "_Cmd"):
        for c in cmds:
            self._register_cmd(c)

    def setup(self):
        pass

    def get_command_info(self):
        return ("gen-cmd", "Get commands of running external cli tools.")

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="gen_cmd", metavar="GEN_CMD_COMMAND"
        )
        certbot_parser = subparsers.add_parser("certbot", help="print certbot commands")
        certbot_parser.add_argument(
            "-t", "--test", action="store_true", help="run certbot in test mode"
        )
        for cmd in self._cmds.values():
            subparsers.add_parser(cmd.name, help=cmd.desc)

    def _print_cmd(self, name: str):
        print(self._cmds[name].generate_text(False))

    def run_command(self, args):
        if args.gen_cmd is None or args.gen_cmd == "list":
            print("[certbot]: certbot ssl cert commands")
            for cmd in self._cmds.values():
                print(cmd.generate_text(True))
        elif args.gen_cmd == "certbot":
            self.app.get_feature(NginxManager).print_all_certbot_commands(args.test)
        else:
            self._print_cmd(args.gen_cmd)
