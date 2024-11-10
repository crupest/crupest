import shutil
import subprocess

from .._util import L


class DockerController:
    DOCKER_BIN_NAME = "docker"

    def __init__(self, docker_bin: None | str = None) -> None:
        self._docker_bin = docker_bin

    @property
    def docker_bin(self) -> str:
        if self._docker_bin is None:
            self._docker_bin = shutil.which(self.DOCKER_BIN_NAME)
        return self._docker_bin

    def list_containers(self) -> L[str]:
        p = subprocess.run([self.docker_bin, "container", "ls", ""], capture_output=True)
        return p.stdout.decode("utf-8").splitlines()

    def restart_container(self, container_name: str) -> None:
        subprocess.run([self.docker_bin, "restart", container_name])