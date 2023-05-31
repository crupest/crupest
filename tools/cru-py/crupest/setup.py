from os.path import *
from datetime import datetime
from rich.prompt import Confirm
from .path import *
from .nginx import *
from .config import *
from .helper import *


def get_template_name_list(console) -> list[str]:
    console.print("First let's check all the templates...")

    # get all filenames ending with .template
    template_name_list = [basename(f)[:-len('.template')] for f in os.listdir(
        template_dir) if f.endswith(".template")]
    console.print(
        f"I have found following template files in [magenta]{template_dir}[/]:", style="green")
    for filename in template_name_list:
        console.print(f"{filename}.template", style="magenta")

    return template_name_list


def data_dir_check(domain, console):
    if isdir(data_dir):
        if not exists(join(data_dir, "certbot")):
            print_create_cert_message(domain, console)
        else:
            to_check = Confirm.ask(
                "I want to check your ssl certs, but I need to sudo. Do you want me check", console=console, default=False)
            if to_check:
                check_ssl_cert(domain, console)


def template_generate(console):
    template_name_list = get_template_name_list(console)
    template_list: list = []
    config_var_name_set_in_template = set()
    for template_name in template_name_list:
        template = Template(join(template_dir, template_name+".template"))
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

        domain = get_domain()

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
                nginx(domain, config, console)
    data_dir_check(domain, console)


def clear(console, /, delete_data_dir=False):
    template_name_list = get_template_name_list(console)
    # check root if we have to delete data dir
    if delete_data_dir and exists(data_dir) and os.geteuid() != 0:
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

    delete_data_dir = delete_data_dir and exists(
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
