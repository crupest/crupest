import os.path
import re

_template_filename_suffix = ".template"
_template_var_regex = r"\$([-_a-zA-Z0-9]+)"
_template_var_brace_regex = r"\$\{\s*([-_a-zA-Z0-9]+?)\s*\}"


class Template2:

    @staticmethod
    def from_file(template_path: str) -> "Template2":
        if not template_path.endswith(_template_filename_suffix):
            raise Exception(
                "Template file must have a name ending with .template.")
        template_name = os.path.basename(
            template_path)[:-len(_template_filename_suffix)]
        with open(template_path, "r") as f:
            template = f.read()
        return Template2(template_name, template, template_path=template_path)

    def __init__(self, template_name: str, template: str, *, template_path: str | None = None) -> None:
        self.template_name = template_name
        self.template = template
        self.template_path = template_path
        self.var_set = set()
        for match in re.finditer(_template_var_regex, self.template):
            self.var_set.add(match.group(1))
        for match in re.finditer(_template_var_brace_regex, self.template):
            self.var_set.add(match.group(1))

    def partial_render(self, vars: dict[str, str]) -> "Template2":
        t = self.render(vars)
        return Template2(self.template_name, t, template_path=self.template_path)

    def render(self, vars: dict[str, str]) -> str:
        for name in vars.keys():
            if name not in self.var_set:
                raise ValueError(f"Invalid var name {name}.")

        text = self.template
        for name, value in vars.items():
            text = text.replace("$" + name, value)
            text = re.sub(r"\$\{\s*" + name + r"\s*\}", value, text)
        return text
