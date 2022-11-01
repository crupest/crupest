#!/usr/bin/env python3

import os
import os.path
import re
import pwd
import grp
import sys
import argparse

parser = argparse.ArgumentParser(
    description="Crupest server all-in-one setup script. Have fun play with it!")
parser.add_argument("action", choices=["setup", "download-tools", "clear"], default="setup", nargs="?",
                    help="choose what to do, 'setup' for everything needed to run server, 'download-tools' for downloading other needed tools for setup, 'clear' for deleting everything so you can restart.")
parser.add_argument("--include-data-dir", action="store_true",
                    default=False, help="include data dir when clear")
args = parser.parse_args()

if args.action != 'clear' and args.include_data_dir:
    print("Warning: --include-data-dir is only used when clear, ignored.")

print("Nice to see you!\n")

# get script dir in relative path
script_dir = os.path.dirname(__file__)
project_dir = os.path.normpath(os.path.join(script_dir, "../"))
template_dir = os.path.join(project_dir, "template")
data_dir = os.path.join(project_dir, "data")
tool_dir = os.path.join(project_dir, "tool")


def download_tools():
    SCRIPTS = [("docker-mailserver setup script", "docker-mailserver-setup.sh",
                "https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh")]
    for script in SCRIPTS:
        name, filename, url = script
        path = os.path.join(tool_dir, filename)
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


if args.action == 'download-tools':
    download_tools()
    exit(0)

print("First let's check all the templates...")

# get all filenames ending with .template
template_name_list = [os.path.basename(f)[:-len('.template')] for f in os.listdir(
    template_dir) if f.endswith(".template")]

# if action is 'clean'
if args.action == "clear":
    # check root if we have to delete data dir
    if args.include_data_dir and os.path.exists(data_dir) and os.geteuid() != 0:
        print("You need to be root to delete data dir.")
        sys.exit(1)

    print("Are you sure you want to delete everything? all your data will be lost! (y/N)", end=" ")
    if input() == "y":
        files_to_delete = []
        for template_name in template_name_list:
            f = os.path.join(project_dir, template_name)
            if os.path.exists(f):
                files_to_delete.append(f)

        delete_data_dir = args.include_data_dir and os.path.exists(data_dir)

        if len(files_to_delete) == 0:
            print("Nothing to delete. We are safe!")
            exit(0)

        print("Here are the files to delete:")
        for f in files_to_delete:
            print(f)
        if delete_data_dir:
            print(data_dir + " (data dir)")

        print("Are you sure you want to delete them? (y/N)", end=" ")
        if input() == "y":
            for f in files_to_delete:
                os.remove(f)
            if delete_data_dir:
                os.rmdir(data_dir)
        print("Your workspace is clean now! However config file is still there! See you!")
    exit(0)

print("I have found following template files:")
for filename in template_name_list:
    print(filename)
print("")

required_config_key_list = [
    ("CRUPEST_DOMAIN", lambda: input("Please input your domain name:")),
    ("CRUPEST_EMAIL", lambda: input("Please input your email address:")),
    ("CRUPEST_USER", lambda: pwd.getpwuid(os.getuid()).pw_name),
    ("CRUPEST_GROUP", lambda: grp.getgrgid(os.getgid()).gr_name),
    ("CRUPEST_UID", lambda: str(os.getuid())),
    ("CRUPEST_GID", lambda: str(os.getgid())),
    ("CRUPEST_HALO_DB_PASSWORD", lambda: os.urandom(8).hex()),
    ("CRUPEST_IN_CHINA", lambda: "false")
]

required_config_value_generator_map = dict(required_config_key_list)

required_config_keys = set([key for key, _ in required_config_key_list])

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
for filename in template_name_list:
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

config_path = os.path.join(data_dir, "config")


def parse_config(str):
    config = {}
    for line_number, line in enumerate(str.splitlines()):
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
    return config


def config_to_str(config):
    return "\n".join([f"{key}={value}" for key, value in config.items()])


def print_config(config):
    print(config_to_str(config))


# check if there exists a config file
if not os.path.exists(config_path):
    config = {}
    print("No existing config file found. Don't worry. Let's create one!")
    for key, default_generator in required_config_key_list:
        if default_generator is not None:
            config[key] = default_generator()
    config_content = config_to_str(config)
    # create data dir if not exist
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
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
        content = f.read()
    config = parse_config(content)
    print_config(config)
    missed_keys = []
    for required_key in required_config_keys:
        if required_key not in config:
            missed_keys.append(required_key)

    if len(missed_keys) > 0:
        print(
            "Oops! It seems you have missed some keys in your config file. Let's add them!")
        for key in missed_keys:
            config[key] = required_config_value_generator_map[key]()
        content = config_to_str(config)
        with open(config_path, "w") as f:
            f.write(content)
        print("Here is the new config, it has been written out:")
        print(content)
    print("Is it good enough? (Y/n)")
    if input() == "n":
        print("Great! Check the config file and see you next time!")
        exit()

print("Finally, everything is ready. Let's generate the files:")

# generate files
for filename in template_name_list:
    print(f"Generating {filename}...")
    with open(os.path.join(template_dir, filename + ".template"), "r") as f:
        content = f.read()
        content = sub_regex.sub(lambda m: config[m.group(1)], content)
        with open(os.path.join(project_dir, filename), "w") as f:
            f.write(content)

print()

if not os.path.exists(os.path.join(data_dir, "code-server")):
    os.mkdir(os.path.join(data_dir, "code-server"))
    print("I also create data dir for code-server. Because letting docker create it would result in permission problem.")
else:
    code_server_stat = os.stat(os.path.join(data_dir, "code-server"))
    if code_server_stat.st_uid == 0 or code_server_stat.st_gid == 0:
        print("WARNING: The owner of data dir for code-server is root. This may cause permission problem. You had better change it. Want me help you? (Y/n)")
        if input() != "n":
            os.system(
                f"sudo chown -R {os.getuid()}:{os.getgid()} {os.path.join(data_dir, 'code-server')}")
print()

print("🍻All done! By the way, would you like to download some scripts to do some extra setup like creating email user? (Y/n)")
if input() == "n":
    print("Great! See you next time!")
    exit()

download_tools()
