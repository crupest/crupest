import os.path
import re


class Template:
    def __init__(self, template_path: str, var_prefix: str = "CRUPEST"):
        if len(var_prefix) != 0 and re.fullmatch(r"^[a-zA-Z_][a-zA-Z0-9_]*$", var_prefix) is None:
            raise ValueError("Invalid var prefix.")
        self.template_path = template_path
        self.template_name = os.path.basename(
            template_path)[:-len(".template")]
        with open(template_path, "r") as f:
            self.template = f.read()
        self.var_prefix = var_prefix
        self.__var_regex = re.compile(r"\$(" + var_prefix + r"_[a-zA-Z0-9_]+)")
        self.__var_brace_regex = re.compile(
            r"\$\{\s*(" + var_prefix + r"_[a-zA-Z0-9_]+)\s*\}")
        var_set = set()
        for match in self.__var_regex.finditer(self.template):
            var_set.add(match.group(1))
        for match in self.__var_brace_regex.finditer(self.template):
            var_set.add(match.group(1))
        self.var_set = var_set

    def generate(self, config: dict) -> str:
        result = self.template
        for var in self.var_set:
            if var not in config:
                raise ValueError(f"Missing config var {var}.")
            result = result.replace("$" + var, config[var])
            result = re.sub(r"\$\{\s*" + var + r"\s*\}", config[var], result)
        return result
