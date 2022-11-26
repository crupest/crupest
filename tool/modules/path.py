import os
import os.path

script_dir = os.path.relpath(os.path.dirname(__file__))
project_dir = os.path.normpath(os.path.join(script_dir, "../../"))
project_abs_path = os.path.abspath(project_dir)
template_dir = os.path.join(project_dir, "template")
nginx_template_dir = os.path.join(template_dir, "nginx")
data_dir = os.path.join(project_dir, "data")
tool_dir = os.path.join(project_dir, "tool")
tmp_dir = os.path.join(project_dir, "tmp")
config_file_path = os.path.join(data_dir, "config")
nginx_config_dir = os.path.join(project_dir, "nginx-config")
log_dir = os.path.join(project_dir, "log")


def ensure_log_dir():
    if not os.path.exists(log_dir):
        os.mkdir(log_dir)


def ensure_tmp_dir():
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)
