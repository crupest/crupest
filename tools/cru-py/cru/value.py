from __future__ import annotations

import random
import secrets
import string
import uuid
from abc import abstractmethod, ABCMeta
from collections.abc import Mapping, Callable
from typing import Any, ClassVar, Literal, TypeVar, Generic, ParamSpec

from .error import CruInternalError, CruException


def _str_case_in(s: str, case: bool, l: list[str]) -> bool:
    if case:
        return s in l
    else:
        return s.lower() in [s.lower() for s in l]


T = TypeVar("T")


class CruValueError(CruException):
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


class CruValueValidationError(CruValueError):
    pass


class CruValueStringConversionError(CruValueError):
    pass


# TODO: Continue here tomorrow!
class ValueType(Generic[T], metaclass=ABCMeta):
    def __init__(self, name: str, _type: type[T]) -> None:
        self._name = name
        self._type = _type

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> type[T]:
        return self._type

    def check_value_type(self, value: Any) -> bool:
        return isinstance(value, self.type)

    def _do_check_value(self, value: Any) -> T:
        return value

    def check_value(self, value: Any) -> T:
        if not isinstance(value, self.type):
            raise CruValueValidationError("Value type is wrong.", value, self)
        return self._do_check_value(value)

    def _do_check_str_format(self, s: str) -> bool | tuple[bool, str]:
        raise NotImplementedError()

    def check_str_format(self, s: str) -> None:
        ok, err = self._do_check_str_format(s)
        if ok is None:
            raise CruInternalLogicError("_do_check_str_format should not return None.")
        if ok:
            return
        if err is None:
            err = "Invalid value str format."
        raise ValueStringConvertionError(err, s, value_type=self)

    @abstractmethod
    def _do_convert_value_to_str(self, value: T) -> str:
        raise NotImplementedError()

    def convert_value_to_str(self, value: T) -> str:
        self.check_value(value)
        return self._do_convert_value_to_str(value)

    @abstractmethod
    def _do_convert_str_to_value(self, s: str) -> T:
        raise NotImplementedError()

    def convert_str_to_value(self, s: str) -> T:
        self.check_str_format(s)
        return self._do_convert_str_to_value(s)

    def check_value_or_try_convert_from_str(self, value_or_str: Any) -> T:
        try:
            return self.check_value(value_or_str)
        except ValidationError as e:
            if isinstance(value_or_str, str):
                return self.convert_str_to_value(value_or_str)
            else:
                raise ValidationError(
                    "Value is not valid and is not a str.", value_or_str, self, inner=e
                )


class TextValueType(ValueType[str]):
    def __init__(self) -> None:
        super().__init__("text")

    def _do_check_str_format(self, s):
        return True

    def _do_convert_value_to_str(self, value):
        return value

    def _do_convert_str_to_value(self, s):
        return s


class IntegerValueType(ValueType[int]):

    def __init__(self) -> None:
        super().__init__("integer")

    def _do_check_str_format(self, s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def _do_convert_value_to_str(self, value):
        return str(value)

    def _do_convert_str_to_value(self, s):
        return int(s)


class FloatValueType(ValueType[float]):
    def __init__(self) -> None:
        super().__init__("float")

    def _do_check_str_format(self, s):
        try:
            float(s)
            return True
        except ValueError:
            return False

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
        super().__init__("boolean")
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
        if _str_case_in(s, self.case_sensitive, self.valid_boolean_strs):
            return True
        return (
            False,
            f"Not a valid boolean string ({ValueType.case_sensitive_to_str(self.case_sensitive)}). Valid string of true: {' '.join(self._valid_true_strs)}. Valid string of false: {' '.join(self._valid_false_strs)}. All is case insensitive.",
        )

    def _do_convert_value_to_str(self, value):
        return "True" if value else "False"

    def _do_convert_str_to_value(self, s):
        return _str_case_in(s, self.case_sensitive, self._valid_true_strs)


class EnumValueType(ValueType[str]):
    def __init__(self, valid_values: list[str], /, case_sensitive=False) -> None:
        s = " | ".join([f'"{v}"' for v in valid_values])
        self._valid_value_str = f"[ {s} ]"
        super().__init__(f"enum{self._valid_value_str}")
        self._case_sensitive = case_sensitive
        self._valid_values = valid_values

    @property
    def case_sensitive(self) -> bool:
        return self._case_sensitive

    @property
    def valid_values(self) -> list[str]:
        return self._valid_values

    def _do_check_value(self, value):
        ok, err = self._do_check_str_format(value)
        return ok, (value if ok else err)

    def _do_check_str_format(self, s):
        if _str_case_in(s, self.case_sensitive, self.valid_values):
            return True
        return (
            False,
            f"Value is not in valid values ({ValueType.case_sensitive_to_str(self.case_sensitive)}): {self._valid_value_str}",
        )

    def _do_convert_value_to_str(self, value):
        return value

    def _do_convert_str_to_value(self, s):
        return s


TEXT_VALUE_TYPE = TextValueType()
INTEGER_VALUE_TYPE = IntegerValueType()
BOOLEAN_VALUE_TYPE = BooleanValueType()

P = ParamSpec("P")


class ValueGenerator(Generic[T, P]):
    INTERACTIVE_KEY: ClassVar[Literal["interactive"]] = "interactive"

    def __init__(
        self, f: Callable[P, T], /, attributes: None | Mapping[str, Any] = None
    ) -> None:
        self._f = f
        self._attributes = attributes or {}

    @property
    def f(self) -> Callable[P, T]:
        return self._f

    @property
    def attributes(self) -> Mapping[str, Any]:
        return self._attributes

    def generate(self, *args, **kwargs) -> T:
        return self._f(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        return self._f(*args, **kwargs)

    @property
    def interactive(self) -> bool:
        return self._attributes.get(ValueGenerator.INTERACTIVE_KEY, False)

    @staticmethod
    def create_interactive(
        f: Callable[P, T],
        interactive: bool = True,
        /,
        attributes: None | Mapping[str, Any] = None,
    ) -> "ValueGenerator[T, P]":
        return ValueGenerator(
            f, dict({ValueGenerator.INTERACTIVE_KEY: interactive}, **(attributes or {}))
        )


class UuidValueGenerator(ValueGenerator[str, []]):
    def __init__(self) -> None:
        super().__init__(lambda: str(uuid.uuid4()))


class RandomStringValueGenerator(ValueGenerator[str, []]):
    @staticmethod
    def _create_generate_ramdom_func(length: int, secure: bool) -> Callable[str, []]:
        random_choice = secrets.choice if secure else random.choice

        def generate_random_string():
            characters = string.ascii_letters + string.digits
            random_string = "".join(random_choice(characters) for _ in range(length))
            return random_string

        return generate_random_string

    def __init__(self, length: int, secure: bool) -> None:
        super().__init__(
            RandomStringValueGenerator._create_generate_ramdom_func(length, secure)
        )


UUID_VALUE_GENERATOR = UuidValueGenerator()
