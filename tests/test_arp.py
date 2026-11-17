"""Pruebas de mac_lookup por ARP. (e2 1.3)

Todas las fixtures están inventadas. Ningún test ejecuta `arp` de verdad.
"""

import subprocess

import pytest

from app.arp import _run_arp, mac_lookup, parse_arp

# ---------------------------------------------------------------------------
# Fixtures inventadas (salida de `arp -a`, nunca salida real)
# ---------------------------------------------------------------------------

ARP_EN = """Interface: 192.168.1.10 --- 0x5
  Internet Address      Physical Address      Type
  192.168.1.1           aa-bb-cc-00-11-01     dynamic
  192.168.1.20          aa-bb-cc-00-11-20     dynamic
  192.168.1.255         ff-ff-ff-ff-ff-ff     static
  224.0.0.22            01-00-5e-00-00-16     static
"""

ARP_ES = """Interfaz: 192.168.1.10 --- 0x5
  Dirección de Internet          Dirección física      Tipo
  192.168.1.1           aa-bb-cc-00-11-01     dinámico
  192.168.1.30          aa-bb-cc-00-11-30     dinámico
"""

# ---------------------------------------------------------------------------
# parse_arp: casos felices
# ---------------------------------------------------------------------------

def test_encuentra_mac_ingles():
    assert parse_arp(ARP_EN, "192.168.1.20") == "AA:BB:CC:00:11:20"


def test_encuentra_mac_espanol():
    assert parse_arp(ARP_ES, "192.168.1.30") == "AA:BB:CC:00:11:30"


def test_devuelve_mac_canonica_mayusculas_y_puntos():
    assert parse_arp(ARP_EN, "192.168.1.1") == "AA:BB:CC:00:11:01"


# ---------------------------------------------------------------------------
# parse_arp: devuelve None
# ---------------------------------------------------------------------------

def test_ip_ausente_devuelve_none():
    assert parse_arp(ARP_EN, "192.168.1.99") is None


def test_salida_vacia_devuelve_none():
    assert parse_arp("", "192.168.1.20") is None


def test_broadcast_devuelve_none():
    assert parse_arp(ARP_EN, "192.168.1.255") is None


def test_multicast_devuelve_none():
    assert parse_arp(ARP_EN, "224.0.0.22") is None


def test_ipv6_devuelve_none():
    assert parse_arp(ARP_EN, "::1") is None


def test_ip_no_valida_devuelve_none():
    assert parse_arp(ARP_EN, "testclient") is None
    assert parse_arp(ARP_EN, "") is None


def test_ip_con_espacios_devuelve_none():
    assert parse_arp(ARP_EN, " 192.168.1.20 ") is None


def test_ip_con_ceros_izquierda_devuelve_none():
    assert parse_arp(ARP_EN, "192.168.001.020") is None


# ---------------------------------------------------------------------------
# parse_arp: ambigüedad
# ---------------------------------------------------------------------------

def test_misma_ip_dos_macs_distintas_devuelve_none():
    output =(
        "Interface: 192.168.1.10 --- 0x5\n"
        "  192.168.1.50           aa-bb-cc-00-11-50     dynamic\n"
        "Interface: 192.168.1.20 --- 0x6\n"
        "  192.168.1.50           aa-bb-cc-00-11-51     dynamic\n"
    )
    assert parse_arp(output,"192.168.1.50") is None


def test_misma_ip_misma_mac_repetida_devuelve_mac():
    output =(
        "Interface: 192.168.1.10 --- 0x5\n"
        "  192.168.1.50           aa-bb-cc-00-11-50     dynamic\n"
        "Interface: 192.168.1.20 --- 0x6\n"
        "  192.168.1.50           aa-bb-cc-00-11-50     dynamic\n"
    )
    assert parse_arp(output,"192.168.1.50") == "AA:BB:CC:00:11:50"


# ---------------------------------------------------------------------------
# parse_arp: casos adversarios
# ---------------------------------------------------------------------------

def test_unicode_en_ip_no_coincide():
    output ="  ١٩٢.١٦٨.١.٢٠           aa-bb-cc-00-11-20     dynamic\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_unicode_en_mac_no_coincide():
    output ="  192.168.1.20           ａａ-ｂｂ-ｃｃ-００-１１-２０     dynamic\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_unicode_en_ip_argumento_devuelve_none():
    assert parse_arp(ARP_EN, "١٩٢.١٦٨.١.٢٠") is None


