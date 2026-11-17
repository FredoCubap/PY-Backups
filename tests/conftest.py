"""Fixtures compartidas. Las bases son SIEMPRE temporales: nunca la real. (e1 1.3)"""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.admin import create_admin
from app.config import Settings
from app.database import make_engine, make_session_factory
from app.main import create_app

ROOT = Path(__file__).resolve().parent.parent
CLAVE_ADMIN = "clave-de-prueba-1"


def migrate(db_file: Path) -> str:
    """Aplica las migraciones sobre `db_file` y devuelve su URL async."""
    url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "migrations"))
    cfg.set_main_option("sqlalchemy.url", url)
    command.upgrade(cfg, "head")
    return url


@pytest.fixture
def db_url(tmp_path):
    return migrate(tmp_path / "test.db")


def run_with_session(db_url: str, fn):
    """Ejecuta `fn(session_factory)` en una base temporal y cierra el motor."""

    async def go():
        engine = make_engine(db_url)
        try:
            return await fn(make_session_factory(engine))
        finally:
            await engine.dispose()

    return asyncio.run(go())


@pytest.fixture
def app_settings(tmp_path):
    """Ajustes que apuntan a una carpeta de datos temporal ya migrada."""
    migrate(tmp_path / "app.db")
    return Settings(data_dir=tmp_path)


@pytest.fixture
def client(app_settings):
    with TestClient(create_app(app_settings), follow_redirects=False) as c:
        yield c


@pytest.fixture
def admin_client(app_settings):
    """Cliente con un admin `helix` ya creado en la base temporal."""
    run_with_session(
        app_settings.database_url, lambda f: create_admin(f, "helix", CLAVE_ADMIN)
    )
    with TestClient(create_app(app_settings), follow_redirects=False) as c:
        yield c


@pytest.fixture
def logged(admin_client):
    """`admin_client` con la sesión de `helix` ya abierta."""
    r = admin_client.post("/login", data={"username": "helix", "password": CLAVE_ADMIN})
    assert r.status_code == 303
    return admin_client
