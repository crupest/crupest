from ..common import Paths, console, ensure_file, UserFriendlyException
from config.config_map import ConfigMap
from rich.prompt import Confirm
from shutil import move


def setup_config_vars() -> None:
    console.print("Begin to setup config...")
    if ensure_file(Paths.config_file_path):
        console.print("Config file already exists. I'll load it...")
        try:
            configs = ConfigMap().load_from_file()
        except UserFriendlyException as e:
            raise UserFriendlyException(
                f"Looks like there is something wrong in your config file. {e.message}.")
        console.print("Config file loaded!")
        unused_items = configs.unused_items
        if len(unused_items) > 0:
            console.print(
                "Some config items are not used. You may want to remove them. Here is the list:")
            for item in unused_items:
                console.print(f"  {item.name} = {item.value}")
        fresh = False
    else:
        console.print("There is no config file. Let's setup one!")
        configs = ConfigMap()
        fresh = True

    undefined_vars = configs.undefined_vars

    if not fresh:
        if len(undefined_vars) > 0:
            console.print(
                "Some config variables are missing. You may want to add them. Let's add them!")

    for var in undefined_vars:
        configs.add_item(var.name, var.generate_default_value())

    console.log("Now the configs looks nice! Let's check it again:")
    for item in configs.items:
        console.log(f"  {item.name} = {item.value}")

    save = Confirm.ask("Do you want to save the config file?", default=True)
    if save:
        if not fresh:
            console.print("Move the original config file to config.bak")
            move(Paths.config_file_path, Paths.config_file_path + ".bak")
        configs.write_to_file()
        console.print("Config file saved!")