def test_formato_corrupto_un_campo_devuelve_none():
    output ="  192.168.1.20\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_formato_corrupto_ip_sin_mac_devuelve_none():
    output ="  192.168.1.20   dynamic\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_formato_corrupto_mac_de_5_bytes_devuelve_none():
    output ="  192.168.1.20           aa-bb-cc-00-11     dynamic\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_ip_192_168_1_256_devuelve_none():
    output ="  192.168.1.256           aa-bb-cc-00-11-20     dynamic\n"
    assert parse_arp(output,"192.168.1.20") is None


def test_tabulaciones_como_separador():
    output ="  192.168.1.20\taa-bb-cc-00-11-20\tdynamic\n"
    assert parse_arp(output,"192.168.1.20") == "AA:BB:CC:00:11:20"


def test_salida_de_1_mb_encuentra_entrada_al_final():
    junk = "x " * 500_000 + "\n"
    good_line = "  192.168.1.20           aa-bb-cc-00-11-20     dynamic\n"
    assert parse_arp(junk + good_line, "192.168.1.20") == "AA:BB:CC:00:11:20"


def test_ip_con_mac_invalida_devuelve_none():
    output =(
        "Interface: 192.168.1.10 --- 0x5\n"
        "  192.168.1.20           aa-bb-cc-00-11-20     dynamic\n"
        "  192.168.1.20           00-00-00-00-00-00     dynamic\n"
    )
    assert parse_arp(output,"192.168.1.20") is None


# ---------------------------------------------------------------------------
# parse_arp: TypeError
# ---------------------------------------------------------------------------

def test_parse_arp_tipo_ip_invalido():
    with pytest.raises(TypeError):
        parse_arp(ARP_EN, None)  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_arp(ARP_EN, b"192.168.1.20")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_arp(ARP_EN, 3232235796)  # type: ignore[arg-type]


def test_parse_arp_tipo_output_invalido():
    with pytest.raises(TypeError):
        parse_arp(None, "192.168.1.20")  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        parse_arp(b"", "192.168.1.20")  # type: ignore[arg-type]


def test_type_error_mensaje_no_incluye_valor():
    try:
        parse_arp(ARP_EN, 3232235796)  # type: ignore[arg-type]
    except TypeError as exc:
        assert "3232235796" not in str(exc)
    else:
        pytest.fail("No se lanzó TypeError")


# ---------------------------------------------------------------------------
# mac_lookup: run inyectado
# ---------------------------------------------------------------------------

def test_mac_lookup_con_run_inyectado():
    run = lambda: ARP_EN  # noqa: E731
    assert mac_lookup("192.168.1.20", run=run) == "AA:BB:CC:00:11:20"


def test_mac_lookup_con_file_not_found_devuelve_none():
    def run_raises_file_not_found():
        raise FileNotFoundError("arp no existe")

    assert mac_lookup("192.168.1.20", run=run_raises_file_not_found) is None


def test_mac_lookup_con_timeout_devuelve_none():
    def run_that_times_out():
        raise subprocess.TimeoutExpired("arp", 5)

    assert mac_lookup("192.168.1.20", run=run_that_times_out) is None


def test_mac_lookup_con_oserror_devuelve_none():
    def run_that_raises_oserror():
        raise OSError("error de red")

    assert mac_lookup("192.168.1.20", run=run_that_raises_oserror) is None


# ---------------------------------------------------------------------------
# _run_arp: comando correcto (monkeypatch, sin ejecutar arp de verdad)
# ---------------------------------------------------------------------------

def test_run_arp_usa_comando_correcto(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_run(cmd, *, capture_output, timeout, check):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["timeout"] = timeout
        captured["check"] = check
        class Result:
            stdout = b"salida falsa"
        return Result()

    monkeypatch.setattr("app.arp.subprocess.run", fake_run)
    assert _run_arp() == "salida falsa"

    assert captured["cmd"] == ["arp", "-a"]
    assert captured["capture_output"] is True
    assert captured["timeout"] == 5
    assert captured["check"] is False


def test_run_arp_cp850_espanol(monkeypatch: pytest.MonkeyPatch):
    def fake_run(cmd, *, capture_output, timeout, check):
        class Result:
            stdout = ARP_ES.encode("cp850")
        return Result()

    monkeypatch.setattr("app.arp.subprocess.run", fake_run)
    assert mac_lookup("192.168.1.30") == "AA:BB:CC:00:11:30"
