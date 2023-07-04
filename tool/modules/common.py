from .path import Paths, ensure_dir, ensure_file, create_dir_if_not_exists
from rich.console import Console
from rich.prompt import Prompt, Confirm

Paths = Paths
Prompt = Prompt
Confirm = Confirm
create_dir_if_not_exists = create_dir_if_not_exists
ensure_dir = ensure_dir
ensure_file = ensure_file

MY_NAME = "crupest"


class UserFriendlyException(Exception):
    """
    An exception that is user friendly.
    It usually means that the user has done something wrong.
    The message should be friendly to the user.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


console = Console()
