"""Canje del código de alta por una PC, sobre bases temporales. (e2 2.3)

La MAC de la ARP se inyecta en `app.state.resolve_mac`: ningún test hace
ping ni lee la ARP de verdad. Solo MACs e IPs inventadas.
"""

import re
import sqlite3
import subprocess
from datetime import datetime, timedelta

import pytest

from app import arp
from app.enroll import BAD_CODE, MAC_MISMATCH, MAC_TAKEN, NO_ARP, hash_token

MAC_A = "AA:BB:CC:00:11:22"
MAC_B = "AA:BB:CC:00:11:33"
MAC_C = "AA:BB:CC:00:11:44"
CODE_RE = re.compile(r"<code>([A-Z2-7-]+)</code>")


def _query(app_settings, sql, args=()):
    con = sqlite3.connect(app_settings.database_path)
    rows = con.execute(sql, args).fetchall()
    con.commit()
    con.close()
    return rows


def _code_for(logged, app_settings, username="trabajador1"):
    logged.post("/workers", data={"username": username})
    [(wid,)] = _query(app_settings, "select id from workers where username = ?", (username,))
    return CODE_RE.search(logged.post(f"/workers/{wid}/enroll-code").text).group(1)


def _redeem(c, code, macs=(MAC_A,), arp_mac=MAC_A):
    c.app.state.resolve_mac = lambda ip: arp_mac
    return c.post("/enroll/redeem", json={"code": code, "macs": list(macs)})


def _devices(app_settings):
    return _query(app_settings, "select id, worker_id, token_hash, created_at, expires_at, "
                                "revoked_at from devices")


def _enroll_audits(app_settings):
    return _query(app_settings, "select actor, target, result, ip from audit_log "
                                "where action = 'pc-enroll' order by id")


@pytest.fixture
def code(logged, app_settings):
    return _code_for(logged, app_settings)


def test_canje_correcto_crea_la_pc_y_devuelve_el_token_una_vez(logged, app_settings, code):
    r = _redeem(logged, code, macs=["aa-bb-cc-00-11-22", MAC_B, MAC_A])  # MAC_A repetida
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    token = r.json()["token"]
    assert len(token) == 43  # 256 bits en base64url

    [(did, _wid, token_hash, created, expires, revoked)] = _devices(app_settings)
    assert token_hash == hash_token(token) and revoked is None
    assert datetime.fromisoformat(expires) - datetime.fromisoformat(created) == timedelta(
        days=365)
    assert _query(app_settings, "select mac from device_macs where device_id = ? order by mac",
                  (did,)) == [(MAC_A,), (MAC_B,)]
    [(used_at,)] = _query(app_settings, "select used_at from enroll_codes")
    assert used_at is not None
    assert _enroll_audits(app_settings) == [("pc", "trabajador1", "ok", "testclient")]

    dump = "".join(str(_query(app_settings, f"select * from {t}"))
                   for t in ("devices", "audit_log", "enroll_codes"))
    assert token not in dump


def test_codigo_tecleado_en_minusculas_y_sin_guiones_vale(logged, code):
    assert _redeem(logged, code.lower().replace("-", " ")).status_code == 200


def test_reuso_del_codigo_da_403_y_se_audita(logged, app_settings, code):
    assert _redeem(logged, code).status_code == 200
    r = _redeem(logged, code, macs=[MAC_C], arp_mac=MAC_C)
    assert r.status_code == 403 and r.json()["detail"] == BAD_CODE
    assert len(_devices(app_settings)) == 1
    assert _enroll_audits(app_settings)[-1] == ("pc", "trabajador1", "bad-code", "testclient")


def test_codigo_caducado_da_403(logged, app_settings, code):
    past = (datetime.now().astimezone() - timedelta(seconds=1)).isoformat(timespec="seconds")
    _query(app_settings, "update enroll_codes set expires_at = ?", (past,))
    r = _redeem(logged, code)
    assert r.status_code == 403 and r.json()["detail"] == BAD_CODE
    assert _devices(app_settings) == []


def test_codigo_inexistente_da_403_sin_trabajador_en_la_auditoria(logged, app_settings):
    r = _redeem(logged, "AAAA-BBBB-CCCC-DDDD-EEEE-FFFF-GG")
    assert r.status_code == 403 and r.json()["detail"] == BAD_CODE
    assert _enroll_audits(app_settings) == [("pc", None, "bad-code", "testclient")]


def test_sin_entrada_arp_no_crea_nada(logged, app_settings, code):
    r = _redeem(logged, code, arp_mac=None)
    assert r.status_code == 403 and r.json()["detail"] == NO_ARP
    assert _devices(app_settings) == []
    assert _enroll_audits(app_settings)[-1][2] == "no-arp"


