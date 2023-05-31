from .path import *
from rich.prompt import Prompt, Confirm
from urllib.request import urlretrieve
import subprocess
from datetime import datetime


def backup_restore(http_url_or_path, /, console):
    url = http_url_or_path
    if len(url) == 0:
        raise Exception("You specify an empty url. Abort.")
    if url.startswith("http://") or url.startswith("https://"):
        download_path = os.path.join(tmp_dir, "data.tar.xz")
        if os.path.exists(download_path):
            to_remove = Confirm.ask(
                f"I want to download to [cyan]{download_path}[/]. However, there is a file already there. Do you want to remove it first", default=False, console=console)
            if to_remove:
                os.remove(download_path)
            else:
                raise Exception(
                    "Aborted! Please check the file and try again.")
        urlretrieve(url, download_path)
        url = download_path
    subprocess.run(["sudo", "tar", "-xJf", url, "-C", project_dir], check=True)


def backup_backup(path, /, console):
    ensure_backup_dir()
    now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if path is None:
        path = Prompt.ask(
            "You don't specify the path to backup to. Please specify one. http and https are NOT supported", console=console, default=os.path.join(backup_dir, now + ".tar.xz"))
    if len(path) == 0:
        raise Exception("You specify an empty path. Abort!")
    if os.path.exists(path):
        raise Exception(
            "A file is already there. Please remove it first. Abort!")
    subprocess.run(
        ["sudo", "tar", "-cJf", path, "data", "-C", project_dir],
        check=True
    )
