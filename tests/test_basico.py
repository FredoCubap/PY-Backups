import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert re.fullmatch(r"\d+\.\d+\.\d+", r.json()["version"])  # SemVer MAJOR.MINOR.PATCH


def test_home_funciona():
    r = client.get("/")
    assert r.status_code == 200
    assert "funciona" in r.text
