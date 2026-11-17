"""Alta de trabajadores (e2 2.1) y código de alta (e2 2.2), sobre bases temporales."""

import hashlib
import re
import sqlite3
from datetime import datetime, timedelta

import pytest

from app.enroll import hash_code, new_code
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


# --- Código de alta (e2 2.2) ---

CODE_RE = re.compile(r"<code>([A-Z2-7]{4}(?:-[A-Z2-7]{1,4})+)</code>")


def _new_worker(logged, app_settings, username="trabajador1"):
    logged.post("/workers", data={"username": username})
    return _query(app_settings, f"select id from workers where username = '{username}'")[0][0]


def _codes(app_settings):
    return _query(app_settings, "select worker_id, code_hash, created_at, expires_at, used_at "
                                "from enroll_codes order by id")


def test_codigo_sin_sesion_no_se_genera(client, app_settings):
    r = client.post("/workers/1/enroll-code")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert _codes(app_settings) == []


def test_codigo_se_muestra_una_vez_y_solo_se_guarda_el_hash(logged, app_settings):
    wid = _new_worker(logged, app_settings)
    r = logged.post(f"/workers/{wid}/enroll-code")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    code = CODE_RE.search(r.text).group(1)
    assert len(code.replace("-", "")) == 26  # 128 bits en base32

    [(worker_id, code_hash, created, expires, used)] = _codes(app_settings)
    assert worker_id == wid and used is None
    expected = hashlib.sha256(code.replace("-", "").encode()).hexdigest()
    assert code_hash == hash_code(code) == expected
    created_dt, expires_dt = datetime.fromisoformat(created), datetime.fromisoformat(expires)
    assert expires_dt - created_dt == timedelta(hours=24)

    # El código no queda en ningún sitio de la base ni se vuelve a mostrar.
    dump = str(_query(app_settings, "select * from enroll_codes")) + str(
        _query(app_settings, "select * from audit_log"))
    assert code not in dump and code.replace("-", "") not in dump
    assert code not in logged.get("/workers").text
    assert _query(app_settings, "select actor, action, target, result from audit_log "
                                "where action = 'enroll-code-created'") == [
        ("helix", "enroll-code-created", "trabajador1", "ok")
    ]


def test_cada_codigo_es_distinto(logged, app_settings):
    wid = _new_worker(logged, app_settings)
    codes = {CODE_RE.search(logged.post(f"/workers/{wid}/enroll-code").text).group(1)
             for _ in range(5)}
    assert len(codes) == 5


def test_codigo_para_trabajador_inexistente_da_404(logged, app_settings):
    assert logged.post("/workers/999/enroll-code").status_code == 404
    assert logged.post("/workers/abc/enroll-code").status_code == 422
    assert _codes(app_settings) == []


def test_hash_code_normaliza_lo_que_se_teclea():
    code, h = new_code()
    assert hash_code(code.lower()) == h
    assert hash_code(" " + code.replace("-", " ") + "\n") == h
    assert hash_code(code.replace("-", "")) == h
    assert hash_code(code[:-1]) != h
