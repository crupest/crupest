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
import os.path
import sys
import argparse
import shutil
import subprocess
import urllib.request
import re
from rich.console import Console
from rich.prompt import Confirm
from modules.path import *
from modules.template import Template
from modules.nginx import *
from modules.configfile import *
from modules.config import *

console = Console()

parser = argparse.ArgumentParser(
    description="Crupest server all-in-one setup script. Have fun play with it!")
parser.add_argument("--no-hello", action="store_true",
                    default=False, help="Do not print hello message.")
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

backup_command_group = backup_parser.add_mutually_exclusive_group()
backup_command_group.add_argument(
    "-R", "--restore", action="append", nargs="?", default=None, help="Restore data from url.")
backup_command_group.add_argument(
    "-B", "--backup", action="append", nargs="?", default=None, help="Backup data to specified path.")

docker_parser = subparsers.add_parser("docker", help="Docker related things.")
docker_subparsers = docker_parser.add_subparsers(dest="docker_action")
docker_subparsers.add_parser("up", help="Run docker compose up -d.")
docker_subparsers.add_parser("down", help="Run docker compose down.")
docker_subparsers.add_parser(
    "prune", help="Run docker system prune -a -f.")

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


if not args.no_check_python_version:
    if sys.version_info < (3, 10):
        console.print("This script works well on python 3.10 or higher. Otherwise you may encounter some problems. But I would like to improve some rational compatibility.", style="yellow")


def check_ubuntu():
    if not os.path.exists("/etc/os-release"):
        return False
    else:
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if re.match(r"NAME=\"?Ubuntu\"?", content, re.IGNORECASE) is None:
                return False
            if re.match(r"UBUNTU_CODENAME=\"?jammy\"?", re.IGNORECASE) is None:
                return False
    return True


if not args.no_check_system:
    if not check_ubuntu():
        console.print("This script works well on Ubuntu 22.04. Otherwise you may encounter some problems. But I would like to improve some rational compatibility.", style="yellow")

if args.action == "certbot":
    if args.create or args.renew or args.expand:
        args.no_hello = True

if not args.no_hello:
    console.print("Nice to see you! :waving_hand:", style="cyan")


def print_order(number: int, total: int, *, console=console) -> None:
    console.print(f"\[{number}/{total}]", end=" ", style="green")


if args.action == "install-docker":
    ensure_tmp_dir()
    get_docker_path = os.path.join(tmp_dir, "get-docker.sh")
    urllib.request.urlretrieve("https://get.docker.com", get_docker_path)
    os.chmod(get_docker_path, 0o755)
    subprocess.run(["sudo", "sh", get_docker_path], check=True)
    subprocess.run(["sudo", "systemctl", "enable",
                   "--now", "docker"], check=True)
    subprocess.run(["sudo", "usermod", "-aG", "docker",
                   os.getlogin()], check=True)
    console.print(
        "Succeeded to install docker. Please re-login to take effect.", style="green")
    exit(0)


if args.action == "docker":
    def run_in_dir(dir: str, func: callable):
        old_dir = os.path.abspath(os.getcwd())
        os.chdir(dir)
        func()
        os.chdir(old_dir)
    match args.docker_action:
        case "up":
            def docker_compose_up():
                subprocess.run(["docker", "compose", "up", "-d"], check=True)
            run_in_dir(project_abs_path, docker_compose_up)
        case "down":
            def docker_compose_down():
                subprocess.run(["docker", "compose", "down"], check=True)
            run_in_dir(project_abs_path, docker_compose_down)
        case "prune":
            to_do = Confirm.ask("[yellow]Are you sure to prune docker?[/]")
            if to_do:
                subprocess.run(
                    ["docker", "system", "prune", "-a", "-f"], check=True)
        case _:
            raise ValueError("Unknown docker action.")
    exit(0)

