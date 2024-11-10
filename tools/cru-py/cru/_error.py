from typing import NoReturn


class CruException(Exception):
    """Base exception class of all exceptions in cru."""


class CruUnreachableError(CruException):
    """Raised when a code path is unreachable."""


def cru_unreachable() -> NoReturn:
    raise CruUnreachableError()


class CruInternalError(CruException):
    """Raised when an internal logic error occurs."""


class CruUserFriendlyException(CruException):
    def __init__(self, message: str, user_message: str, *args, **kwargs) -> None:
        super().__init__(message, *args, **kwargs)
        self._user_message = user_message

    @property
    def user_message(self) -> str:
        return self._user_message
