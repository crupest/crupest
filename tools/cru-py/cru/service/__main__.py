import argparse


arg_parser = argparse.ArgumentParser(description="Service management")
command_subparser = arg_parser.add_subparsers(dest="command")

template_parser = command_subparser.add_parser("template", help="Template management")
template_subparser = template_parser.add_subparsers(dest="template_command")

template_subparser.add_parser('list', description="List templates")
template_subparser.add_parser('generate')
