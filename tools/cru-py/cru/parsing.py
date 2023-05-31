from abc import ABCMeta, abstractmethod
from typing import TypeVar, Generic, NoReturn, Callable

from cru.excp import CruException, CRU_EXCEPTION_ATTR_DEF_REGISTRY

R = TypeVar("R")


class ParseException(CruException):
    LINE_NUMBER_KEY = "line_number"

    CRU_EXCEPTION_ATTR_DEF_REGISTRY.register_with(LINE_NUMBER_KEY, "Line number of the error.")


class Parser(Generic[R], metaclass=ABCMeta):
    def __init__(self, name: str) -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    @abstractmethod
    def parse(self, s: str) -> R:
        raise NotImplementedError()

    def raise_parse_exception(self, s: str, line_number: int | None = None) -> NoReturn:
        a = f" at line {line_number}" if line_number is not None else ""
        raise ParseException(f"Parser {self.name} failed{a}, {s}")


class SimpleLineConfigParser(Parser[list[tuple[str, str]]]):
    def __init__(self) -> None:
        super().__init__(type(self).__name__)

    def _parse(self, s: str, f: Callable[[str, str], None]) -> None:
        for ln, line in enumerate(s.splitlines()):
            line_number = ln + 1
            # check if it's a comment
            if line.strip().startswith("#"):
                continue
            # check if there is a '='
            if line.find("=") == -1:
                self.raise_parse_exception(f"There is even no '='!", line_number)
            # split at first '='
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            f(key, value)

    def parse(self, s: str) -> list[tuple[str, str]]:
        items = []
        self._parse(s, lambda key, value: items.append((key, value)))
        return items

    def parse_to_dict(self, s: str, /, allow_override: bool = False) -> tuple[dict[str, str], list[tuple[str, str]]]:
        d = {}
        duplicate = []

        def add(key: str, value: str) -> None:
            if key in d:
                if allow_override:
                    duplicate.append((key, d[key]))
                    d[key] = value
                else:
                    self.raise_parse_exception(f"Key '{key}' already exists!", None)
            d[key] = value

        self._parse(s, add)
        return d, duplicate
