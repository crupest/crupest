from .tui import console

good_style = "green"
warning_style = "yellow"
error_style = "red bold"
file_name_style = "cyan bold"
var_style = "magenta bold"
value_style = "cyan bold"
bye_style = "cyan"


def print_with_indent(value: str, style: str,  /, indent: int = 0, *, indent_width: int = 2, end='\n'):
    console.print(
        f'{" " * indent * indent_width}[{style}]{value}[/]', end=end)


def print_var_value(name: str, value: str, /, indent: int = 0, *, indent_width: int = 2, end='\n'):
    console.print(
        f'{" " * indent * indent_width}[{var_style}]{name}[/] = [{value_style}]{value}[/]', end=end)
