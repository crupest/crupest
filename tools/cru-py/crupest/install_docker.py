from os.path import *
from .path import *
import urllib
import subprocess


def install_docker():
    ensure_tmp_dir()
    get_docker_path = join(tmp_dir, "get-docker.sh")
    urllib.request.urlretrieve("https://get.docker.com", get_docker_path)
    os.chmod(get_docker_path, 0o755)
    subprocess.run(["sudo", "sh", get_docker_path], check=True)
    subprocess.run(["sudo", "systemctl", "enable",
                   "--now", "docker"], check=True)
    subprocess.run(["sudo", "usermod", "-aG", "docker",
                   os.getlogin()], check=True)
