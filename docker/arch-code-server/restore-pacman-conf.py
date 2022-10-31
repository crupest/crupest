#!/usr/bin/env python3

# Fxxk damn shit bash script and linux tools. They just don't work well with text processing, which took me a long time to discover the stupid fact.

import os
import os.path
import sys
import urllib.request
from http.client import HTTPResponse

PACMAN_NO_EXTRACT_URL = 'https://gitlab.archlinux.org/archlinux/archlinux-docker/-/raw/master/pacman-conf.d-noextract.conf'

# check if this is in docker by CRUPEST_IN_DOCKER env
if not os.environ.get('CRUPEST_IN_DOCKER'):
    print("Not in docker, exiting!", file=sys.stderr)
    exit(1)

# check if I'm root
if os.geteuid() != 0:
    print("Not root, exiting!", file=sys.stderr)
    exit(1)

# check if pacman.conf exists
if not os.path.exists('/etc/pacman.conf'):
    print("/etc/pacman.conf does not exist, are you running this in Arch Linux? Exiting!", file=sys.stderr)
    exit(2)

# Download pacman-no-extract file from url
res: HTTPResponse = urllib.request.urlopen(PACMAN_NO_EXTRACT_URL)
if res.status != 200:
    print(
        f"Failed to download pacman-no-extract file from url: {PACMAN_NO_EXTRACT_URL}, exiting!", file=sys.stderr)
    exit(3)

# Read the content of pacman-no-extract file
pacman_no_extract_content = res.read().decode('utf-8')

# Read the content of pacman.conf
with open('/etc/pacman.conf', 'r') as f:
    pacman_conf_content = f.read()
    # remove pacman_no_extract_content from pacman_conf_content
    pacman_conf_content = pacman_conf_content.replace(
        pacman_no_extract_content, '')

# Write the content of pacman.conf
with open('/etc/pacman.conf', 'w') as f:
    f.write(pacman_conf_content)
