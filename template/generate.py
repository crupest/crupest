#!/usr/bin/env python3

import os
import os.path
import re
import pwd
import grp
import sys

required_config_keys = set(["CRUPEST_DOMAIN", "CRUPEST_USER", "CRUPEST_GROUP", "CRUPEST_UID",
                            "CRUPEST_GID", "CRUPEST_HALO_DB_PASSWORD", "CRUPEST_IN_CHINA"])

print("It's happy to see you!\n")

# get script dir in relative path
script_dir = os.path.dirname(__file__)
template_dir = script_dir
project_dir = os.path.normpath(os.path.join(script_dir, "../"))

print("First let's check all the templates...")

# get all filenames ending with .template
filenames = [os.path.basename(f)[:-len('.template')] for f in os.listdir(
    template_dir) if f.endswith(".template")]

print("I have found following template files:")
for filename in filenames:
    print(filename)

print("")

# if command is 'clean'
if len(sys.argv) > 1 and sys.argv[1] == "clean":
    print("Are you sure you want to delete all generated files? (y/N)")
    if input() == "y":
        print("Deleting all generated files...")
        for filename in filenames:
            os.remove(os.path.join(project_dir, filename))
        print("Your workspace is clean now! However config file is still there! See you!")
    exit(0)


sub_regex = re.compile(r"\{\{\s*([a-zA-Z0-9_]+?)\s*\}\}")
var_set = set()
for template in os.listdir(template_dir):
    if not template.endswith(".template"):
        continue
    with open(os.path.join(template_dir, template), "r") as f:
        content = f.read()
        match_list = sub_regex.finditer(content)
        for match in match_list:
            var_set.add(match.group(1))

print("I have found following variables needed in templates:")
for var in var_set:
    print(var, end=" ")
print("")

# check vars
if not var_set == required_config_keys:
    print("The variables needed in templates are not same to the explicitly declared ones! There must be something wrong.")
    print("The explicitly declared ones are:")
    for var in required_config_keys:
        print(var, end=" ")
    print("Try to check template files and edit the var list at the head of this script. Aborted! See you next time!")
    exit(1)


print("Now let's check if they are already generated...")

conflict = False

# check if there exists any generated files
for filename in filenames:
    if os.path.exists(os.path.join(project_dir, filename)):
        print(f"Found {filename}")
        conflict = True

if conflict:
    print("It seems there are some files already generated. Do you want to overwrite them? (y/N)")
    if input() != "y":
        print("Great! Check the existing files and see you next time!")
        exit()
else:
    print("No conflict found. Let's go on!\n")

print("Check for existing config file...")

config_path = os.path.join(project_dir, "data/config")

# check if there exists a config file
if not os.path.exists(config_path):
    config = {}
    print("No existing config file found. Don't worry. Let's create one! Just tell me your domain name:")
    config["CRUPEST_DOMAIN"] = input()
    config["CRUPEST_USER"] = pwd.getpwuid(os.getuid()).pw_name
    config["CRUPEST_GROUP"] = grp.getgrgid(os.getgid()).gr_name
    config["CRUPEST_UID"] = str(os.getuid())
    config["CRUPEST_GID"] = str(os.getgid())
    config["CRUPEST_HALO_DB_PASSWORD"] = os.urandom(8).hex()
    config["CRUPEST_IN_CHINA"] = "false"
    config_content = ""
    for key in config:
        config_content += f"{key}={config[key]}\n"
    # create data dir if not exist
    if not os.path.exists(os.path.join(project_dir, "data")):
        os.mkdir(os.path.join(project_dir, "data"))
    # write config file
    with open(config_path, "w") as f:
        f.write(config_content)
    print(
        f"Everything else is auto generated. The config file is written into {config_path}. You had better keep it well. And here is the content:")
    print(config_content)
    print("If you think it's not ok, you can stop here and edit it. Or let's go on? (Y/n)")
    if input() == "n":
        print("Great! Check the config file and see you next time!")
        exit()
else:
    print("Looks like you have already had a config file. Let's check the content:")
    with open(config_path, "r") as f:
        print(f.read())
    print("Is it good enough? (Y/n)")
    if input() == "n":
        print("Great! Check the config file and see you next time!")
        exit()

# Parse config file
with open(config_path, "r") as f:
    config = {}
    # read line with line number
    for line_number, line in enumerate(f.readlines()):
        # check if it's a comment
        if line.startswith("#"):
            continue
        # check if there is a '='
        if line.find("=") == -1:
            print(
                f"Invalid config file. Please check line {line_number + 1}. There is even no '='! Aborted!")
        # split at first '='
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        config[key] = value


# check if all required keys are in config
for key in required_config_keys:
    if key not in config:
        print(
            f"Invalid config file. Please check if {key} is in the config file. Aborted!")
        exit()

print("Finally, everything is ready. Let's generate the files:")

# generate files
for filename in filenames:
    print(f"Generating {filename}...")
    with open(os.path.join(template_dir, filename + ".template"), "r") as f:
        content = f.read()
        content = sub_regex.sub(lambda m: config[m.group(1)], content)
        with open(os.path.join(project_dir, filename), "w") as f:
            f.write(content)

print("\n🍻All done! See you next time!\nBy the way, you may wish to run tool/download.py to download some scripts to do some extra setup like creating email user.")
