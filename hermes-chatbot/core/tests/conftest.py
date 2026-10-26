import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from core_helpers import make_event  # noqa: E402


@pytest.fixture
def group_event():
    return make_event

