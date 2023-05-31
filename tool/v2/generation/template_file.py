import json
from os.path import basename, join

from ..paths import template_dir


class TemplateFile:
    """
    A template file.
    Fields:
        path (str): the path of the template file, NOT from template dir.
        name (str): the name of the template, default to the filename in path.
        text (str): the content text of the template file.
    """

    def __init__(self, path: str, *, name=None):
        """
        Args:
            path (str): the template file relative path **from template dir**.
            name (None | str): the name of the template, default to the filename in path.
        """
        path = join(template_dir, path)
        self.path = path
        self.name = name if name is not None else basename(path)
        with open(path, 'r') as f:
            self.text = f.read()

    def parse(self, /, type="plain"):
        """
        Parse the template file content. Return the parsed result.
        Args:
            type ("plain" | "json"): the type of the template file. Available types: plain, json. Default: plain
        """
        if type == "plain":
            return self.text
        elif type == "json":
            return json.loads(self.text)
        else:
            raise ValueError("Unknown template file type: " + type)
