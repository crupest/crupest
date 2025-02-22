import shutil
import subprocess
from typing import Any
from collections.abc import Iterable

from ._error import CruException


class CruExternalToolError(CruException):
    def __init__(self, message: str, tool: str, *args, **kwargs) -> None:
        super().__init__(message, *args, **kwargs)
        self._tool = tool

    @property
    def tool(self) -> str:
        return self._tool


class CruExternalToolNotFoundError(CruExternalToolError):
    def __init__(self, message: str | None, tool: str, *args, **kwargs) -> None:
        super().__init__(
            message or f"Could not find binary for {tool}.", tool, *args, **kwargs
        )


class CruExternalToolRunError(CruExternalToolError):
    def __init__(
        self,
        message: str,
        tool: str,
        tool_args: Iterable[str],
        tool_error: Any,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(message, tool, *args, **kwargs)
        self._tool_args = list(tool_args)
        self._tool_error = tool_error

    @property
    def tool_args(self) -> list[str]:
        return self._tool_args

    @property
    def tool_error(self) -> Any:
        return self._tool_error


class ExternalTool:
    def __init__(self, bin: str) -> None:
        self._bin = bin

    @property
    def bin(self) -> str:
        return self._bin

    @bin.setter
    def bin(self, value: str) -> None:
        self._bin = value

    @property
    def bin_path(self) -> str:
        real_bin = shutil.which(self.bin)
        if not real_bin:
            raise CruExternalToolNotFoundError(None, self.bin)
        return real_bin

    def run(
        self, *process_args: str, **subprocess_kwargs
    ) -> subprocess.CompletedProcess:
        try:
            return subprocess.run(
                [self.bin_path] + list(process_args), **subprocess_kwargs
            )
        except subprocess.CalledProcessError as e:
            raise CruExternalToolError("Subprocess failed.", self.bin) from e
        except OSError as e:
            raise CruExternalToolError("Failed to start subprocess", self.bin) from e

    def run_get_output(self, *process_args: str, **subprocess_kwargs) -> Any:
        process = self.run(*process_args, capture_output=True, **subprocess_kwargs)
        return process.stdout
