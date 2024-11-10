from argparse import ArgumentParser, Namespace


from ._base import AppCommandFeatureProvider
from cru.app import ApplicationPath
from cru.template import TemplateTree


class TemplateManager(AppCommandFeatureProvider):
    def __init__(self, prefix: str = "CRUPEST"):
        super().__init__("template-manager")
        self._templates_dir = self.add_app_path("templates", True)
        self._generated_dir = self.add_app_path("generated", True)
        self._template_tree = TemplateTree(
            prefix, self._templates_dir.full_path_str, self._generated_dir.full_path_str
        )

    @property
    def templates_dir(self) -> ApplicationPath:
        return self._templates_dir

    @property
    def generated_dir(self) -> ApplicationPath:
        return self._generated_dir

    def add_arg_parser(self, arg_parser: ArgumentParser) -> None:
        subparsers = arg_parser.add_subparsers(dest="template_command")
        list_parser = subparsers.add_parser("list", help="List templates.")
        generate_parser = subparsers.add_parser("generate", help="Generate template.")

    def run_command(self, args: Namespace) -> None: ...
