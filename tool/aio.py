#!/usr/bin/env python3

import os
import os.path
import pwd
import grp
import sys
import argparse
import typing
import shutil
import urllib.request
from rich.console import Console
from rich.prompt import Prompt, Confirm
from modules.path import *
from modules.template import Template
from modules.nginx import *
from modules.configfile import *

console = Console()


def print_order(number: int, total: int, *, console=console) -> None:
    console.print(f"\[{number}/{total}]", end=" ", style="green")


parser = argparse.ArgumentParser(
    description="Crupest server all-in-one setup script. Have fun play with it!")
subparsers = parser.add_subparsers(dest="action")

setup_parser = subparsers.add_parser(
    "setup", help="Do everything necessary to setup the server.")

download_tools_parser = subparsers.add_parser(
    "download-tools", help="Download some extra tools to manage the server.")

domain_parser = subparsers.add_parser(
    "domain", help="Misc things about domains.")
domain_subparsers = domain_parser.add_subparsers(dest="domain_action")

domain_list_parser = domain_subparsers.add_parser(
    "list", help="List all domains.")

domain_nginx_parser = domain_subparsers.add_parser(
    "nginx", help="Generate nginx config for a domain.")

domain_certbot_parser = domain_subparsers.add_parser(
    "certbot", help="Get some common certbot commands.")

domain_certbot_parser.add_argument(
    "-t", "--test", action="store_true", help="Make the commands for test use.")

clear_parser = subparsers .add_parser(
    "clear", help="Delete existing data so you can make a fresh start.")
clear_parser.add_argument("-D", "--include-data-dir", action="store_true",
                          default=False, help="Also delete the data directory.")

args = parser.parse_args()

console.print("Nice to see you! :waving_hand:", style="cyan")


def check_domain_is_defined() -> str:
    try:
        return get_domain()
    except ValueError as e:
        console.print(
            "We are not able to get the domain. You may want to first run setup command.", style="red")
        console.print_exception(e)
        exit(1)


def download_tools():
    SCRIPTS = [("docker-mailserver setup script", "docker-mailserver-setup.sh",
                "https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh")]
    for index, script in enumerate(SCRIPTS):
        number = index + 1
        total = len(SCRIPTS)
        print_order(number, total)
        name, filename, url = script
        path = os.path.join(tool_dir, filename)
        skip = False
        if os.path.exists(path):
            overwrite = Confirm.ask(
                f"[cyan]{name}[/] already exists, download and overwrite?", default=False)
            if not overwrite:
                skip = True
        else:
            download = Confirm.ask(
                f"Download [cyan]{name}[/] to [magenta]{path}[/]?", default=True)
            if not download:
                skip = True
        if not skip:
            console.print(f"Downloading {name}...")
            urllib.request.urlretrieve(url, path)
            os.chmod(path, 0o755)
            console.print(f"Downloaded {name} to {path}.", style="green")
        else:
            console.print(f"Skipped {name}.", style="yellow")


def generate_nginx_config(domain: str) -> None:
    if not os.path.exists(nginx_config_dir):
        os.mkdir(nginx_config_dir)
        console.print(
            f"Nginx config directory created at [magenta]{nginx_config_dir}[/]", style="green")
    nginx_config_gen(domain, dest=nginx_config_dir)
    console.print("Nginx config generated.", style="green")


