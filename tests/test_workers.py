"""Alta de trabajadores desde el panel, sobre bases temporales. (e2 2.1)"""

import sqlite3

import pytest

from tests.conftest import CLAVE_ADMIN


def _query(app_settings, sql):
    con = sqlite3.connect(app_settings.database_path)
    rows = con.execute(sql).fetchall()
    con.close()
    return rows


def _workers(app_settings):
    return [r[0] for r in _query(app_settings, "select username from workers order by id")]


def _audits(app_settings):
    return _query(
        app_settings,
        "select actor, action, target, result, ip from audit_log "
        "where action = 'worker-created' order by id",
    )


@pytest.fixture
def logged(admin_client):
    r = admin_client.post("/login", data={"username": "helix", "password": CLAVE_ADMIN})
    assert r.status_code == 303
    return admin_client


def test_sin_sesion_no_se_ve_ni_se_crea(client, app_settings):
    for r in (client.get("/workers"), client.post("/workers", data={"username": "trabajador1"})):
        assert r.status_code == 303 and r.headers["location"] == "/login"
    assert _workers(app_settings) == []


def test_crea_trabajador_normalizado_y_audita(logged, app_settings):
    r = logged.post("/workers", data={"username": "  Trabajador.Uno "})
    assert r.status_code == 303 and r.headers["location"] == "/workers"
    assert _workers(app_settings) == ["trabajador.uno"]
    assert "trabajador.uno" in logged.get("/workers").text
    assert _audits(app_settings) == [
        ("helix", "worker-created", "trabajador.uno", "ok", "testclient")
    ]


def test_repetido_con_otras_mayusculas_se_rechaza(logged, app_settings):
    logged.post("/workers", data={"username": "trabajador1"})
    r = logged.post("/workers", data={"username": "TRABAJADOR1"})
    assert r.status_code == 409
    assert "Ese usuario ya existe." in r.text
    assert _workers(app_settings) == ["trabajador1"]
    assert _audits(app_settings)[-1] == (
        "helix", "worker-created", "trabajador1", "fail", "testclient"
    )


@pytest.mark.parametrize(
    "username",
    [
        "", "ab", "a" * 33, "trabajador uno", "año1", "١٢٣٤", "<script>",
        "trabajador\x00", "a/b", "x" * 100_000,
    ],
)
def test_usuario_invalido_no_crea_nada(logged, app_settings, username):
    r = logged.post("/workers", data={"username": username})
    assert r.status_code == 400
    assert "El usuario debe tener de 3 a 32 caracteres" in r.text
    assert _workers(app_settings) == []
    assert _audits(app_settings) == []


def test_panel_enlaza_a_trabajadores(logged):
    assert 'href="/workers"' in logged.get("/panel").text
