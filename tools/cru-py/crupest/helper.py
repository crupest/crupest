import os
import os.path
from .path import *


def run_in_dir(dir: str, func: callable):
    old_dir = os.path.abspath(os.getcwd())
    os.chdir(dir)
    func()
    os.chdir(old_dir)


def run_in_project_dir(func: callable):
    run_in_dir(project_dir, func)


def print_order(number: int, total: int, /, console) -> None:
    console.print(f"\[{number}/{total}]", end=" ", style="green")
