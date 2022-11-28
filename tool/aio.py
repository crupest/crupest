#!/usr/bin/env python3

try:
    import rich
    import jsonschema
    import cryptography
except ImportError:
    print("Some necessary modules can't be imported. Please run `pip install -r requirements.txt` to install them.")
    exit(1)

import datetime
import os
from os.path import *
import argparse
import shutil
import subprocess
from rich.console import Console
from rich.prompt import Confirm
from modules.install_docker import *
from modules.path import *
from modules.template import Template
from modules.nginx import *
from modules.config import *
from modules.check import *
from modules.backup import *
from modules.download_tools import *
from modules.helper import *
from modules.test import *
from modules.dns import *

console = Console()

parser = argparse.ArgumentParser(
    description="Crupest server all-in-one setup script. Have fun play with it!")
parser.add_argument("--no-hello", action="store_true",
                    default=False, help="Do not print hello message.")
parser.add_argument("--no-bye-bye", action="store_true",
                    default=False, help="Do not print bye-bye message.")

parser.add_argument("--no-check-python-version", action="store_true",
                    default=False, help="Do not check python version.")
parser.add_argument("--no-check-system", action="store_true",
                    default=False, help="Do not check system type.")
parser.add_argument("-y", "--yes", action="store_true",
                    default=False, help="Yes to all confirmation.")

subparsers = parser.add_subparsers(dest="action")

setup_parser = subparsers.add_parser(
    "setup", help="Do everything necessary to setup the server.")

print_path_parser = subparsers.add_parser(
    "print-path", help="Print the paths of all related files and dirs.")

download_tools_parser = subparsers.add_parser(
    "download-tools", help="Download some extra tools to manage the server.")

list_domain_parser = subparsers.add_parser(
    "list-domain", help="Misc things about domains.")

nginx_parser = subparsers.add_parser(
    "nginx", help="Generate nginx config.")

certbot_parser = subparsers.add_parser(
    "certbot", help="Get some common certbot commands.")

certbot_command_group = certbot_parser.add_mutually_exclusive_group()

certbot_command_group.add_argument(
    "-C", "--create", action="store_true", default=False, help="Only print the command for 'create' action.")
certbot_command_group.add_argument(
    "-E", "--expand", action="store_true", default=False, help="Only print the command for 'expand' action.")
certbot_command_group.add_argument(
    "-R", "--renew", action="store_true", default=False, help="Only print the command for 'renew' action.")

certbot_parser.add_argument(
    "-t", "--test", action="store_true", default=False, help="Make the commands for test use.")

clear_parser = subparsers.add_parser(
    "clear", help="Delete existing data so you can make a fresh start.")
clear_parser.add_argument("-D", "--include-data-dir", action="store_true",
                          default=False, help="Also delete the data directory.")

install_docker_parser = subparsers.add_parser(
    "install-docker", help="Install docker and docker-compose.")

backup_parser = subparsers.add_parser(
    "backup", help="Backup related things."
)

backup_subparsers = backup_parser.add_subparsers(dest="backup_action")
backup_restore_parser = backup_subparsers.add_parser(
    "restore", help="Restore data from url.")
backup_restore_parser.add_argument(
    "restore_url", help="Restore archive url. Can be local path or http/https.")
backup_backup_parser = backup_subparsers.add_parser(
    "backup", help="Backup data to specified path.")
backup_backup_parser.add_argument(
    "backup_path", nargs="?", help="Backup path. Can be empty for a timestamp as name. Must be local path.")

docker_parser = subparsers.add_parser("docker", help="Docker related things.")
docker_subparsers = docker_parser.add_subparsers(dest="docker_action")
docker_subparsers.add_parser("up", help="Run docker compose up -d.")
docker_subparsers.add_parser("down", help="Run docker compose down.")
docker_subparsers.add_parser(
    "prune", help="Run docker system prune -a -f.")

test_parser = subparsers.add_parser("test", help="Test things.")
test_parser.add_argument(
    "test_action", help="Test action.", choices=["crupest-api"])

dns_parser = subparsers.add_parser("dns", help="Generate dns zone.")

dns_parser.add_argument("-i", "--ip", help="IP address of the server.")

git_update_parser = subparsers.add_parser(
    "git-update", help="Update git submodules.")

