from __future__ import annotations

import random
import secrets
import string
import uuid
from abc import abstractmethod, ABCMeta
from collections.abc import Callable
from typing import Any, ClassVar, TypeVar, Generic

from ._error import CruException


def _str_case_in(s: str, case: bool, str_list: list[str]) -> bool:
    if case:
        return s in str_list
    else:
        return s.lower() in [s.lower() for s in str_list]


_T = TypeVar("_T")


class CruValueTypeError(CruException):
    def __init__(
        self,
        message: str,
        value: Any,
        value_type: ValueType | None,
        *args,
        **kwargs,
    ):
        super().__init__(
            message,
            *args,
            **kwargs,
        )
        self._value = value
        self._value_type = value_type

    @property
    def value(self) -> Any:
        return self._value

    @property
    def value_type(self) -> ValueType | None:
        return self._value_type


class ValueType(Generic[_T], metaclass=ABCMeta):
    def __init__(self, name: str, _type: type[_T]) -> None:
        self._name = name
        self._type = _type

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> type[_T]:
        return self._type

    def check_value_type(self, value: Any) -> None:
        if not isinstance(value, self.type):
            raise CruValueTypeError("Type of value is wrong.", value, self)

    def _do_check_value(self, value: Any) -> _T:
        return value

    def check_value(self, value: Any) -> _T:
        self.check_value_type(value)
        return self._do_check_value(value)

    @abstractmethod
    def _do_check_str_format(self, s: str) -> None:
        raise NotImplementedError()

    def check_str_format(self, s: str) -> None:
        if not isinstance(s, str):
            raise CruValueTypeError("Try to check format on a non-str.", s, self)
        self._do_check_str_format(s)

    @abstractmethod
    def _do_convert_value_to_str(self, value: _T) -> str:
        raise NotImplementedError()

    def convert_value_to_str(self, value: _T) -> str:
        self.check_value(value)
        return self._do_convert_value_to_str(value)

    @abstractmethod
    def _do_convert_str_to_value(self, s: str) -> _T:
        raise NotImplementedError()

    def convert_str_to_value(self, s: str) -> _T:
        self.check_str_format(s)
        return self._do_convert_str_to_value(s)

    def check_value_or_try_convert_from_str(self, value_or_str: Any) -> _T:
        try:
            return self.check_value(value_or_str)
        except CruValueTypeError:
            if isinstance(value_or_str, str):
                return self.convert_str_to_value(value_or_str)
            else:
                raise

    def create_default_value(self) -> _T:
        return self.type()


class TextValueType(ValueType[str]):
    def __init__(self) -> None:
        super().__init__("text", str)

    def _do_check_str_format(self, _s):
        return

    def _do_convert_value_to_str(self, value):
        return value

    def _do_convert_str_to_value(self, s):
        return s


class IntegerValueType(ValueType[int]):
    def __init__(self) -> None:
        super().__init__("integer", int)

    def _do_check_str_format(self, s):
        try:
            int(s)
        except ValueError as e:
            raise CruValueTypeError("Invalid integer format.", s, self) from e

    def _do_convert_value_to_str(self, value):
        return str(value)

    def _do_convert_str_to_value(self, s):
        return int(s)


class FloatValueType(ValueType[float]):
    def __init__(self) -> None:
        super().__init__("float", float)

    def _do_check_str_format(self, s):
        try:
            float(s)
        except ValueError as e:
            raise CruValueTypeError("Invalid float format.", s, self) from e

    def _do_convert_value_to_str(self, value):
        return str(value)

    def _do_convert_str_to_value(self, s):
        return float(s)


class BooleanValueType(ValueType[bool]):
    DEFAULT_TRUE_LIST: ClassVar[list[str]] = ["true", "yes", "y", "on", "1"]
    DEFAULT_FALSE_LIST: ClassVar[list[str]] = ["false", "no", "n", "off", "0"]

    def __init__(
        self,
        *,
        case_sensitive=False,
        true_list: None | list[str] = None,
        false_list: None | list[str] = None,
    ) -> None:
        super().__init__("boolean", bool)
        self._case_sensitive = case_sensitive
        self._valid_true_strs: list[str] = (
            true_list or BooleanValueType.DEFAULT_TRUE_LIST
        )
        self._valid_false_strs: list[str] = (
            false_list or BooleanValueType.DEFAULT_FALSE_LIST
        )

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    @property
    def valid_true_strs(self) -> list[str]:
        return self._valid_true_strs

    @property
    def valid_false_strs(self) -> list[str]:
        return self._valid_false_strs

    @property
    def valid_boolean_strs(self) -> list[str]:
        return self._valid_true_strs + self._valid_false_strs

    def _do_check_str_format(self, s):
        if not _str_case_in(s, self.case_sensitive, self.valid_boolean_strs):
            raise CruValueTypeError("Invalid boolean format.", s, self)

    def _do_convert_value_to_str(self, value):
        return self._valid_true_strs[0] if value else self._valid_false_strs[0]

    def _do_convert_str_to_value(self, s):
        return _str_case_in(s, self.case_sensitive, self._valid_true_strs)

    def create_default_value(self):
        return self.valid_false_strs[0]


class EnumValueType(ValueType[str]):
    def __init__(self, valid_values: list[str], /, case_sensitive=False) -> None:
        super().__init__(f"enum({'|'.join(valid_values)})", str)
        self._case_sensitive = case_sensitive
        self._valid_values = valid_values

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    @property
    def valid_values(self) -> list[str]:
        return self._valid_values

    def _do_check_value(self, value):
        self._do_check_str_format(value)

    def _do_check_str_format(self, s):
        if not _str_case_in(s, self.case_sensitive, self.valid_values):
            raise CruValueTypeError("Invalid enum value", s, self)

    def _do_convert_value_to_str(self, value):
        return value

    def _do_convert_str_to_value(self, s):
        return s

    def create_default_value(self):
        return self.valid_values[0]


TEXT_VALUE_TYPE = TextValueType()
INTEGER_VALUE_TYPE = IntegerValueType()
BOOLEAN_VALUE_TYPE = BooleanValueType()


class ValueGeneratorBase(Generic[_T], metaclass=ABCMeta):
    @abstractmethod
    def generate(self) -> _T:
        raise NotImplementedError()

    def __call__(self) -> _T:
        return self.generate()


class ValueGenerator(ValueGeneratorBase[_T]):
    def __init__(self, generate_func: Callable[[], _T]) -> None:
        self._generate_func = generate_func

    @property
    def generate_func(self) -> Callable[[], _T]:
        return self._generate_func

    def generate(self) -> _T:
        return self._generate_func()


class UuidValueGenerator(ValueGeneratorBase[str]):
    def generate(self):
        return str(uuid.uuid4())


class RandomStringValueGenerator(ValueGeneratorBase[str]):
    def __init__(self, length: int, secure: bool) -> None:
        self._length = length
        self._secure = secure

    @property
    def length(self) -> int:
        return self._length

    @property
    def secure(self) -> bool:
        return self._secure

    def generate(self):
        random_func = secrets.choice if self._secure else random.choice
        characters = string.ascii_letters + string.digits
        random_string = "".join(random_func(characters) for _ in range(self._length))
        return random_string


UUID_VALUE_GENERATOR = UuidValueGenerator()
