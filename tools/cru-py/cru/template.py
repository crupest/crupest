from collections.abc import Iterable, Mapping
import os
import os.path
from string import Template

from ._iter import CruIterator
from ._error import CruException


class CruTemplateError(CruException):
    pass


class CruTemplate:
    def __init__(self, prefix: str, text: str):
        self._prefix = prefix
        self._template = Template(text)
        self._variables = (
            CruIterator(self._template.get_identifiers())
            .filter(lambda i: i.startswith(self._prefix))
            .to_set()
        )
        self._all_variables = set(self._template.get_identifiers())

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def real_template(self) -> Template:
        return self._template

    @property
    def variables(self) -> set[str]:
        return self._variables

    @property
    def all_variables(self) -> set[str]:
        return self._all_variables

    @property
    def has_no_variables(self) -> bool:
        return len(self._variables) == 0

    def generate(self, mapping: Mapping[str, str], allow_extra: bool = True) -> str:
        values = dict(mapping)
        if not self.variables <= set(values.keys()):
            raise CruTemplateError("Missing variables.")
        if not allow_extra and not set(values.keys()) <= self.variables:
            raise CruTemplateError("Extra variables.")
        return self._template.safe_substitute(values)


class CruTemplateFile(CruTemplate):
    def __init__(self, prefix: str, source: str, destination_path: str):
        self._source = source
        self._destination = destination_path
        with open(source, "r") as f:
            super().__init__(prefix, f.read())

    @property
    def source(self) -> str:
        return self._source

    @property
    def destination(self) -> str | None:
        return self._destination

    def generate_to_destination(
        self, mapping: Mapping[str, str], allow_extra: bool = True
    ) -> None:
        with open(self._destination, "w") as f:
            f.write(self.generate(mapping, allow_extra))


class TemplateTree:
    def __init__(
        self,
        prefix: str,
        source: str,
        destination: str,
        exclude: Iterable[str],
        template_file_suffix: str = ".template",
    ):
        self._prefix = prefix
        self._files: list[CruTemplateFile] | None = None
        self._source = source
        self._destination = destination
        self._exclude = [os.path.normpath(p) for p in exclude]
        self._template_file_suffix = template_file_suffix

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def files(self) -> list[CruTemplateFile]:
        if self._files is None:
            self.reload()
        return self._files  # type: ignore

    @property
    def template_files(self) -> list[CruTemplateFile]:
        return (
            CruIterator(self.files).filter(lambda f: not f.has_no_variables).to_list()
        )

    @property
    def non_template_files(self) -> list[CruTemplateFile]:
        return CruIterator(self.files).filter(lambda f: f.has_no_variables).to_list()

    @property
    def source(self) -> str:
        return self._source

    @property
    def destination(self) -> str:
        return self._destination

    @property
    def exclude(self) -> list[str]:
        return self._exclude

    @property
    def template_file_suffix(self) -> str:
        return self._template_file_suffix

    @staticmethod
    def _scan_files(root_path: str, exclude: list[str]) -> Iterable[str]:
        for root, _dirs, files in os.walk(root_path):
            for file in files:
                path = os.path.join(root, file)
                path = os.path.relpath(path, root_path)
                is_exclude = False
                for exclude_path in exclude:
                    if path.startswith(exclude_path):
                        is_exclude = True
                        break
                if not is_exclude:
                    yield path

    def reload(self, strict=True) -> None:
        self._files = []
        file_names = self._scan_files(self.source, self.exclude)
        for file_name in file_names:
            source = os.path.join(self.source, file_name)
            destination = os.path.join(self.destination, file_name)
            file = CruTemplateFile(self._prefix, source, destination)
            if file_name.endswith(self.template_file_suffix):
                if strict and file.has_no_variables:
                    raise CruTemplateError(
                        f"Template file {file_name} has no variables."
                    )
            else:
                if strict and not file.has_no_variables:
                    raise CruTemplateError(f"Non-template {file_name} has variables.")
            self._files.append(file)

    @property
    def variables(self) -> set[str]:
        s = set()
        for file in self.files:
            s.update(file.variables)
        return s

    def generate_to_destination(self, variables: Mapping[str, str]) -> None:
        for file in self.files:
            file.generate_to_destination(variables)
