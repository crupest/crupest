from collections.abc import Iterable, Mapping
import os
import os.path
from string import Template

from ._error import CruException


class CruTemplateError(CruException):
    pass


class TemplateFile:
    def __init__(self, source: str, destination_path: str | None):
        self._source = source
        self._destination = destination_path
        self._template: Template | None = None

    @property
    def source(self) -> str:
        return self._source

    @property
    def destination(self) -> str | None:
        return self._destination

    @destination.setter
    def destination(self, value: str | None) -> None:
        self._destination = value

    @property
    def template(self) -> Template:
        if self._template is None:
            return self.reload_template()
        return self._template

    def reload_template(self) -> Template:
        with open(self._source, "r") as f:
            self._template = Template(f.read())
        return self._template

    @property
    def variables(self) -> set[str]:
        return set(self.template.get_identifiers())

    def generate(self, variables: Mapping[str, str]) -> str:
        return self.template.substitute(variables)

    def generate_to_destination(self, variables: Mapping[str, str]) -> None:
        if self._destination is None:
            raise CruTemplateError("No destination specified for this template.")
        with open(self._destination, "w") as f:
            f.write(self.generate(variables))


class TemplateDirectory:
    def __init__(
        self,
        source: str,
        destination: str,
        exclude: Iterable[str],
        file_suffix: str = ".template",
    ):
        self._files: list[TemplateFile] | None = None
        self._source = source
        self._destination = destination
        self._exclude = [os.path.normpath(p) for p in exclude]
        self._file_suffix = file_suffix

    @property
    def files(self) -> list[TemplateFile]:
        if self._files is None:
            return self.reload()
        else:
            return self._files

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
    def file_suffix(self) -> str:
        return self._file_suffix

    @staticmethod
    def _scan_files(
        root_path: str, exclude: list[str], suffix: str | None
    ) -> Iterable[str]:
        for root, _dirs, files in os.walk(root_path):
            for file in files:
                if suffix is None or file.endswith(suffix):
                    path = os.path.join(root, file)
                    path = os.path.relpath(path, root_path)
                    if suffix is not None:
                        path = path[: -len(suffix)]
                    is_exclude = False
                    for exclude_path in exclude:
                        if path.startswith(exclude_path):
                            is_exclude = True
                            break
                    if not is_exclude:
                        yield path

    def reload(self) -> list[TemplateFile]:
        if not os.path.isdir(self.source):
            raise CruTemplateError(
                f"Source directory {self.source} does not exist or is not a directory."
            )
        files = self._scan_files(self.source, self.exclude, self.file_suffix)
        self._files = [
            TemplateFile(
                os.path.join(self._source, file + self.file_suffix),
                os.path.join(self._destination, file),
            )
            for file in files
        ]
        return self._files

    @property
    def variables(self) -> set[str]:
        s = set()
        for file in self.files:
            s.update(file.variables)
        return s

    def generate_to_destination(self, variables: Mapping[str, str]) -> None:
        for file in self.files:
            file.generate_to_destination(variables)

    def extra_files_in_destination(self) -> Iterable[str]:
        source_files = set(os.path.relpath(f.source, self.source) for f in self.files)
        for file in self._scan_files(self.destination, self.exclude, None):
            if file not in source_files:
                yield file
