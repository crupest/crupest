from argparse import Namespace

from cru import CruIterator
from cru.template import TemplateTree

from ._base import AppCommandFeatureProvider, AppFeaturePath, OWNER_NAME
from ._config import ConfigManager


class TemplateManager(AppCommandFeatureProvider):
    def __init__(self, prefix: str = OWNER_NAME.upper()):
        super().__init__("template-manager")
        self._prefix = prefix

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

    def list_files(self) -> list[str]:
        return (
            CruIterator(self.template_tree.templates)
            .transform(lambda t: t[0])
            .to_list()
        )

    def print_file_lists(self) -> None:
        for file in self.list_files():
            print(file)

    def generate_files(self) -> None:
        config_manager = self.app.get_feature(ConfigManager)
        self.template_tree.generate_to(
            self.generated_dir.full_path_str, config_manager.config_map
        )

    def get_command_info(self):
        return ("template", "Template Management")

    def setup_arg_parser(self, arg_parser):
        subparsers = arg_parser.add_subparsers(dest="template_command")
        _list_parser = subparsers.add_parser("list", help="List templates.")
        _generate_parser = subparsers.add_parser("generate", help="Generate template.")

    def run_command(self, args: Namespace) -> None:
        if args.template_command == "list":
            self.print_file_lists()
        elif args.template_command == "generate":
            self.generate_files()
