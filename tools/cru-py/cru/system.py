import re
import os.path


def check_debian_derivative_version(name: str) -> None | str:
    if not os.path.isfile("/etc/os-release"):
        return None
    with open("/etc/os-release", "r") as f:
        content = f.read()
        if not f"ID={name}" in content:
            return None
        m = re.search(r'VERSION_ID="(.+)"', content)
        if m is None: return None
        return m.group(1)


def check_ubuntu_version() -> None | str:
    return check_debian_derivative_version("ubuntu")


def check_debian_version() -> None | str:
    return check_debian_derivative_version("debian")