up_parser = subparsers.add_parser(
    "up", help="Do something necessary and then docker compose up.")

args = parser.parse_args()

if args.yes:
    old_ask = Confirm.ask

    def new_ask(prompt, *args, console=console, default=None, **kwargs):
        default_text = ""
        if default is not None:
            default_text = "(y)" if default else "(n)"
        text = f"[prompt]{prompt}[/] [prompt.choices]\[y/n][/] [prompt.default]{default_text}[/]"
        console.print(text)
        return True

    Confirm.ask = new_ask

if (args.action == "certbot" and (args.create or args.renew or args.expand)) or (args.action == "dns" and args.ip is not None):
    args.no_hello = True
    args.no_bye_bye = True


if not args.no_check_python_version:
    if check_python_version():
        console.print("This script works well on python 3.10. Otherwise you may encounter some problems. But I would like to improve some rational compatibility.", style="yellow")

if not args.no_check_system:
    if not check_ubuntu():
        console.print("This script works well on Ubuntu 22.04. Otherwise you may encounter some problems. But I would like to improve some rational compatibility.", style="yellow")


if not args.no_hello:
    console.print("Nice to see you! :waving_hand:", style="cyan")


def check_domain_is_defined():
    try:
        return get_domain()
    except Exception as e:
        console.print(e.args[0], style="red")


def data_dir_check(domain):
    if not exists(data_dir):
        console.print(
            "Looks like you haven't generated data dir. I'll create it for you.", style="green")
        os.mkdir(data_dir)
    elif not isdir(data_dir):
        console.print(
            "ERROR: data dir is not a dir! Everything will be broken! Please delete it manually", style="red")

    if isdir(data_dir):
        if not exists(join(data_dir, "certbot")):
            print_create_cert_message(domain, console)
        else:
            to_check = Confirm.ask(
                "I want to check your ssl certs, but I need to sudo. Do you want me check", console=console, default=False)
            if to_check:
                check_ssl_cert(domain, console)

    if not exists(join(data_dir, "code-server")):
        os.mkdir(join(data_dir, "code-server"))
        console.print(
            "I also create data dir for code-server. Because letting docker create it would result in permission problem.", style="green")
    else:
        code_server_stat = os.stat(
            join(data_dir, "code-server"))
        if code_server_stat.st_uid == 0 or code_server_stat.st_gid == 0:
            console.print(
                "WARNING: The owner of data dir for code-server is root. This may cause permission problem. You had better change it.", style="yellow")
            to_fix = Confirm.ask(
                "Do you want me to help you fix it?", console=console, default=True)
            if to_fix:
                subprocess.run(
                    ["sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}", join(data_dir, 'code-server')], check=True)


