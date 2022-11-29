#!/usr/bin/env python3

try:
    import rich
    import jsonschema
    import cryptography
except ImportError:
    print("Some necessary modules can't be imported. Please run `pip install -r requirements.txt` to install them.")
    exit(1)

from os.path import *
import argparse
import subprocess
from rich.console import Console
from rich.prompt import Confirm
from modules.install_docker import *
from modules.path import *
from modules.nginx import *
from modules.config import *
from modules.check import *
from modules.backup import *
from modules.download_tools import *
from modules.test import *
from modules.dns import *
from modules.setup import *

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

down_parser = subparsers.add_parser(
    "down", help="Do something necessary and then docker compose down.")

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


def git_update():
    def do_it():
        subprocess.run(["git", "pull"], check=True)
    run_in_project_dir(do_it)


def docker_compose_up():
    def do_docker_compose_up():
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
    run_in_dir(project_abs_path, do_docker_compose_up)


def docker_compose_down():
    def do_docker_compose_down():
        subprocess.run(
            ["docker", "compose", "down"], check=True)
    run_in_dir(project_abs_path, do_docker_compose_down)


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
                    docker_compose_down()
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
            template_generate(console)
            docker_compose_up()

        case "down":
            docker_compose_down()

        case "clear":
            clear(console, args.include_data_dir)

        case _:
            template_generate(console)
            if Confirm.ask(
                    "By the way, would you like to download some scripts to do some extra setup like creating email user?", console=console, default=True):
                download_tools(console)


run()

if not args.no_bye_bye:
    console.print(":beers: All done! Bye bye!", style="green")
