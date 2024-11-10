import subprocess

from cru.tool import ExternalTool


class DockerController(ExternalTool):
    DOCKER_BIN_NAME = "docker"

    def __init__(self, docker_bin: None | str = None) -> None:
        super().__init__(docker_bin or self.DOCKER_BIN_NAME)

    def list_containers(self) -> L[str]:
        p = subprocess.run(
            [self.docker_bin, "container", "ls", ""], capture_output=True
        )
        return p.stdout.decode("utf-8").splitlines()

    def restart_container(self, container_name: str) -> None:
        subprocess.run([self.docker_bin, "restart", container_name])
