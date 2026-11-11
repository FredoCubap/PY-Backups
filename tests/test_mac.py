"""Tests de `normalize_mac`. (e2 1.2)

Solo MACs inventadas: `AA:BB:CC:DD:EE:FF` y `AA:BB:CC:00:11:22` son
valores de ejemplo, no equipos reales.
"""

import pytest

from app.mac import normalize_mac


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("aa-bb-cc-dd-ee-ff", "AA:BB:CC:DD:EE:FF"),
        ("AA:BB:CC:DD:EE:FF", "AA:BB:CC:DD:EE:FF"),
        ("aabb.ccdd.eeff", "AA:BB:CC:DD:EE:FF"),
        ("AABBCCDDEEFF", "AA:BB:CC:DD:EE:FF"),
        ("aa:bb:cc:00:11:22", "AA:BB:CC:00:11:22"),
        # Decisión documentada: los separadores pueden mezclarse.
        ("AA-BB.CC:DD:EE-FF", "AA:BB:CC:DD:EE:FF"),
    ],
)
def test_formatos_validos_dan_la_misma_mac_canonica(value, expected):
    assert normalize_mac(value) == expected


@pytest.mark.parametrize(
    "value",
    [
        "  aa:bb:cc:dd:ee:ff  ",
        "AA BB CC DD EE FF",
        "\taabb.ccdd.eeff\n",
    ],
)
def test_espacios_y_minusculas(value):
    assert normalize_mac(value) == "AA:BB:CC:DD:EE:FF"


@pytest.mark.parametrize(
    "value",
    [
        "",
        "   ",
        "AA:BB:CC:DD:EE",
        "AA:BB:CC:DD:EE:FF:00",
        "AA:BB:CC:DD:EE:GG",
        "AA:BB-CC:DD:EE",
        "AABBCCDDEEFG",
    ],
)
def test_valores_invalidos(value):
    with pytest.raises(ValueError):
        normalize_mac(value)


def test_rechaza_digitos_unicode():
    # "٣" es el dígito arábigo U+0663: `str.isdigit()` lo aceptaría.
    with pytest.raises(ValueError):
        normalize_mac("AA:BB:CC:DD:EE:٣F")


@pytest.mark.parametrize(
    "value",
    [
        "00:00:00:00:00:00",
        "FF:FF:FF:FF:FF:FF",
        "01:00:5E:00:00:01",
        "0100.5e00.0001",
    ],
)
def test_mac_que_no_corresponde_a_un_equipo_individual(value):
    with pytest.raises(ValueError):
        normalize_mac(value)


def test_acepta_mac_localmente_administrada():
    # El bit 0x02 (administrada localmente) no la convierte en multicast.
    assert normalize_mac("02:11:22:33:44:55") == "02:11:22:33:44:55"


def test_el_error_no_devuelve_la_mac_recibida():
    with pytest.raises(ValueError) as exc:
        normalize_mac("AA:BB:CC:DD:EE:GG")
    assert "AA:BB:CC:DD:EE:GG" not in str(exc.value)
