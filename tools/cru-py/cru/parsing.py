from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import NamedTuple, TypeAlias, TypeVar, Generic, NoReturn, Callable

from ._error import CruException
from ._iter import  CruIterable

_T = TypeVar("_T")


class ParseException(CruException, Generic[_T]):
    def __init__(
        self,
        message,
        parser: Parser[_T],
        text: str,
        line_number: int | None = None,
        *args,
        **kwargs,
    ):
        super().__init__(message, *args, **kwargs)
        self._parser = parser
        self._text = text
        self._line_number = line_number

    @property
    def parser(self) -> Parser[_T]:
        return self._parser

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
        a = line_number and f" at line {line_number}" or ""
        raise ParseException(f"Parser {self.name} failed{a}.", self, text, line_number)


class SimpleLineConfigParserItem(NamedTuple):
    key: str
    value: str
    line_number: int | None = None


SimpleLineConfigParserResult: TypeAlias = CruIterable.IterList[
    SimpleLineConfigParserItem
]


class SimpleLineConfigParser(Parser[SimpleLineConfigParserResult]):
    """
    The parsing result is a list of tuples (key, value, line number).
    """

    Item: TypeAlias = SimpleLineConfigParserItem
    Result: TypeAlias = SimpleLineConfigParserResult

    def __init__(self) -> None:
        super().__init__(type(self).__name__)

    def _parse(self, text: str, callback: Callable[[Item], None]) -> None:
        for ln, line in enumerate(text.splitlines()):
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
            callback(SimpleLineConfigParserItem(key, value, line_number))

    def parse(self, text: str) -> Result:
        result = SimpleLineConfigParserResult()
        self._parse(text, lambda item: result.append(item))
        return result
