"""Alta de admin: función y CLI, siempre sobre bases temporales. (e1 2.2)"""

import sqlite3

import pytest
from sqlalchemy import select

from app import cli
from app.admin import AdminError, create_admin
from app.config import Settings
from app.models import AdminUser, AuditLog
from app.security import verify_password
from tests.conftest import migrate, run_with_session

CLAVE = "clave-de-prueba-1"


def test_crea_admin_con_hash_y_auditoria(db_url):
    async def caso(factory):
        assert await create_admin(factory, "  Admin1 ", CLAVE) == "admin1"
        async with factory() as s:
            usuario = (await s.scalars(select(AdminUser))).one()
            entradas = (await s.scalars(select(AuditLog))).all()
        return usuario, entradas

    usuario, entradas = run_with_session(db_url, caso)
    assert usuario.username == "admin1"  # normalizado a minúsculas
    assert usuario.password_hash != CLAVE
    assert verify_password(CLAVE, usuario.password_hash)
    assert [(e.actor, e.action, e.target, e.result) for e in entradas] == [
        ("cli", "admin-created", "admin1", "ok")
    ]
    # Ninguna entrada contiene la contraseña.
    assert all(CLAVE not in str(vars(e)) for e in entradas)
    assert "T" in entradas[0].ts and entradas[0].ts[-6] in "+-"  # ISO con desfase


def test_usuario_repetido_aunque_cambien_las_mayusculas(db_url):
    async def caso(factory):
        await create_admin(factory, "admin1", CLAVE)
        with pytest.raises(AdminError, match="ya existe"):
            await create_admin(factory, "ADMIN1", CLAVE)

    run_with_session(db_url, caso)


@pytest.mark.parametrize(
    ("usuario", "clave"),
    [("ab", CLAVE), ("con espacio", CLAVE), ("", CLAVE), ("admin1", "corta"), ("admin1", "")],
)
def test_datos_invalidos_no_crean_nada(db_url, usuario, clave):
    async def caso(factory):
        with pytest.raises(AdminError) as exc:
            await create_admin(factory, usuario, clave)
        assert clave not in str(exc.value) or clave == ""
        async with factory() as s:
            assert (await s.scalars(select(AdminUser))).all() == []

    run_with_session(db_url, caso)


def test_caracter_no_codificable_no_filtra_la_contrasena(db_url):
    clave = "abcdefghij\ud800"

    async def caso(factory):
        with pytest.raises(AdminError) as exc:
            await create_admin(factory, "admin1", clave)
        assert "\ud800" not in str(exc.value)
        assert exc.value.__cause__ is None

    run_with_session(db_url, caso)


def _cli_con_base(monkeypatch, tmp_path, claves):
    """Prepara el CLI contra una base temporal y teclado simulado."""
    migrate(tmp_path / "app.db")
    monkeypatch.setattr(cli, "settings", Settings(data_dir=tmp_path))
    respuestas = iter(claves)
    monkeypatch.setattr(cli.getpass, "getpass", lambda *_: next(respuestas))
    return tmp_path / "app.db"


def test_cli_crea_el_admin(monkeypatch, tmp_path, capsys):
    base = _cli_con_base(monkeypatch, tmp_path, [CLAVE, CLAVE])
    assert cli.main(["crear-admin", "--usuario", "admin1"]) == 0
    assert "creado" in capsys.readouterr().out
    con = sqlite3.connect(base)
    assert con.execute("select username from admin_users").fetchall() == [("admin1",)]
    con.close()


def test_cli_confirmacion_distinta_no_crea_nada(monkeypatch, tmp_path, capsys):
    base = _cli_con_base(monkeypatch, tmp_path, [CLAVE, CLAVE + "x"])
    assert cli.main(["crear-admin", "--usuario", "admin1"]) == 1
    assert "no coinciden" in capsys.readouterr().err
    con = sqlite3.connect(base)
    assert con.execute("select count(*) from admin_users").fetchone() == (0,)
    con.close()


def test_cli_sin_base_no_crea_un_archivo_vacio(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(cli, "settings", Settings(data_dir=tmp_path))
    assert cli.main(["crear-admin", "--usuario", "admin1"]) == 1
    assert "alembic upgrade head" in capsys.readouterr().err
    assert not (tmp_path / "app.db").exists()