def setup(template_name_list):
    template_list: list = []
    config_var_name_set_in_template = set()
    for template_path in os.listdir(template_dir):
        if not template_path.endswith(".template"):
            continue
        template = Template(join(
            template_dir, template_path))
        template_list.append(template)
        config_var_name_set_in_template.update(template.var_set)

    console.print(
        "I have found following variables needed in templates:", style="green")
    for key in config_var_name_set_in_template:
        console.print(key, style="magenta")

    # check vars
    check_success, more, less = check_config_var_set(
        config_var_name_set_in_template)
    if len(more) != 0:
        console.print("There are more variables in templates than in config file:",
                      style="red")
        for key in more:
            console.print(key, style="magenta")
    if len(less) != 0:
        console.print("Following config vars are not used:",
                      style="yellow")
        for key in less:
            console.print(key, style="magenta")

    if not check_success:
        console.print(
            "Please check you config vars and make sure the needed ones are defined!", style="red")
    else:
        console.print(
            "Now let's check if they are already generated...")

        conflict = False

        # check if there exists any generated files
        for filename in template_name_list:
            if exists(join(project_dir, filename)):
                console.print(f"Found [magenta]{filename}[/]")
                conflict = True

        to_gen = True
        if conflict:
            to_overwrite = Confirm.ask(
                "It seems there are some files already generated. Do you want to overwrite them?", console=console, default=False)
            if not to_overwrite:
                to_gen = False
                console.print(
                    "Great! Check the existing files and see you next time!", style="green")
        else:
            print("No conflict found. Let's go on!\n")

        if to_gen:
            console.print("Check for existing config file...")

            # check if there exists a config file
            if not config_file_exists():
                config = {}
                console.print(
                    "No existing config file found. Don't worry. Let's create one!", style="green")
                for config_var in config_var_list:
                    config[config_var.name] = config_var.get_default_value()
                config_content = config_to_str(config)
                # create data dir if not exist
                if not exists(data_dir):
                    os.mkdir(data_dir)
                # write config file
                with open(config_file_path, "w") as f:
                    f.write(config_content)
                console.print(
                    f"Everything else is auto generated. The config file is written into [magenta]{config_file_path}[/]. You had better keep it safe. And here is the content:", style="green")
                print_config(console, config)
                is_ok = Confirm.ask(
                    "If you think it's not ok, you can stop here and edit it. Or let's go on?", console=console, default=True)
                if not is_ok:
                    console.print(
                        "Great! Check the config file and see you next time!", style="green")
                    to_gen = False
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
                        config[config_var.name] = config_var.get_default_value(
                            console)
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
                    to_gen = False

        domain = config["CRUPEST_DOMAIN"]

        if to_gen:
            console.print(
                "Finally, everything is ready. Let's generate the files:", style="green")

            # generate files
            for index, template in enumerate(template_list):
                number = index + 1
                total = len(template_list)
                print_order(number, total, console)
                console.print(
                    f"Generating [magenta]{template.template_name}[/]...")
                content = template.generate(config)
                with open(join(project_dir, template.template_name), "w") as f:
                    f.write(content)

            # generate nginx config
            if not exists(nginx_config_dir):
                to_gen_nginx_conf = Confirm.ask("It seems you haven't generate nginx config. Do you want to generate it?",
                                                default=True, console=console)
            else:
                # get the latest time of files in nginx template
                template_time = 0
                for path in os.listdir(nginx_template_dir):
                    template_time = max(template_time, os.stat(
                        join(nginx_template_dir, path)).st_mtime)
                console.print(
                    f"Nginx template update time: {datetime.fromtimestamp(template_time)}")

                nginx_config_time = 0
                for path in os.listdir(nginx_config_dir):
                    nginx_config_time = max(nginx_config_time, os.stat(
                        join(nginx_config_dir, path)).st_mtime)
                console.print(
                    f"Generated nginx template update time: {datetime.fromtimestamp(nginx_config_time)}")
                if template_time > nginx_config_time:
                    to_gen_nginx_conf = Confirm.ask("It seems you have updated the nginx template and not regenerate config. Do you want to regenerate the nginx config?",
                                                    default=True, console=console)
                else:
                    to_gen_nginx_conf = Confirm.ask("[yellow]It seems you have already generated nginx config. Do you want to overwrite it?[/]",
                                                    default=False, console=console)
            if to_gen_nginx_conf:
                nginx(domain, console)
    data_dir_check(domain)


def clean(template_name_list):
    # check root if we have to delete data dir
    if args.include_data_dir and exists(data_dir) and os.geteuid() != 0:
        console.print(
            "You need to be root to delete data dir.", style="red")
        exit(1)

    to_delete = Confirm.ask(
        "[yellow]Are you sure you want to delete everything? all your data will be lost![/]", default=False, console=console)
    if to_delete:
        files_to_delete = []
        for template_name in template_name_list:
            f = join(project_dir, template_name)
            if exists(f):
                files_to_delete.append(f)

    delete_data_dir = args.include_data_dir and exists(
        data_dir)

    if len(files_to_delete) == 0:
        console.print(
            "Nothing to delete. We are safe!", style="green")
    else:
        console.print("Here are the files to delete:")
        for f in files_to_delete:
            console.print(f, style="magenta")
        if delete_data_dir:
            console.print(data_dir + " (data dir)",
                          style="magenta")

        to_delete = Confirm.ask(
            "[red]Are you sure you want to delete them?[/]", default=False, console=console)
        if to_delete:
            for f in files_to_delete:
                os.remove(f)
            if delete_data_dir:
                # recursively delete data dir
                shutil.rmtree(data_dir)
        console.print(
            "Your workspace is clean now!", style="green")


