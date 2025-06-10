from argparse import Namespace
from pathlib import Path
import shutil
from typing import NamedTuple
import graphlib

from cru import CruException
from cru.parsing import SimpleLineVarParser
from cru.template import TemplateTree, CruStrWrapperTemplate

from ._base import AppCommandFeatureProvider, AppFeaturePath


class _Config(NamedTuple):
    text: str
    config: dict[str, str]


class _GeneratedConfig(NamedTuple):
    base: _Config
    private: _Config
    merged: _Config


class _PreConfig(NamedTuple):
    base: _Config
    private: _Config
    config: dict[str, str]

    @staticmethod
    def create(base: _Config, private: _Config) -> "_PreConfig":
        return _PreConfig(base, private, {**base.config, **private.config})

    def _merge(self, generated: _Config):
        text = (
            "\n".join(
                [
                    self.private.text.strip(),
                    self.base.text.strip(),
                    generated.text.strip(),
                ]
            )
            + "\n"
        )
        config = {**self.config, **generated.config}
        return _GeneratedConfig(self.base, self.private, _Config(text, config))


class _Template(NamedTuple):
    config: CruStrWrapperTemplate
    config_vars: set[str]
    tree: TemplateTree


class TemplateManager(AppCommandFeatureProvider):
    def __init__(self):
        super().__init__("template-manager")

    def setup(self) -> None:
        self._base_config_file = self.app.services_dir.add_subpath("base-config", False)
        self._private_config_file = self.app.data_dir.add_subpath("config", False)
        self._template_config_file = self.app.services_dir.add_subpath(
            "config.template", False
        )
        self._templates_dir = self.app.services_dir.add_subpath("templates", True)
        self._generated_dir = self.app.services_dir.add_subpath("generated", True)

        self._config_parser = SimpleLineVarParser()

        def _read_pre(app_path: AppFeaturePath) -> _Config:
            text = app_path.read_text()
            config = self._read_config(text)
            return _Config(text, config)

        base = _read_pre(self._base_config_file)
        private = _read_pre(self._private_config_file)
        self._preconfig = _PreConfig.create(base, private)

        self._generated: _GeneratedConfig | None = None

        template_config_text = self._template_config_file.read_text()
        self._template_config = self._read_config(template_config_text)

        self._template = _Template(
            CruStrWrapperTemplate(template_config_text),
            set(self._template_config.keys()),
            TemplateTree(
                lambda text: CruStrWrapperTemplate(text),
                self.templates_dir.full_path_str,
            ),
        )

        self._real_required_vars = (
            self._template.config_vars | self._template.tree.variables
        ) - self._template.config_vars
        lacks = self._real_required_vars - self._preconfig.config.keys()
        self._lack_vars = lacks if len(lacks) > 0 else None

    def _read_config_entry_names(self, text: str) -> set[str]:
        return set(entry.key for entry in self._config_parser.parse(text))

    def _read_config(self, text: str) -> dict[str, str]:
        return {entry.key: entry.value for entry in self._config_parser.parse(text)}

    @property
    def templates_dir(self) -> AppFeaturePath:
        return self._templates_dir

    @property
    def generated_dir(self) -> AppFeaturePath:
        return self._generated_dir

    def get_domain(self) -> str:
        return self._preconfig.config["CRUPEST_DOMAIN"]

    def get_email(self) -> str:
        return self._preconfig.config["CRUPEST_EMAIL"]

    def _generate_template_config(self, config: dict[str, str]) -> dict[str, str]:
        entry_templates = {
            key: CruStrWrapperTemplate(value)
            for key, value in self._template_config.items()
        }
        sorter = graphlib.TopologicalSorter(
            config
            | {key: template.variables for key, template in entry_templates.items()}
        )

        vars: dict[str, str] = config.copy()
        for _ in sorter.static_order():
            del_keys = []
            for key, template in entry_templates.items():
                new = template.generate_partial(vars)
                if not new.has_variables:
                    vars[key] = new.generate({})
                    del_keys.append(key)
                else:
                    entry_templates[key] = new
            for key in del_keys:
                del entry_templates[key]
        assert len(entry_templates) == 0
        return {key: value for key, value in vars.items() if key not in config}

    def _generate_config(self) -> _GeneratedConfig:
        if self._generated is not None:
            return self._generated
        if self._lack_vars is not None:
            raise CruException(f"Required vars are not defined: {self._lack_vars}.")
        config = self._generate_template_config(self._preconfig.config)
        text = self._template.config.generate(self._preconfig.config | config)
        self._generated = self._preconfig._merge(_Config(text, config))
        return self._generated

    def generate(self) -> list[tuple[Path, str]]:
        config = self._generate_config()
        return [
            (Path("config"), config.merged.text),
            *self._template.tree.generate(config.merged.config),
        ]

    def _generate_files(self, dry_run: bool) -> None:
        result = self.generate()
        if not dry_run:
            if self.generated_dir.full_path.exists():
                shutil.rmtree(self.generated_dir.full_path)
            for path, text in result:
                des = self.generated_dir.full_path / path
                des.parent.mkdir(parents=True, exist_ok=True)
                with open(des, "w") as f:
                    f.write(text)

    def get_command_info(self):
        return ("template", "Manage templates.")

    def _print_file_lists(self) -> None:
        print(f"[{self._template.config.variable_count}]", "config")
        for path, template in self._template.tree.templates:
            print(f"[{template.variable_count}]", path.as_posix())

    def _print_vars(self, required: bool) -> None:
        for var in self._template.config.variables:
            print(f"[config] {var}")
        for var in self._template.tree.variables:
            if not (required and var in self._template.config_vars):
                print(f"[template] {var}")

    def _run_check_vars(self) -> None:
        if self._lack_vars is not None:
            print("Lacks:")
            for var in self._lack_vars:
                print(var)

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="template_command", required=True, metavar="TEMPLATE_COMMAND"
        )
        _list_parser = subparsers.add_parser("list", help="list templates")
        vars_parser = subparsers.add_parser(
            "vars", help="list variables used in all templates"
        )
        vars_parser.add_argument(
            "-r",
            "--required",
            help="only list really required one.",
            action="store_true",
        )
        _check_vars_parser = subparsers.add_parser(
            "check-vars",
            help="check if required vars are set",
        )
        generate_parser = subparsers.add_parser("generate", help="generate templates")
        generate_parser.add_argument(
            "--no-dry-run", action="store_true", help="generate and write target files"
        )

    def run_command(self, args: Namespace) -> None:
        if args.template_command == "list":
            self._print_file_lists()
        elif args.template_command == "vars":
            self._print_vars(args.required)
        elif args.template_command == "generate":
            dry_run = not args.no_dry_run
            self._generate_files(dry_run)
            if dry_run:
                print("Dry run successfully.")
                print(
                    f"Will delete dir {self.generated_dir.full_path_str} if it exists."
                )
