from argparse import ArgumentParser, Namespace

from ._base import AppBase, AppFunction


class TemplateManager(AppFunction):
    def __init__(self, app: AppBase):
        self._app = app
        pass

    @property
    def name(self):
        return "template-manager"

    def add_arg_parser(self, arg_parser: ArgumentParser) -> None:
        subparsers = arg_parser.add_subparsers(dest="template_command")
        list_parser = subparsers.add_parser("list", help="List templates")
        generate_parser = subparsers.add_parser("generate", help="Generate template")

    def run_command(self, args: Namespace) -> None: ...
