import os
import os.path

script_dir = os.path.relpath(os.path.dirname(__file__))
project_dir = os.path.normpath(os.path.join(script_dir, "../../../"))
project_abs_path = os.path.abspath(project_dir)
template_dir = os.path.join(project_dir, "template")
nginx_template_dir = os.path.join(template_dir, "nginx")
data_dir = os.path.join(project_dir, "data")
tool_dir = os.path.join(project_dir, "tools")
tmp_dir = os.path.join(project_dir, "tmp")
backup_dir = os.path.join(project_dir, "backup")
config_file_path = os.path.join(data_dir, "config")
nginx_config_dir = os.path.join(project_dir, "nginx-config")
log_dir = os.path.join(project_dir, "log")


def ensure_file(path: str, /, must_exist: bool = True) -> bool:
    if must_exist and not os.path.exists(path):
        raise Exception(f"File {path} does not exist!")
    if not os.path.exists(path):
        return False
    if not os.path.isfile(path):
        raise Exception(f"{path} is not a file!")
    return True


def ensure_dir(path: str, /, must_exist: bool = True) -> bool:
    if must_exist and not os.path.exists(path):
        raise Exception(f"Directory {path} does not exist!")
    if not os.path.exists(path):
        return False
    if not os.path.isdir(path):
        raise Exception(f"{path} is not a directory!")
    return True


class Paths:
    script_dir = os.path.relpath(os.path.dirname(__file__))
    project_dir = os.path.normpath(os.path.join(script_dir, "../../"))
    project_abs_path = os.path.abspath(project_dir)
    data_dir = os.path.join(project_dir, "data")
    config_file_path = os.path.join(data_dir, "config")
    template_dir = os.path.join(project_dir, "template")
    tool_dir = os.path.join(project_dir, "tool")
    tmp_dir = os.path.join(project_dir, "tmp")
    backup_dir = os.path.join(project_dir, "backup")
    log_dir = os.path.join(project_dir, "log")
    template2_dir = os.path.join(project_dir, "template2")
    nginx2_template_dir = os.path.join(template2_dir, "nginx")
    generated_dir = os.path.join(project_dir, "generated")
    nginx_generated_dir = os.path.join(generated_dir, "nginx")


def create_dir_if_not_exists(path: str) -> None:
    if not ensure_dir(path, must_exist=False):
        os.mkdir(path)
