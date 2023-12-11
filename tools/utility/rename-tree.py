#!/usr/bin/env python3

import argparse
import os
import os.path
import re

parser = argparse.ArgumentParser(
                    prog='rename-tree',
                    description='Recursively rename directories and files')

parser.add_argument('old')
parser.add_argument('new')
parser.add_argument('dirs', nargs="+")

args = parser.parse_args()

old_regex = re.compile(args.old)
new = args.new

def rename(path, isdir):
    dirname = os.path.dirname(path)
    filename = os.path.basename(path)
    new_filename = re.sub(old_regex, new, filename)
    dir_str = "/" if isdir else ""
    if new_filename != filename:
        os.rename(path, os.path.join(dirname, new_filename))
        print(f"{path}{dir_str} -> {new_filename}{dir_str}")

for i, d in enumerate(args.dirs):
    print(f"[{i + 1}/{len(args.dirs)}] Run for {d}:")
    for dirpath, dirnames, filenames in os.walk(d, topdown=False):
        for filename in filenames:
            rename(os.path.join(dirpath, filename), False)
        rename(dirpath, True)

print("Done!")
