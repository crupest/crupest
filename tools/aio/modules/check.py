import sys
import re
from os.path import *


def check_python_version(required_version=(3, 10)):
    return sys.version_info < required_version


def check_ubuntu():
    if not exists("/etc/os-release"):
        return False
    else:
        with open("/etc/os-release", "r") as f:
            content = f.read()
            if re.search(r"NAME=\"?Ubuntu\"?", content, re.IGNORECASE) is None:
                return False
            if re.search(r"VERSION_ID=\"?22.04\"?", content, re.IGNORECASE) is None:
                return False
    return True
