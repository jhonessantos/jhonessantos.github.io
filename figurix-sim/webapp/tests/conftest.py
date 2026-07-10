import sys
from pathlib import Path

WEBAPP = Path(__file__).resolve().parent.parent
SRC = WEBAPP.parent / "src"
for caminho in (str(WEBAPP), str(SRC)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)

import pytest  # noqa: E402

from cards import reset_uid_counter  # noqa: E402
from config import carregar_config  # noqa: E402


@pytest.fixture
def config():
    return carregar_config()


@pytest.fixture(autouse=True)
def _uid_determinismo():
    reset_uid_counter(1)
    yield


@pytest.fixture
def db_temporario(tmp_path, monkeypatch):
    import db

    monkeypatch.setattr(db, "DB_PATH", tmp_path / "figurix_teste.db")
    db.inicializar_banco()
    return db
