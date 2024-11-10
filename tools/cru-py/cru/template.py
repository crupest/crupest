from collections.abc import Mapping
import os
import os.path
from pathlib import Path
from string import Template

from ._path import CruPath
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
    def raw_text(self) -> str:
        return self._template.template

    @property
    def py_template(self) -> Template:
        return self._template

    @property
    def variables(self) -> set[str]:
        return self._variables

    @property
    def all_variables(self) -> set[str]:
        return self._all_variables

    @property
    def has_variables(self) -> bool:
        """
        If the template does not has any variables that starts with the given prefix,
        it returns False. This usually indicates that the template is not a real
        template and should be copied as is. Otherwise, it returns True.

        This can be used as a guard to prevent invalid templates created accidentally
        without notice.
        """
        return len(self.variables) > 0

    def generate(self, mapping: Mapping[str, str], allow_extra: bool = True) -> str:
        values = dict(mapping)
        if not self.variables <= set(values.keys()):
            raise CruTemplateError("Missing variables.")
        if not allow_extra and not set(values.keys()) <= self.variables:
            raise CruTemplateError("Extra variables.")
        return self._template.safe_substitute(values)


class TemplateTree:
    def __init__(
        self,
        prefix: str,
        source: str,
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
        self._prefix = prefix
        self._files: list[tuple[CruPath, CruTemplate]] = []
        self._source = source
        self._template_file_suffix = template_file_suffix
        self._load()

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def templates(self) -> list[tuple[CruPath, CruTemplate]]:
        return self._files

    @property
    def source(self) -> str:
        return self._source

    @property
    def template_file_suffix(self) -> str | None:
        return self._template_file_suffix

    @staticmethod
    def _scan_files(root_path: str) -> list[CruPath]:
        result: list[CruPath] = []
        for root, _dirs, files in os.walk(root_path):
            for file in files:
                path = Path(root, file)
                path = path.relative_to(root_path)
                result.append(CruPath(path))
        return result

    def _load(self) -> None:
        files = self._scan_files(self.source)
        for file_path in files:
            template_file = Path(self.source) / file_path
            with open(template_file, "r") as f:
                content = f.read()
            template = CruTemplate(self.prefix, content)
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

    def generate_to(
        self, destination: str, variables: Mapping[str, str], dry_run: bool
    ) -> None:
        for file, template in self.templates:
            des = CruPath(destination) / file
            if self.template_file_suffix is not None and des.name.endswith(
                self.template_file_suffix
            ):
                des = des.parent / (des.name[: -len(self.template_file_suffix)])

            text = template.generate(variables)
            if not dry_run:
                des.parent.mkdir(parents=True, exist_ok=True)
                with open(des, "w") as f:
                    f.write(text)
