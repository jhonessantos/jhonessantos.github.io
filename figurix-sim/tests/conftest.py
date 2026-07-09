import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pytest

from cards import reset_uid_counter
from config import carregar_config


@pytest.fixture
def config():
    return carregar_config()


@pytest.fixture(autouse=True)
def _uid_determinismo():
    reset_uid_counter(1)
    yield