def test_mac_distinta_se_rechaza_sin_quemar_el_codigo(logged, app_settings, code):
    r = _redeem(logged, code, macs=[MAC_B], arp_mac=MAC_A)
    assert r.status_code == 403 and r.json()["detail"] == MAC_MISMATCH
    assert MAC_A not in r.text  # no se revela qué MAC vio el servidor
    assert _devices(app_settings) == []
    assert _enroll_audits(app_settings)[-1][2] == "mac-mismatch"
    assert _redeem(logged, code).status_code == 200  # el código sigue valiendo


def test_mac_ya_tomada_da_409_y_no_crea_ni_quema_nada(logged, app_settings, code):
    assert _redeem(logged, code, macs=[MAC_A, MAC_B]).status_code == 200
    code2 = _code_for(logged, app_settings, "trabajador2")
    r = _redeem(logged, code2, macs=[MAC_C, MAC_B], arp_mac=MAC_C)  # MAC_B ya es de la PC 1
    assert r.status_code == 409 and r.json()["detail"] == MAC_TAKEN
    assert len(_devices(app_settings)) == 1
    assert _query(app_settings, "select count(*) from device_macs") == [(2,)]
    assert _enroll_audits(app_settings)[-1] == ("pc", "trabajador2", "mac-taken", "testclient")
    [(used,)] = _query(app_settings, "select used_at from enroll_codes where id = 2")
    assert used is None  # se deshizo también el uso del código


@pytest.mark.parametrize(
    "body",
    [
        {"code": "x", "macs": []},
        {"code": "x", "macs": ["zz"]},
        {"code": "x", "macs": ["FF:FF:FF:FF:FF:FF"]},
        {"code": "x", "macs": [f"AA:BB:CC:00:11:{i:02X}" for i in range(17)]},
        {"code": "x" * 65, "macs": [MAC_A]},
        {"code": "x", "macs": ["A" * 65]},
        {"code": 123, "macs": [MAC_A]},
        {"macs": [MAC_A]},
        {"code": "x"},
    ],
)
def test_entrada_invalida_da_422_sin_tocar_la_base(client, app_settings, body):
    assert client.post("/enroll/redeem", json=body).status_code == 422
    assert _devices(app_settings) == []


# --- resolve_mac: ping + ARP (sin ejecutar nada de verdad) ---

ARP_OUT = "  192.168.1.20          aa-bb-cc-00-11-20     dynamic\n"


def _fake_subprocess(monkeypatch):
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return type("R", (), {"stdout": ARP_OUT.encode() if cmd[0] == "arp" else b""})()

    monkeypatch.setattr(arp.subprocess, "run", fake_run)
    return calls


def test_resolve_mac_hace_ping_y_lee_la_arp(monkeypatch):
    calls = _fake_subprocess(monkeypatch)
    assert arp.resolve_mac("192.168.1.20") == "AA:BB:CC:00:11:20"
    assert [c[0] for c in calls] == [["ping", "-n", "1", "-w", "500", "192.168.1.20"],
                                     ["arp", "-a"]]
    assert all("shell" not in kw and kw["timeout"] for _, kw in calls)


@pytest.mark.parametrize(
    "ip", ["-t", "192.168.1.20 -t", "::1", "testclient", "", None, 3232235796, "192.168.001.020"]
)
def test_resolve_mac_no_ejecuta_nada_con_ip_rara(monkeypatch, ip):
    calls = _fake_subprocess(monkeypatch)
    assert arp.resolve_mac(ip) is None
    assert calls == []


def test_resolve_mac_lee_la_arp_aunque_falle_el_ping(monkeypatch):
    calls = _fake_subprocess(monkeypatch)
    original = arp.subprocess.run

    def run(cmd, **kwargs):
        if cmd[0] == "ping":
            raise subprocess.TimeoutExpired(cmd, 3)
        return original(cmd, **kwargs)

    monkeypatch.setattr(arp.subprocess, "run", run)
    assert arp.resolve_mac("192.168.1.20") == "AA:BB:CC:00:11:20"
    assert [c[0][0] for c in calls] == ["arp"]


def test_dos_canjes_simultaneos_solo_gana_uno(logged, app_settings, code):
    # Mientras se resuelve la ARP (en un hilo), otro canje gana la carrera y
    # marca el código como usado. Este canje debe perder sin crear nada.
    def other_redeem_wins(ip):
        _query(app_settings, "update enroll_codes set used_at = 'x'")
        return MAC_A

    logged.app.state.resolve_mac = other_redeem_wins
    r = logged.post("/enroll/redeem", json={"code": code, "macs": [MAC_A]})
    assert r.status_code == 403 and r.json()["detail"] == BAD_CODE
    assert _devices(app_settings) == []
