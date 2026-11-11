import re


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert re.fullmatch(r"\d+\.\d+\.\d+", r.json()["version"])  # SemVer MAJOR.MINOR.PATCH


def test_home_funciona(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "funciona" in r.text
