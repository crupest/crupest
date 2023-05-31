import sys
from os.path import *
from urllib.request import *
from rich.prompt import Confirm
from .path import *
from .helper import print_order


TOOLS = [("docker-mailserver setup script", "docker-mailserver-setup.sh",
          "https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh")]


def download_tools(console):
    # if we are not linux, we prompt the user
    if sys.platform != "linux":
        console.print(
            "You are not running this script on linux. The tools will not work.", style="yellow")
        if not Confirm.ask("Do you want to continue?", default=False, console=console):
            return

    for index, script in enumerate(TOOLS):
        number = index + 1
        total = len(TOOLS)
        print_order(number, total, console)
        name, filename, url = script
        # if url is callable, call it
        if callable(url):
            url = url()
        path = join(tool_dir, filename)
        skip = False
        if exists(path):
            overwrite = Confirm.ask(
                f"[cyan]{name}[/] already exists, download and overwrite?", default=False, console=console)
            if not overwrite:
                skip = True
        else:
            download = Confirm.ask(
                f"Download [cyan]{name}[/] to [magenta]{path}[/]?", default=True, console=console)
            if not download:
                skip = True
        if not skip:
            console.print(f"Downloading {name}...")
            urlretrieve(url, path)
            os.chmod(path, 0o755)
            console.print(f"Downloaded {name} to {path}.", style="green")
        else:
            console.print(f"Skipped {name}.", style="yellow")
