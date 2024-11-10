from ._base import AppCommandFeatureProvider
from ._nginx import NginxManager


class CliToolCommandProvider(AppCommandFeatureProvider):
    def __init__(self) -> None:
        super().__init__("cli-tool-command-provider")

    def setup(self):
        pass

    def get_command_info(self):
        return ("gen-cli", "Get commands of running external cli tools.")

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="gen_cli_command", required=True, metavar="GEN_CLI_COMMAND"
        )
        certbot_parser = subparsers.add_parser("certbot", help="print certbot commands")
        certbot_parser.add_argument(
            "-t", "--test", action="store_true", help="run certbot in test mode"
        )
        _install_docker_parser = subparsers.add_parser(
            "install-docker", help="print docker commands"
        )

    def _print_install_docker_commands(self) -> None:
        output = """
### COMMAND: uninstall apt docker
for pkg in docker.io docker-doc docker-compose \
podman-docker containerd runc; \
do sudo apt-get remove $pkg; done

### COMMAND: prepare apt certs
sudo apt-get update
sudo apt-get install ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings

### COMMAND: install certs
sudo curl -fsSL https://download.docker.com/linux/debian/gpg \
-o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

### COMMAND: add docker apt source
echo \\
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] \
https://download.docker.com/linux/debian \\
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \\
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

### COMMAND: update apt and install docker
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io \
docker-buildx-plugin docker-compose-plugin

### COMMAND: setup system for docker
sudo systemctl enable docker
sudo systemctl start docker
sudo groupadd -f docker
sudo usermod -aG docker $USER
# Remember to log out and log back in for the group changes to take effect
""".strip()
        print(output)

    def run_command(self, args):
        if args.gen_cli_command == "certbot":
            self.app.get_feature(NginxManager).print_all_certbot_commands(args.test)
        elif args.gen_cli_command == "install-docker":
            self._print_install_docker_commands()
