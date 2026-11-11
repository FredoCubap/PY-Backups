import re

from tests.conftest import CLAVE_ADMIN


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert re.fullmatch(r"\d+\.\d+\.\d+", r.json()["version"])  # SemVer MAJOR.MINOR.PATCH


def test_la_raiz_lleva_al_login_sin_sesion(client):
    r = client.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/login"


def test_la_raiz_lleva_al_panel_con_sesion(admin_client):
    admin_client.post("/login", data={"username": "helix", "password": CLAVE_ADMIN})
    r = admin_client.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/panel"
