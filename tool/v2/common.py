from rich.console import Console
import os.path
from paths import Paths as P

Paths = P


def ensure_file(file: str) -> bool:
    if os.path.exists(file) and not os.path.isfile(file):
        raise UserFriendlyException(
            "Path should be a file but is something else: " + file)
    if not os.path.exists(file):
        with open(file, 'w') as f:
            f.write("")
        return False
    return True


def ensure_dir(dir: str):
    if os.path.exists(dir) and not os.path.isdir(dir):
        raise UserFriendlyException(
            "Path should be a directory but is something else: " + dir)
    if not os.path.exists(dir):
        os.makedirs(dir)


console = Console()


class UserFriendlyException(Exception):
    """
    An exception that is user friendly.
    It usually means that the user has done something wrong.
    The message should be friendly to the user.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
