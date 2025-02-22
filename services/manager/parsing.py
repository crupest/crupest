from __future__ import annotations

from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import NamedTuple, TypeAlias, TypeVar, Generic, NoReturn, Callable

from ._error import CruException
from ._iter import CruIterable

_T = TypeVar("_T")


class StrParseStream:
    class MemStackEntry(NamedTuple):
        pos: int
        lineno: int

    class MemStackPopStr(NamedTuple):
        text: str
        lineno: int

    def __init__(self, text: str) -> None:
        self._text = text
        self._pos = 0
        self._lineno = 1
        self._length = len(self._text)
        self._valid_pos_range = range(0, self.length + 1)
        self._valid_offset_range = range(-self.length, self.length + 1)
        self._mem_stack: CruIterable.IterList[StrParseStream.MemStackEntry] = (
            CruIterable.IterList()
        )

    @property
    def text(self) -> str:
        return self._text

    @property
    def length(self) -> int:
        return self._length

    @property
    def valid_pos_range(self) -> range:
        return self._valid_pos_range

    @property
    def valid_offset_range(self) -> range:
        return self._valid_offset_range

    @property
    def pos(self) -> int:
        return self._pos

    @property
    def lineno(self) -> int:
        return self._lineno

    @property
    def eof(self) -> bool:
        return self._pos == self.length

    def peek(self, length: int) -> str:
        real_length = min(length, self.length - self._pos)
        new_position = self._pos + real_length
        text = self._text[self._pos : new_position]
        return text

    def read(self, length: int) -> str:
        text = self.peek(length)
        self._pos += len(text)
        self._lineno += text.count("\n")
        return text

    def skip(self, length: int) -> None:
        self.read(length)

    def peek_str(self, text: str) -> bool:
        if self.pos + len(text) > self.length:
            return False
        for offset in range(len(text)):
            if self._text[self.pos + offset] != text[offset]:
                return False
        return True

    def read_str(self, text: str) -> bool:
        if not self.peek_str(text):
            return False
        self._pos += len(text)
        self._lineno += text.count("\n")
        return True

    @property
    def mem_stack(self) -> CruIterable.IterList[MemStackEntry]:
        return self._mem_stack

    def push_mem(self) -> None:
        self.mem_stack.append(self.MemStackEntry(self.pos, self.lineno))

    def pop_mem(self) -> MemStackEntry:
        return self.mem_stack.pop()

    def pop_mem_str(self, strip_end: int = 0) -> MemStackPopStr:
        old = self.pop_mem()
        assert self.pos >= old.pos
        return self.MemStackPopStr(
            self._text[old.pos : self.pos - strip_end], old.lineno
        )


class ParseError(CruException, Generic[_T]):
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
        raise ParseError(f"Parser {self.name} failed{a}.", self, text, line_number)


class _SimpleLineVarParserEntry(NamedTuple):
    key: str
    value: str
    line_number: int | None = None


class _SimpleLineVarParserResult(CruIterable.IterList[_SimpleLineVarParserEntry]):
    pass


class SimpleLineVarParser(Parser[_SimpleLineVarParserResult]):
    """
    The parsing result is a list of tuples (key, value, line number).
    """

    Entry: TypeAlias = _SimpleLineVarParserEntry
    Result: TypeAlias = _SimpleLineVarParserResult

    def __init__(self) -> None:
        super().__init__(type(self).__name__)

    def _parse(self, text: str, callback: Callable[[Entry], None]) -> None:
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
            callback(_SimpleLineVarParserEntry(key, value, line_number))

    def parse(self, text: str) -> Result:
        result = _SimpleLineVarParserResult()
        self._parse(text, lambda item: result.append(item))
        return result


class _StrWrapperVarParserTokenKind(Enum):
    TEXT = "TEXT"
    VAR = "VAR"


@dataclass
class _StrWrapperVarParserToken:
    kind: _StrWrapperVarParserTokenKind
    value: str
    line_number: int

    @property
    def is_text(self) -> bool:
        return self.kind is _StrWrapperVarParserTokenKind.TEXT

    @property
    def is_var(self) -> bool:
        return self.kind is _StrWrapperVarParserTokenKind.VAR

    @staticmethod
    def from_mem_str(
        kind: _StrWrapperVarParserTokenKind, mem_str: StrParseStream.MemStackPopStr
    ) -> _StrWrapperVarParserToken:
        return _StrWrapperVarParserToken(kind, mem_str.text, mem_str.lineno)

    def __repr__(self) -> str:
        return f"VAR: {self.value}" if self.is_var else "TEXT: ..."


class _StrWrapperVarParserResult(CruIterable.IterList[_StrWrapperVarParserToken]):
    pass


class StrWrapperVarParser(Parser[_StrWrapperVarParserResult]):
    TokenKind: TypeAlias = _StrWrapperVarParserTokenKind
    Token: TypeAlias = _StrWrapperVarParserToken
    Result: TypeAlias = _StrWrapperVarParserResult

    def __init__(self, wrapper: str):
        super().__init__(f"StrWrapperVarParser({wrapper})")
        self._wrapper = wrapper

    @property
    def wrapper(self) -> str:
        return self._wrapper

    def parse(self, text: str) -> Result:
        result = self.Result()

        class _State(Enum):
            TEXT = "TEXT"
            VAR = "VAR"

        state = _State.TEXT
        stream = StrParseStream(text)
        stream.push_mem()

        while True:
            if stream.eof:
                break

            if stream.read_str(self.wrapper):
                if state is _State.TEXT:
                    result.append(
                        self.Token.from_mem_str(
                            self.TokenKind.TEXT, stream.pop_mem_str(len(self.wrapper))
                        )
                    )
                    state = _State.VAR
                    stream.push_mem()
                else:
                    result.append(
                        self.Token.from_mem_str(
                            self.TokenKind.VAR,
                            stream.pop_mem_str(len(self.wrapper)),
                        )
                    )
                    state = _State.TEXT
                    stream.push_mem()

                continue

            stream.skip(1)

        if state is _State.VAR:
            raise ParseError("Text ended without closing variable.", self, text)

        mem_str = stream.pop_mem_str()
        if len(mem_str.text) != 0:
            result.append(self.Token.from_mem_str(self.TokenKind.TEXT, mem_str))

        return result