if args.action == "backup":
    if not args.restore is None:
        if args.restore[0] is None:
            url = Prompt.ask(
                "You don't specify the path to restore from. Please specify one. http and https are supported", console=console)
        else:
            url = args.restore[0]
        if len(url) == 0:
            console.print("You specify an empty url. Abort.", style="red")
            exit(1)
        if url.startswith("http://") or url.startswith("https://"):
            download_path = os.path.join(tmp_dir, "data.tar.xz")
            if os.path.exists(download_path):
                to_remove = Confirm.ask(
                    f"I want to download to {download_path}. However, there is already a file there. Do you want to remove it first", default=False)
                if to_remove:
                    os.remove(download_path)
                else:
                    console.print(
                        "Aborted! Please check the file and try again.", style="cyan")
                    exit(0)
            urllib.request.urlretrieve(url, download_path)
            url = download_path
        subprocess.run(
            ["sudo", "tar", "-xJf", url, "-C", project_dir], check=True)
        console.print("Succeeded to restore data.", style="green")
        exit(0)
    elif not args.backup is None:
        if args.backup[0] is None:
            ensure_backup_dir()
            now = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
            path = Prompt.ask(
                "You don't specify the path to backup to. Please specify one. http and https are NOT supported", console=console, default=os.path.join(backup_dir, now + ".tar.xz"))
        else:
            path = args.backup[0]
        if len(path) == 0:
            console.print("You specify an empty path. Abort.", style="red")
            exit(1)
        if os.path.exists(path):
            console.print(
                "A file is already there. Please remove it first. Abort!", style="red")
            exit(1)
        subprocess.run(
            ["sudo", "tar", "-cJf", path, "data", "-C", project_dir],
            check=True
        )
        console.print("Succeeded to backup data.", style="green")
        exit(0)
    else:
        console.print(
            "You should specify either -R or -B. Abort!", style="red")
        exit(1)

if args.action == 'print-path':
    console.print("Project path =", project_dir)
    console.print("Project absolute path =", project_abs_path)
    console.print("Data path =", data_dir)
    exit(0)


def check_domain_is_defined() -> str:
    try:
        return get_domain()
    except ValueError as e:
        console.print(
            "We are not able to get the domain. You may want to first run setup command.", style="red")
        console.print_exception(e)
        exit(1)


def download_tools():
    # if we are not linux, we prompt the user
    if sys.platform != "linux":
        console.print(
            "You are not running this script on linux. The tools will not work.", style="yellow")
        if not Confirm.ask("Do you want to continue?", default=False, console=console):
            exit(0)

    SCRIPTS = [("docker-mailserver setup script", "docker-mailserver-setup.sh",
                "https://raw.githubusercontent.com/docker-mailserver/docker-mailserver/master/setup.sh")]
    for index, script in enumerate(SCRIPTS):
        number = index + 1
        total = len(SCRIPTS)
        print_order(number, total)
        name, filename, url = script
        # if url is callable, call it
        if callable(url):
            url = url()
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
    bad_files = nginx_config_dir_check(nginx_config_dir, domain)
    if len(bad_files) > 0:
        console.print(
            "WARNING: It seems there are some bad conf files in the nginx config directory:", style="yellow")
        for bad_file in bad_files:
            console.print(bad_file, style="cyan")
        to_delete = Confirm.ask(
            "They will affect nginx in a [red]bad[/] way. Do you want to delete them?", default=True, console=console)
        if to_delete:
            for file in bad_files:
                os.remove(os.path.join(nginx_config_dir, file))
    console.print(
        "I have found following var in nginx templates:", style="green")
    for var in nginx_var_set:
        console.print(var, end=" ", style="magenta")
    console.print()
    if not os.path.exists(nginx_config_dir):
        os.mkdir(nginx_config_dir)
        console.print(
            f"Nginx config directory created at [magenta]{nginx_config_dir}[/]", style="green")
    nginx_config_gen(domain, dest=nginx_config_dir)
    console.print("Nginx config generated.", style="green")


if args.action == 'list-domain':
    domain = check_domain_is_defined()
    domains = list_domains(domain)
    for domain in domains:
        console.print(domain)
    exit(0)

if args.action == 'certbot':
    domain = check_domain_is_defined()
    is_test = args.test
    if args.create:
        console.print(certbot_command_gen(domain, "create",
                                          test=is_test), soft_wrap=True, highlight=False)
        exit(0)
    elif args.expand:
        console.print(certbot_command_gen(domain, "expand",
                                          test=is_test), soft_wrap=True, highlight=False)
        exit(0)
    elif args.renew:
        console.print(certbot_command_gen(domain, "renew",
                                          test=is_test), soft_wrap=True, highlight=False)
        exit(0)
    console.print(
        "Here is some commands you can use to do certbot related work.")
    if is_test:
        console.print(
            "Note you specified --test, so the commands are for test use.", style="yellow")
    console.print(
        f"To create certs for init:\n[code]{certbot_command_gen(domain, 'create', test=is_test)}[/]")
    console.print(
        f"To renew certs previously created:\n[code]{certbot_command_gen(domain, 'renew', test=is_test)}[/]")
    exit(0)

