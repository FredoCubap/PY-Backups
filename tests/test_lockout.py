"""Bloqueo tras intentos de login fallidos. (e1 2.4)"""

import sqlite3

import pytest

from app import auth
from app.lockout import LoginLimiter
from tests.conftest import CLAVE_ADMIN

KEY = ("helix", "10.0.0.5")


class Reloj:
    """Reloj controlable para no esperar 5 minutos de verdad."""

    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


@pytest.fixture
def reloj():
    return Reloj()


@pytest.fixture
def limiter(reloj):
    return LoginLimiter(now=reloj)


def _fallar(limiter, n, key=KEY):
    return [limiter.register_failure(key) for _ in range(n)]


# --- la lógica del contador -------------------------------------------------


def test_cuatro_fallos_no_bloquean_el_quinto_si(limiter):
    assert _fallar(limiter, 4) == [False] * 4
    assert limiter.blocked_for(KEY) == 0
    assert limiter.register_failure(KEY) is True  # el quinto inicia el bloqueo
    assert limiter.blocked_for(KEY) == 300


def test_el_bloqueo_termina_a_los_5_minutos(limiter, reloj):
    _fallar(limiter, 5)
    reloj.t += 299
    assert limiter.blocked_for(KEY) == pytest.approx(1)
    reloj.t += 2
    assert limiter.blocked_for(KEY) == 0
    # y vuelve a empezar de cero: hacen falta otros 5 fallos
    assert _fallar(limiter, 4) == [False] * 4


def test_el_bloqueo_no_se_alarga_por_seguir_intentando(limiter, reloj):
    _fallar(limiter, 5)
    reloj.t += 100
    assert limiter.register_failure(KEY) is False  # ya estaba bloqueado
    assert limiter.blocked_for(KEY) == pytest.approx(200)


def test_los_fallos_viejos_no_se_acumulan(limiter, reloj):
    _fallar(limiter, 4)
    reloj.t += 301
    assert limiter.register_failure(KEY) is False  # cuenta como el primero
    assert limiter.blocked_for(KEY) == 0


def test_un_login_correcto_reinicia_la_cuenta(limiter):
    _fallar(limiter, 4)
    limiter.reset(KEY)
    assert _fallar(limiter, 4) == [False] * 4


def test_otra_ip_u_otro_usuario_no_se_ven_afectados(limiter):
    _fallar(limiter, 5)
    assert limiter.blocked_for(("helix", "10.0.0.9")) == 0
    assert limiter.blocked_for(("otro", "10.0.0.5")) == 0


def test_la_memoria_tiene_tope(reloj):
    limiter = LoginLimiter(max_keys=100, now=reloj)
    for i in range(500):
        limiter.register_failure((f"usuario{i}", "10.0.0.5"))
        reloj.t += 0.001
    assert len(limiter._entries) <= 100


# --- el login real ----------------------------------------------------------


def _entrar(client, clave):
    return client.post("/login", data={"username": "helix", "password": clave})


def test_el_sexto_intento_se_rechaza_aunque_la_clave_sea_correcta(admin_client, monkeypatch):
    llamadas = []
    original = auth.verify_password

    def espia(clave, guardado):
        llamadas.append(1)
        return original(clave, guardado)

    monkeypatch.setattr(auth, "verify_password", espia)
    for _ in range(5):
        assert _entrar(admin_client, "mala-clave-99").status_code == 401

    r = _entrar(admin_client, CLAVE_ADMIN)  # la correcta, pero ya bloqueado
    assert r.status_code == 429
    assert "Demasiados intentos" in r.text
    assert int(r.headers["retry-after"]) in range(299, 301)
    assert "set-cookie" not in r.headers
    assert admin_client.get("/panel").status_code == 303
    assert len(llamadas) == 5  # el bloqueado no deriva nada


def test_pasado_el_bloqueo_se_puede_entrar(admin_client, reloj):
    admin_client.app.state.login_limiter = LoginLimiter(now=reloj)
    for _ in range(5):
        _entrar(admin_client, "mala-clave-99")
    assert _entrar(admin_client, CLAVE_ADMIN).status_code == 429
    reloj.t += 301
    assert _entrar(admin_client, CLAVE_ADMIN).status_code == 303


def test_un_login_correcto_reinicia_la_cuenta_real(admin_client):
    for _ in range(4):
        _entrar(admin_client, "mala-clave-99")
    assert _entrar(admin_client, CLAVE_ADMIN).status_code == 303
    admin_client.post("/logout")
    for _ in range(4):
        assert _entrar(admin_client, "mala-clave-99").status_code == 401  # no se bloquea


def test_el_bloqueo_tambien_vale_para_usuarios_inexistentes(admin_client):
    for _ in range(5):
        admin_client.post("/login", data={"username": "nadie", "password": "x-clave-larga-1"})
    r = admin_client.post("/login", data={"username": "nadie", "password": "x-clave-larga-1"})
    assert r.status_code == 429  # no delata qué usuarios existen


def test_se_audita_el_inicio_del_bloqueo_y_no_cada_intento_bloqueado(admin_client, app_settings):
    for _ in range(5):
        _entrar(admin_client, "mala-clave-99")
    for _ in range(3):
        _entrar(admin_client, CLAVE_ADMIN)  # bloqueados
    con = sqlite3.connect(app_settings.database_path)
    filas = con.execute(
        "select actor, action, result from audit_log where action like 'login%' order by id"
    ).fetchall()
    volcado = str(con.execute("select * from audit_log").fetchall())
    con.close()
    assert filas == [("helix", "login", "fail")] * 5 + [("helix", "login-locked", "blocked")]
    assert "mala-clave-99" not in volcado and CLAVE_ADMIN not in volcado