def git_update():
    def do_it():
        subprocess.run(["git", "submodule", "update",
                       "--init", "--recursive"], check=True)
    run_in_project_dir(do_it)


def docker_compose_up():
    def do_docker_compose_up():
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
    run_in_dir(project_abs_path, do_docker_compose_up)


action = args.action


def run():
    match action:
        case "install-docker":
            install_docker()
            console.print(
                "Succeeded to install docker. Please re-login to take effect.", style="green")
        case "docker":
            docker_action = args.docker_action

            match docker_action:
                case "up":
                    docker_compose_up()
                case "down":
                    def docker_compose_down():
                        subprocess.run(
                            ["docker", "compose", "down"], check=True)
                    run_in_dir(project_abs_path, docker_compose_down)
                case "prune":
                    to_do = Confirm.ask(
                        "[yellow]Are you sure to prune docker?[/]", console=console)
                    if to_do:
                        subprocess.run(
                            ["docker", "system", "prune", "-a", "-f"], check=True)
                case _:
                    raise ValueError("Unknown docker action.")

        case "backup":
            backup_action = args.backup_action
            match backup_action:
                case "backup":
                    backup_backup(args.backup_path, console)
                    console.print("Succeeded to restore data.", style="green")
                case "restore":
                    backup_restore(args.restore_path, console)
                    console.print("Succeeded to backup data.", style="green")

        case 'print-path':
            console.print("Project path =", project_dir)
            console.print("Project absolute path =", project_abs_path)
            console.print("Data path =", data_dir)

        case "download-tools":
            download_tools(console)

        case "list-domain":
            domain = check_domain_is_defined()
            domains = list_domains(domain)
            for domain in domains:
                console.print(domain)
        case "nginx":
            domain = check_domain_is_defined()
            nginx(domain, console)

        case "certbot":
            domain = check_domain_is_defined()
            is_test = args.test
            if args.create:
                console.print(certbot_command_gen(domain, "create",
                                                  test=is_test), soft_wrap=True, highlight=False)
            elif args.expand:
                console.print(certbot_command_gen(domain, "expand",
                                                  test=is_test), soft_wrap=True, highlight=False)
            elif args.renew:
                console.print(certbot_command_gen(domain, "renew",
                                                  test=is_test), soft_wrap=True, highlight=False)
            else:
                console.print(
                    "Here is some commands you can use to do certbot related work.")
                if is_test:
                    console.print(
                        "Note you specified --test, so the commands are for test use.", style="yellow")
                console.print(
                    "To create certs for init (standalone):", style="cyan")
                console.print(certbot_command_gen(
                    domain, 'create', test=is_test), soft_wrap=True)
                console.print("To expand certs (nginx):", style="cyan")
                console.print(certbot_command_gen(
                    domain, 'create', test=is_test), soft_wrap=True)
                console.print(
                    "To renew certs previously created (nginx):", style="cyan")
                console.print(certbot_command_gen(
                    domain, 'renew', test=is_test), soft_wrap=True)
        case "test":
            match args.test_action:
                case "crupest-api":
                    test_crupest_api(console)
                case _:
                    console.print("Test action invalid.", style="red")
        case "dns":
            domain = check_domain_is_defined()
            if domain is not None:
                if args.ip is None:
                    ip = Prompt.ask(
                        "Please enter your server ip", console=console)
                else:
                    ip = args.ip
                console.print(generate_dns_zone_with_dkim(
                    domain, ip), soft_wrap=True, highlight=False)

        case "git-update":
            git_update()

        case "up":
            git_update()
            docker_compose_up()

        case _:
            console.print("First let's check all the templates...")

            # get all filenames ending with .template
            template_name_list = [basename(f)[:-len('.template')] for f in os.listdir(
                template_dir) if f.endswith(".template")]
            console.print(
                f"I have found following template files in [magenta]{template_dir}[/]:", style="green")
            for filename in template_name_list:
                console.print(f"{filename}.template", style="magenta")

            # if action is 'clean'
            if action == "clear":
                clean(template_name_list)
            else:
                setup(template_name_list)
                if Confirm.ask(
                        "By the way, would you like to download some scripts to do some extra setup like creating email user?", console=console, default=True):
                    download_tools(console)


run()

if not args.no_bye_bye:
    console.print(":beers: All done! Bye bye!", style="green")
