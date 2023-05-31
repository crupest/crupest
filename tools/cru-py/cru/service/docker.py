import shutil


class DockerController:
    DOCKER_BIN_NAME = "docker"

    def __init__(self, docker_bin: None | str = None) -> None:
        self._docker_bin = docker_bin

    @property
    def docker_bin(self) -> str:
        if self._docker_bin is None:
            self._docker_bin = shutil.which(self.DOCKER_BIN_NAME)
        return self._docker_bin

