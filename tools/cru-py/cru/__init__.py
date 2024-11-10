import sys

from ._base import CruException


class CruInitError(CruException):
    pass


def check_python_version(required_version=(3, 11)):
    if sys.version_info < required_version:
        raise CruInitError(f"Python version must be >= {required_version}!")


check_python_version()