if args.action == 'nginx':
    domain = check_domain_is_defined()
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
check_success, more, less = check_config_var_set(
    config_var_name_set_in_template)
if len(more) != 0:
    console.print("There are more variables in templates than in config file:",
                  style="red")
    for key in more:
        console.print(key, style="magenta")
if len(less) != 0:
    console.print("However, following config vars are not used:",
                  style="yellow")
    for key in less:
        console.print(key, style="magenta")

if not check_success:
    console.print(
        "Please check you config vars and make sure the needed ones are defined!", style="red")
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
            config[config_var.name] = config_var.get_default_value(console)
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
    # get the latest time of files in nginx template
    template_time = 0
    for path in os.listdir(nginx_template_dir):
        template_time = max(template_time, os.stat(
            os.path.join(nginx_template_dir, path)).st_mtime)
    console.print(
        f"Nginx template update time: {datetime.datetime.fromtimestamp(template_time)}")

    nginx_config_time = 0
    for path in os.listdir(nginx_config_dir):
        nginx_config_time = max(nginx_config_time, os.stat(
            os.path.join(nginx_config_dir, path)).st_mtime)
    console.print(
        f"Generated nginx template update time: {datetime.datetime.fromtimestamp(nginx_config_time)}")
    if template_time > nginx_config_time:
        to_gen_nginx_conf = Confirm.ask("It seems you have updated the nginx template and not regenerate config. Do you want to regenerate the nginx config?",
                                        default=True, console=console)
    else:
        to_gen_nginx_conf = Confirm.ask("[yellow]It seems you have already generated nginx config. Do you want to overwrite it?[/]",
                                        default=False, console=console)
if to_gen_nginx_conf:
    domain = config["CRUPEST_DOMAIN"]
    generate_nginx_config(domain)

if not os.path.exists(data_dir):
    console.print(
        "Looks like you haven't generated data dir. I'll create it for you.", style="green")
    os.mkdir(data_dir)
elif not os.path.isdir(data_dir):
    console.print(
        "ERROR: data dir is not a dir! Everything will be broken! Please delete it manually", style="red")


def print_create_cert_message(domain):
    console.print(
        "Looks like you haven't run certbot to get the init ssl certificates. You may want to run following code to get one:", style="cyan")
    console.print(certbot_command_gen(domain, "create"),
                  soft_wrap=True, highlight=False)


def check_ssl_cert():
    domain = check_domain_is_defined()
    cert_path = get_cert_path(domain)
    tmp_cert_path = os.path.join(tmp_dir, "fullchain.pem")
    console.print("Temporarily copy cert to tmp...", style="yellow")
    ensure_tmp_dir()
    subprocess.run(
        ["sudo", "cp", cert_path, tmp_cert_path], check=True)
    subprocess.run(["sudo", "chown", str(os.geteuid()),
                   tmp_cert_path], check=True)
    cert_domains = get_cert_domains(tmp_cert_path, domain)
    if cert_domains is None:
        print_create_cert_message(domain)
    else:
        cert_domain_set = set(cert_domains)
        domains = set(list_domains(domain))
        if not cert_domain_set == domains:
            console.print(
                "Cert domains are not equal to host domains. Run following command to recreate it.", style="red")
            console.print(certbot_command_gen(
                domain, "create", standalone=True), soft_wrap=True, highlight=False)
        console.print("Remove tmp cert...", style="yellow")
        os.remove(tmp_cert_path)


if os.path.isdir(data_dir):
    if not os.path.exists(os.path.join(data_dir, "certbot")):
        print_create_cert_message(check_domain_is_defined())
    else:
        to_check = Confirm.ask(
            "I want to check your ssl certs, but I need to sudo. Do you want me check", console=console, default=False)
        if to_check:
            check_ssl_cert()

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
                subprocess.run(
                    ["sudo", "chown", "-R", f"{os.getuid()}:{os.getgid()}", os.path.join(data_dir, 'code-server')], check=True)

console.print(":beers: All done!", style="green")
to_download_tools = Confirm.ask(
    "By the way, would you like to download some scripts to do some extra setup like creating email user?", console=console, default=True)
if not to_download_tools:
    console.print("Great! See you next time!", style="green")
    exit()

download_tools()
