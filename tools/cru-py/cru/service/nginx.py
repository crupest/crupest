import json
import os
import re
import subprocess
from typing import Literal, Any, cast, ClassVar



def restart_nginx(force=False) -> bool:
    if not force:
        p = subprocess.run(['docker', "container", "ls",
                            "-f", "name=nginx", "-q"], capture_output=True)
        container: str = p.stdout.decode("utf-8")
        if len(container.strip()) == 0:
            return False
    subprocess.run(['docker', 'restart', 'nginx'])
    return True
