from abc import ABCMeta, abstractmethod
from typing import TypeVar, Generic, NoReturn, Callable

from ._error import CruException

_T = TypeVar("_T")


class ParseException(CruException):
    def __init__(
        self, message, text: str, line_number: int | None = None, *args, **kwargs
    ):
        super().__init__(message, *args, **kwargs)
        self._text = text
        self._line_number = line_number

    @property
    def text(self) -> str:
        return self._text

    @property
    def line_number(self) -> int | None:
        return self._line_number


class Parser(Generic[_T], metaclass=ABCMeta):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def parse(self, s: str) -> _T:
        raise NotImplementedError()

    def raise_parse_exception(
        self, text: str, line_number: int | None = None
    ) -> NoReturn:
        a = f" at line {line_number}" if line_number is not None else ""
        raise ParseException(f"Parser {self.name} failed{a}.", text, line_number)


class SimpleLineConfigParser(Parser[list[tuple[str, str]]]):
    def __init__(self) -> None:
        super().__init__(type(self).__name__)

    def _parse(self, s: str, callback: Callable[[str, str], None]) -> None:
        for ln, line in enumerate(s.splitlines()):
            line_number = ln + 1
            # check if it's a comment
            if line.strip().startswith("#"):
                continue
            # check if there is a '='
            if line.find("=") == -1:
                self.raise_parse_exception("There is even no '='!", line_number)
            # split at first '='
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            callback(key, value)

    def parse(self, s: str) -> list[tuple[str, str]]:
        items = []
        self._parse(s, lambda key, value: items.append((key, value)))
        return items

    def parse_to_dict(
        self, s: str, /, allow_override: bool = False
    ) -> tuple[dict[str, str], list[tuple[str, str]]]:
        result: dict[str, str] = {}
        duplicate: list[tuple[str, str]] = []

        def add(key: str, value: str) -> None:
            if key in result:
                if allow_override:
                    duplicate.append((key, result[key]))
                    result[key] = value
                else:
                    self.raise_parse_exception(f"Key '{key}' already exists!", None)
            result[key] = value

        self._parse(s, add)
        return result, duplicate
