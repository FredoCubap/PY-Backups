"""Login del admin, sesión y rutas protegidas, sobre bases temporales. (e1 2.3)"""

import sqlite3

from app import auth
from app.config import load_or_create_secret
from tests.conftest import CLAVE_ADMIN


def _logins(app_settings):
    con = sqlite3.connect(app_settings.database_path)
    filas = con.execute(
        "select actor, action, target, result, ip from audit_log where action = 'login' order by id"
    ).fetchall()
    con.close()
    return filas


def _entrar(client, usuario="helix", clave=CLAVE_ADMIN):
    return client.post("/login", data={"username": usuario, "password": clave})


def test_panel_sin_sesion_redirige_sin_datos(client):
    r = client.get("/panel")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"
    assert "helix" not in r.text


def test_formulario_de_login(client):
    r = client.get("/login")
    assert r.status_code == 200
    assert 'name="password"' in r.text


def test_login_correcto_abre_sesion_y_audita(admin_client, app_settings):
    r = _entrar(admin_client, usuario="  HELIX ")  # se normaliza
    assert r.status_code == 303
    assert r.headers["location"] == "/panel"
    cookie = r.headers["set-cookie"].lower()
    assert "pybackups_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie

    panel = admin_client.get("/panel")
    assert panel.status_code == 200
    assert "helix" in panel.text
    assert _logins(app_settings) == [("helix", "login", None, "ok", "testclient")]


def test_fallo_mismo_mensaje_para_usuario_o_clave_incorrectos(admin_client, app_settings):
    mala_clave = _entrar(admin_client, clave="clave-equivocada-99")
    sin_usuario = _entrar(admin_client, usuario="nadie", clave="clave-equivocada-99")
    for r in (mala_clave, sin_usuario):
        assert r.status_code == 401
        assert "Usuario o contraseña incorrectos." in r.text
        assert "set-cookie" not in r.headers  # no se abre sesión
    assert mala_clave.text == sin_usuario.text  # respuestas idénticas
    assert admin_client.get("/panel").status_code == 303

    assert _logins(app_settings) == [
        ("helix", "login", None, "fail", "testclient"),
        ("desconocido", "login", None, "fail", "testclient"),
    ]


def test_usuario_inexistente_tambien_verifica_contra_un_hash_ficticio(admin_client, monkeypatch):
    llamadas = []
    original = auth.verify_password

    def espia(clave, guardado):
        llamadas.append(guardado)
        return original(clave, guardado)

    monkeypatch.setattr(auth, "verify_password", espia)
    assert _entrar(admin_client, usuario="nadie").status_code == 401
    assert llamadas == [auth._dummy_hash()]  # mismo coste que un usuario real


def test_clave_demasiado_larga_se_rechaza_sin_derivar(admin_client, monkeypatch):
    def no_debe_llamarse(*_):
        raise AssertionError("no debía derivar")

    monkeypatch.setattr(auth, "verify_password", no_debe_llamarse)
    r = _entrar(admin_client, clave="x" * (auth.MAX_PASSWORD_LENGTH + 1))
    assert r.status_code == 401


def test_la_auditoria_no_guarda_lo_tecleado_como_usuario(admin_client, app_settings):
    secreto = "mi-clave-secreta-123!"
    assert _entrar(admin_client, usuario=secreto, clave="otra").status_code == 401
    con = sqlite3.connect(app_settings.database_path)
    volcado = str(con.execute("select * from audit_log").fetchall())
    con.close()
    assert secreto not in volcado
    assert "desconocido" in volcado


def test_logout_cierra_la_sesion(admin_client):
    _entrar(admin_client)
    assert admin_client.get("/panel").status_code == 200
    r = admin_client.post("/logout")
    assert r.status_code == 303 and r.headers["location"] == "/login"
    assert admin_client.get("/panel").status_code == 303


def test_login_con_sesion_abierta_va_al_panel(admin_client):
    _entrar(admin_client)
    r = admin_client.get("/login")
    assert r.status_code == 303 and r.headers["location"] == "/panel"


def test_cookie_manipulada_no_da_acceso(admin_client):
    admin_client.cookies.set("pybackups_session", "basura.firma.falsa")
    assert admin_client.get("/panel").status_code == 303


def test_admin_borrado_invalida_la_sesion(admin_client, app_settings):
    _entrar(admin_client)
    con = sqlite3.connect(app_settings.database_path)
    con.execute("delete from admin_users")
    con.commit()
    con.close()
    assert admin_client.get("/panel").status_code == 303


def test_la_clave_de_sesion_se_genera_una_vez_y_se_conserva(tmp_path):
    primera = load_or_create_secret(tmp_path)
    assert len(primera) == 64
    assert (tmp_path / "session.key").read_text().strip() == primera
    assert load_or_create_secret(tmp_path) == primera
