from argparse import Namespace
import shutil

from cru import CruIterator
from cru.template import TemplateTree

from ._base import AppCommandFeatureProvider, AppFeaturePath
from ._config import ConfigManager


class TemplateManager(AppCommandFeatureProvider):
    def __init__(self, prefix: str | None = None):
        super().__init__("template-manager")
        self._prefix = prefix or self.app.app_id.upper()

    def setup(self) -> None:
        self._templates_dir = self.app.add_path("templates", True)
        self._generated_dir = self.app.add_path("generated", True)
        self._template_tree: TemplateTree | None = None

    @property
    def prefix(self) -> str:
        return self._prefix

    @property
    def templates_dir(self) -> AppFeaturePath:
        return self._templates_dir

    @property
    def generated_dir(self) -> AppFeaturePath:
        return self._generated_dir

    @property
    def template_tree(self) -> TemplateTree:
        if self._template_tree is None:
            return self.reload()
        return self._template_tree

    def reload(self) -> TemplateTree:
        self._template_tree = TemplateTree(
            self.prefix, self.templates_dir.full_path_str
        )
        return self._template_tree

    def _print_file_lists(self) -> None:
        for file in CruIterator(self.template_tree.templates).transform(lambda t: t[0]):
            print(file.as_posix())

    def _generate_files(self, dry_run: bool) -> None:
        config_manager = self.app.get_feature(ConfigManager)
        if not dry_run:
            shutil.rmtree(self.generated_dir.full_path)
        self.template_tree.generate_to(
            self.generated_dir.full_path_str, config_manager.get_str_dict(), dry_run
        )

    def get_command_info(self):
        return ("template", "Manage templates.")

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(
            dest="template_command", required=True, metavar="TEMPLATE_COMMAND"
        )
        _list_parser = subparsers.add_parser("list", help="list templates")
        _variables_parser = subparsers.add_parser(
            "variables", help="list variables used in all templates"
        )
        generate_parser = subparsers.add_parser("generate", help="generate templates")
        generate_parser.add_argument(
            "--no-dry-run", action="store_true", help="generate and write target files"
        )

    def run_command(self, args: Namespace) -> None:
        if args.template_command == "list":
            self._print_file_lists()
        elif args.template_command == "variables":
            for var in self.template_tree.variables:
                print(var)
        elif args.template_command == "generate":
            dry_run = not args.no_dry_run
            self._generate_files(dry_run)
            if dry_run:
                print("Dry run successfully.")
                print(f"Will delete dir {self.generated_dir.full_path_str}.")
