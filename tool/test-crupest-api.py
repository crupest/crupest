#!/usr/bin/env python3

import subprocess
import os
import sys
from os.path import *
import signal
from modules.path import *
import time
from rich.console import Console
from urllib.request import urlopen
from http.client import *
import json

console = console = Console()

ensure_log_dir()

dotnet_project = join(project_dir, "docker", "crupest-api", "CrupestApi")
dotnet_log_path = abspath(join(log_dir, "crupest-api-log"))
dotnet_config_path = abspath(join(project_dir, "crupest-api-config.json"))

os.environ["CRUPEST_API_CONFIG_FILE"] = dotnet_log_path
os.environ["CRUPEST_API_LOG_FILE"] = dotnet_config_path

popen = subprocess.Popen(
    ["dotnet", "run", "--project", dotnet_project, "--launch-profile", "dev"]
)

console.print("Sleep for 3s to wait for server startup.")
time.sleep(3)


def do_the_test():
    res: HTTPResponse = urlopen("http://localhost:5188/api/todos")
    console.print(res)
    body = res.read()
    console.print(body)

    if res.status != 200:
        raise Exception("Status code is not 200.")
    result = json.load(body)
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


for i in range(0, 2):
    console.print(f"Test begin with attempt {i + 1}", style="cyan")
    try:
        do_the_test()
        console.print("Test passed.", style="green")
        popen.send_signal(signal.SIGTERM)
        popen.wait()
        exit(0)
    except Exception as e:
        console.print(e)
        console.print(
            "Test failed. Try again after sleep for 1s.", style="red")
        time.sleep(1)

try:
    console.print(
        f"Test begin with attempt {i + 2}, also the final one.", style="cyan")
    do_the_test()
    console.print("Test passed.", style="green")
    popen.send_signal(signal.SIGTERM)
    popen.wait()
    exit(0)
except Exception as e:
    console.print(e)
    console.print("Final test failed.", style="red")
    exit(1)
