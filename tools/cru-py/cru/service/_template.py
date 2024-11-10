from argparse import ArgumentParser, Namespace

from cru.template import TemplateTree

from ._base import AppCommandFeatureProvider, AppFeaturePath


class TemplateManager(AppCommandFeatureProvider):
    def __init__(self, prefix: str = "CRUPEST"):
        super().__init__("template-manager")
        self._templates_dir = self.app.add_path("templates", True)
        self._generated_dir = self.app.add_path("generated", True)
        self._template_tree = TemplateTree(
            prefix, self._templates_dir.full_path_str, self._generated_dir.full_path_str
        )

    @property
    def templates_dir(self) -> AppFeaturePath:
        return self._templates_dir

    @property
    def generated_dir(self) -> AppFeaturePath:
        return self._generated_dir

    def add_arg_parser(self, arg_parser: ArgumentParser) -> None:
        subparsers = arg_parser.add_subparsers(dest="template_command")
        list_parser = subparsers.add_parser("list", help="List templates.")
        generate_parser = subparsers.add_parser("generate", help="Generate template.")

    def run_command(self, args: Namespace) -> None: ...
