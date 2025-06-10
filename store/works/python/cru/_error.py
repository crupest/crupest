from __future__ import annotations

from typing import NoReturn, cast, overload


class CruException(Exception):
    """Base exception class of all exceptions in cru."""

    @overload
    def __init__(
        self,
        message: None = None,
        *args,
        user_message: str,
        **kwargs,
    ): ...

    @overload
    def __init__(
        self,
        message: str,
        *args,
        user_message: str | None = None,
        **kwargs,
    ): ...

    def __init__(
        self,
        message: str | None = None,
        *args,
        user_message: str | None = None,
        **kwargs,
    ):
        if message is None:
            message = user_message

        super().__init__(
            message,
            *args,
            **kwargs,
        )
        self._message: str
        self._message = cast(str, message)
        self._user_message = user_message

    @property
    def message(self) -> str:
        return self._message

    def get_user_message(self) -> str | None:
        return self._user_message

    def get_message(self, use_user: bool = True) -> str:
        if use_user and self._user_message is not None:
            return self._user_message
        else:
            return self._message

    @property
    def is_internal(self) -> bool:
        return False

    @property
    def is_logic_error(self) -> bool:
        return False


class CruLogicError(CruException):
    """Raised when a logic error occurs."""

    @property
    def is_logic_error(self) -> bool:
        return True


class CruInternalError(CruException):
    """Raised when an internal error occurs."""

    @property
    def is_internal(self) -> bool:
        return True


class CruUnreachableError(CruInternalError):
    """Raised when a code path is unreachable."""


def cru_unreachable() -> NoReturn:
    raise CruUnreachableError("Code should not reach here!")
