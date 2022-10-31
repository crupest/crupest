#!/usr/bin/env python3

import os.path

SCRIPTS = [("docker-mailserver setup script", "docker-mailserver-setup.sh",
            "https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh")]

this_script_dir = os.path.dirname(os.path.relpath(__file__))

for script in SCRIPTS:
    name, filename, url = script
    path = os.path.join(this_script_dir, filename)
    skip = False
    if os.path.exists(path):
        print(f"{name} already exists, download and overwrite? (y/N)", end=" ")
        if input() != "y":
            skip = True
    else:
        print(f"Download {name} to {path}? (Y/n)", end=" ")
        if input() == "n":
            skip = True
    if not skip:
        print(f"Downloading {name}...")
        os.system(f"curl -s {url} > {path} && chmod +x {path}")
        print(f"Downloaded {name} to {path}.")
    else:
        print(f"Skipped {name}.")
