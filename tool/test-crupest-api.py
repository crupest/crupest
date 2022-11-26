#!/usr/bin/env python3

import json
import time
from os.path import *
from urllib.request import urlopen
from http.client import *
from rich.console import Console
from modules.path import *

console = console = Console()


def do_the_test():
    res: HTTPResponse = urlopen("http://localhost:5188/api/todos")
    body = res.read()

    if res.status != 200:
        raise Exception("Status code is not 200.")
    result = json.loads(body)
    if not isinstance(result,  list):
        raise Exception("Result is not an array.")
    if len(result) == 0:
        raise Exception("Result is an empty array.")
    if not isinstance(result[0], dict):
        raise Exception("Result[0] is not an object.")
    if not isinstance(result[0].get("title"), str):
        raise Exception("Result[0].title is not a string.")
    if not isinstance(result[0].get("status"), str):
        raise Exception("Result[0].status is not a string.")


try:
    do_the_test()
    console.print("Test passed!", style="green")
    exit(0)
except Exception as e:
    console.print(e)
    console.print("Test failed!", style="red")
