#!/usr/bin/env python3

# In China? Good for you!

import sys
import re

# read STDIN until EOF
content = sys.stdin.read()

url = re.search(r"url=(.+)", content).group(1)
if url.startswith('"') and url.endswith('"'):
    url = url[1:-1]

if url.startswith("https://github.com"): # yah, it's github!
    content = re.sub(r"\$\{\s*url\s*\}|\$url", url, content)
    content = content.replace("https://raw.githubusercontent.com", "https://gh.api.99988866.xyz/https://raw.githubusercontent.com")
    content = re.sub(r'https://github\.com/(.+)/(.+)/releases/download', lambda match: f'https://gh.api.99988866.xyz/{match.group(0)}', content)

# now print the result
print(content)
