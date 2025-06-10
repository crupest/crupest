from abc import ABCMeta, abstractmethod
from collections.abc import Callable, Mapping
from pathlib import Path
from string import Template
from typing import Generic, Self, TypeVar

from ._iter import CruIterator
from ._error import CruException

from .parsing import StrWrapperVarParser


class CruTemplateError(CruException):
    pass


class CruTemplateBase(metaclass=ABCMeta):
    def __init__(self, text: str):
        self._text = text
        self._variables: set[str] | None = None

    @abstractmethod
    def _get_variables(self) -> set[str]:
        raise NotImplementedError()

    @property
    def text(self) -> str:
        return self._text

    @property
    def variables(self) -> set[str]:
        if self._variables is None:
            self._variables = self._get_variables()
        return self._variables

    @property
    def variable_count(self) -> int:
        return len(self.variables)

    @property
    def has_variables(self) -> bool:
        return self.variable_count > 0

    @abstractmethod
    def _do_generate(self, mapping: dict[str, str]) -> str:
        raise NotImplementedError()

    def _generate_partial(
        self, mapping: Mapping[str, str], allow_unused: bool = True
    ) -> str:
        values = dict(mapping)
        if not allow_unused and not len(set(values.keys() - self.variables)) != 0:
            raise CruTemplateError("Unused variables.")
        return self._do_generate(values)

    def generate_partial(
        self, mapping: Mapping[str, str], allow_unused: bool = True
    ) -> Self:
        return self.__class__(self._generate_partial(mapping, allow_unused))

    def generate(self, mapping: Mapping[str, str], allow_unused: bool = True) -> str:
        values = dict(mapping)
        if len(self.variables - values.keys()) != 0:
            raise CruTemplateError(
                f"Missing variables: {self.variables - values.keys()} ."
            )
        return self._generate_partial(values, allow_unused)


class CruTemplate(CruTemplateBase):
    def __init__(self, prefix: str, text: str):
        super().__init__(text)
        self._prefix = prefix
        self._template = Template(text)

    def _get_variables(self) -> set[str]:
        return (
            CruIterator(self._template.get_identifiers())
            .filter(lambda i: i.startswith(self.prefix))
            .to_set()
        )

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def py_template(self) -> Template:
        return self._template

    @property
    def all_variables(self) -> set[str]:
        return set(self._template.get_identifiers())

    def _do_generate(self, mapping: dict[str, str]) -> str:
        return self._template.safe_substitute(mapping)


class CruStrWrapperTemplate(CruTemplateBase):
    def __init__(self, text: str, wrapper: str = "@@"):
        super().__init__(text)
        self._wrapper = wrapper
        self._tokens: StrWrapperVarParser.Result

    @property
    def wrapper(self) -> str:
        return self._wrapper

    def _get_variables(self):
        self._tokens = StrWrapperVarParser(self.wrapper).parse(self.text)
        return (
            self._tokens.cru_iter()
            .filter(lambda t: t.is_var)
            .map(lambda t: t.value)
            .to_set()
        )

    def _do_generate(self, mapping):
        return (
            self._tokens.cru_iter()
            .map(lambda t: mapping[t.value] if t.is_var else t.value)
            .join_str("")
        )


_Template = TypeVar("_Template", bound=CruTemplateBase)


class TemplateTree(Generic[_Template]):
    def __init__(
        self,
        template_generator: Callable[[str], _Template],
        source: str,
        *,
        template_file_suffix: str | None = ".template",
    ):
        """
        If template_file_suffix is not None, the files will be checked according to the
        suffix of the file name. If the suffix matches, the file will be regarded as a
        template file. Otherwise, it will be regarded as a non-template file.
        Content of template file must contain variables that need to be replaced, while
        content of non-template file may not contain any variables.
        If either case is false, it generally means whether the file is a template is
        wrongly handled.
        """
        self._template_generator = template_generator
        self._files: list[tuple[Path, _Template]] = []
        self._source = source
        self._template_file_suffix = template_file_suffix
        self._load()

    @property
    def templates(self) -> list[tuple[Path, _Template]]:
        return self._files

    @property
    def source(self) -> str:
        return self._source

    @property
    def template_file_suffix(self) -> str | None:
        return self._template_file_suffix

    @staticmethod
    def _scan_files(root: str) -> list[Path]:
        root_path = Path(root)
        result: list[Path] = []
        for path in root_path.glob("**/*"):
            if not path.is_file():
                continue
            path = path.relative_to(root_path)
            result.append(Path(path))
        return result

    def _load(self) -> None:
        files = self._scan_files(self.source)
        for file_path in files:
            template_file = Path(self.source) / file_path
            with open(template_file, "r") as f:
                content = f.read()
            template = self._template_generator(content)
            if self.template_file_suffix is not None:
                should_be_template = file_path.name.endswith(self.template_file_suffix)
                if should_be_template and not template.has_variables:
                    raise CruTemplateError(
                        f"Template file {file_path} has no variables."
                    )
                elif not should_be_template and template.has_variables:
                    raise CruTemplateError(f"Non-template {file_path} has variables.")
            self._files.append((file_path, template))

    @property
    def variables(self) -> set[str]:
        s = set()
        for _, template in self.templates:
            s.update(template.variables)
        return s

    def generate(self, variables: Mapping[str, str]) -> list[tuple[Path, str]]:
        result: list[tuple[Path, str]] = []
        for path, template in self.templates:
            if self.template_file_suffix is not None and path.name.endswith(
                self.template_file_suffix
            ):
                path = path.parent / (path.name[: -len(self.template_file_suffix)])

            text = template.generate(variables)
            result.append((path, text))
        return result