if args.action == 'domain':
    domain = check_domain_is_defined()
    domain_action = args.domain_action
    if domain_action == 'list':
        domains = list_domains(domain)
        for domain in domains:
            console.print(domain)
    elif domain_action == 'certbot':
        console.print(
            "Here is some commands you can use to do certbot related work.")
        is_test = args.test
        if is_test:
            console.print(
                "Note you specified --test, so the commands are for test use.", style="yellow")
        console.print(
            f"To create certs for init:\n[code]{certbot_command_gen(domain, 'create', test=is_test)}[/]")
        console.print(
            f"To renew certs previously created:\n[code]{certbot_command_gen(domain, 'renew', test=is_test)}[/]")
    elif domain_action == 'nginx':
        generate_nginx_config(domain)
    exit(0)


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
        console.print("You need to be root to delete data dir.", style="red")
        sys.exit(1)

    to_delete = Confirm.ask(
        "[yellow]Are you sure you want to delete everything? all your data will be lost![/]", default=False)
    if to_delete:
        files_to_delete = []
        for template_name in template_name_list:
            f = os.path.join(project_dir, template_name)
            if os.path.exists(f):
                files_to_delete.append(f)

        delete_data_dir = args.include_data_dir and os.path.exists(data_dir)

        if len(files_to_delete) == 0:
            console.print("Nothing to delete. We are safe!", style="green")
            exit(0)

        console.print("Here are the files to delete:")
        for f in files_to_delete:
            console.print(f, style="magenta")
        if delete_data_dir:
            console.print(data_dir + " (data dir)", style="magenta")

        to_delete = Confirm.ask(
            "[yellow]Are you sure you want to delete them?[/]", default=False)
        if to_delete:
            for f in files_to_delete:
                os.remove(f)
            if delete_data_dir:
                # recursively delete data dir
                shutil.rmtree(data_dir)
        console.print(
            "Your workspace is clean now! However config file is still there! See you!", style="green")
    exit(0)

console.print(
    f"I have found following template files in [magenta]{template_dir}[/]:", style="green")
for filename in template_name_list:
    console.print(f"- [magenta]{filename}.template[/]")


class ConfigVar:
    def __init__(self, name: str, description: str, default_value_generator: typing.Callable[[], str] | str):
        """Create a config var.

        Args:
            name (str): The name of the config var.
            description (str): The description of the config var.
            default_value_generator (typing.Callable([], str) | str): The default value generator of the config var. If it is a string, it will be used as the input prompt and let user input the value.
        """
        self.name = name
        self.description = description
        self.default_value_generator = default_value_generator

    def get_default_value(self):
        if isinstance(self.default_value_generator, str):
            return Prompt.ask(self.default_value_generator, console=console)
        else:
            return self.default_value_generator()


config_var_list: list = [
    ConfigVar("CRUPEST_DOMAIN", "domain name",
              "Please input your domain name:"),
    # ConfigVar("CRUPEST_EMAIL", "admin email address",
    #           "Please input your email address:"),
    ConfigVar("CRUPEST_USER", "your system account username",
              lambda: pwd.getpwuid(os.getuid()).pw_name),
    ConfigVar("CRUPEST_GROUP", "your system account group name",
              lambda: grp.getgrgid(os.getgid()).gr_name),
    ConfigVar("CRUPEST_UID", "your system account uid",
              lambda: str(os.getuid())),
    ConfigVar("CRUPEST_GID", "your system account gid",
              lambda: str(os.getgid())),
    ConfigVar("CRUPEST_HALO_DB_PASSWORD",
              "password for halo h2 database, once used never change it", lambda: os.urandom(8).hex()),
    ConfigVar("CRUPEST_IN_CHINA",
              "set to true if you are in China, some network optimization will be applied", lambda: "false")
]

config_var_name_set = set([config_var.name for config_var in config_var_list])

template_list: list = []
config_var_name_set_in_template = set()
for template_path in os.listdir(template_dir):
    if not template_path.endswith(".template"):
        continue
    template = Template(os.path.join(template_dir, template_path))
    template_list.append(template)
    config_var_name_set_in_template.update(template.var_set)

console.print(
    "I have found following variables needed in templates:", style="green")
for key in config_var_name_set_in_template:
    console.print(key, end=" ", style="magenta")
console.print("")

# check vars
if not config_var_name_set_in_template == config_var_name_set:
    console.print(
        "The variables needed in templates are not same to the explicitly declared ones! There must be something wrong.", style="red")
    console.print("The explicitly declared ones are:")
    for key in config_var_name_set:
        console.print(key, end=" ", style="magenta")
    console.print(
        "\nTry to check template files and edit the var list at the head of this script. Aborted! See you next time!")
    exit(1)


console.print("Now let's check if they are already generated...")

conflict = False

# check if there exists any generated files
for filename in template_name_list:
    if os.path.exists(os.path.join(project_dir, filename)):
        console.print(f"Found [magenta]{filename}[/]")
        conflict = True

