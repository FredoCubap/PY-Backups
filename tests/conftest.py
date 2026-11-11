"""Fixtures compartidas. Las bases son SIEMPRE temporales: nunca la real. (e1 1.3)"""

import asyncio
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from app.database import make_engine, make_session_factory

ROOT = Path(__file__).resolve().parent.parent


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

