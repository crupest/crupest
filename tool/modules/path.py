import os.path

script_dir = os.path.relpath(os.path.dirname(__file__))
project_dir = os.path.normpath(os.path.join(script_dir, "../../"))
template_dir = os.path.join(project_dir, "template")
nginx_template_dir = os.path.join(template_dir, "nginx")
data_dir = os.path.join(project_dir, "data")
tool_dir = os.path.join(project_dir, "tool")
config_file_path = os.path.join(data_dir, "config")
nginx_config_dir = os.path.join(project_dir, "nginx-config")

__all__ = ["script_dir", "project_dir", "template_dir",
           "nginx_template_dir", "data_dir", "config_file_path", "tool_dir", "nginx_config_dir"]