if conflict:
    to_overwrite = Confirm.ask(
        "It seems there are some files already generated. Do you want to overwrite them?", console=console, default=False)
    if not to_overwrite:
        console.print(
            "Great! Check the existing files and see you next time!", style="green")
        exit()
else:
    print("No conflict found. Let's go on!\n")

console.print("Check for existing config file...")


# check if there exists a config file
if not config_file_exist:
    config = {}
    console.print(
        "No existing config file found. Don't worry. Let's create one!", style="green")
    for config_var in config_var_list:
        config[config_var.name] = config_var.get_default_value()
    config_content = config_to_str(config)
    # create data dir if not exist
    if not os.path.exists(data_dir):
        os.mkdir(data_dir)
    # write config file
    with open(config_file_path, "w") as f:
        f.write(config_content)
    console.print(
        f"Everything else is auto generated. The config file is written into [magenta]{config_file_path}[/]. You had better keep it well. And here is the content:", style="green")
    print_config(console, config)
    is_ok = Confirm.ask(
        "If you think it's not ok, you can stop here and edit it. Or let's go on?", console=console, default=True)
    if not is_ok:
        console.print(
            "Great! Check the config file and see you next time!", style="green")
        exit()
else:
    console.print(
        "Looks like you have already had a config file. Let's check the content:", style="green")
    with open(config_file_path, "r") as f:
        content = f.read()
    config = parse_config(content)
    print_config(console, config)
    missed_config_vars = []
    for config_var in config_var_list:
        if config_var.name not in config:
            missed_config_vars.append(config_var)

    if len(missed_config_vars) > 0:
        console.print(
            "Oops! It seems you have missed some keys in your config file. Let's add them!", style="green")
        for config_var in missed_config_vars:
            config[config_var.name] = config_var.get_default_value()
        content = config_to_str(config)
        with open(config_file_path, "w") as f:
            f.write(content)
        console.print(
            f"Here is the new config, it has been written out to [magenta]{config_file_path}[/]:")
        print_config(console, config)
    good_enough = Confirm.ask("Is it good enough?",
                              console=console, default=True)
    if not good_enough:
        console.print(
            "Great! Check the config file and see you next time!", style="green")
        exit()

console.print(
    "Finally, everything is ready. Let's generate the files:", style="green")

# generate files
for index, template in enumerate(template_list):
    number = index + 1
    total = len(template_list)
    print_order(number, total)
    console.print(
        f"Generating [magenta]{template.template_name}[/]...")
    content = template.generate(config)
    with open(os.path.join(project_dir, template.template_name), "w") as f:
        f.write(content)

# generate nginx config
if not os.path.exists(nginx_config_dir):
    to_gen_nginx_conf = Confirm.ask("It seems you haven't generate nginx config. Do you want to generate it?",
                                    default=True, console=console)
else:
    to_gen_nginx_conf = Confirm.ask("It seems you have already generated nginx config. Do you want to overwrite it?",
                                    default=False, console=console)
if to_gen_nginx_conf:
    domain = config["CRUPEST_DOMAIN"]
    generate_nginx_config(domain)


if not os.path.exists(os.path.join(data_dir, "code-server")):
    os.mkdir(os.path.join(data_dir, "code-server"))
    console.print(
        "I also create data dir for code-server. Because letting docker create it would result in permission problem.", style="green")
else:
    code_server_stat = os.stat(os.path.join(data_dir, "code-server"))
    if code_server_stat.st_uid == 0 or code_server_stat.st_gid == 0:
        console.print(
            "WARNING: The owner of data dir for code-server is root. This may cause permission problem. You had better change it.", style="yellow")
        to_fix = Confirm.ask(
            "Do you want me to help you fix it?", console=console, default=True)
        if to_fix:
            os.system(
                f"sudo chown -R {os.getuid()}:{os.getgid()} {os.path.join(data_dir, 'code-server')}")

console.print(":beers: All done!", style="green")
to_download_tools = Confirm.ask(
    "By the way, would you like to download some scripts to do some extra setup like creating email user?", console=console, default=True)
if not to_download_tools:
    console.print("Great! See you next time!", style="green")
    exit()

download_tools()