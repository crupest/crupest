import os
import os.path

script_dir = os.path.relpath(os.path.dirname(__file__))
project_dir = os.path.normpath(os.path.join(script_dir, "../../"))
project_abs_path = os.path.abspath(project_dir)
template_dir = os.path.join(project_dir, "template")
generate_dir = os.path.join(project_dir, "generate")
data_dir = os.path.join(project_dir, "data")
config_file_path = os.path.join(data_dir, "config")
tool_dir = os.path.join(project_dir, "tool")
tmp_dir = os.path.join(project_dir, "tmp")
backup_dir = os.path.join(project_dir, "backup")
log_dir = os.path.join(project_dir, "log")


def ensure_dir(dir):
    if os.path.exists(dir) and not os.path.isdir(dir):
        raise Exception("Path is not a directory: " + dir)
    if not os.path.exists(dir):
        os.makedirs(dir)
