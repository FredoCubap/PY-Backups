"""Tests del hash y la verificación de contraseñas con scrypt. (e1 2.1)

Solo contraseñas inventadas, por ejemplo `clave-de-prueba-1`.
"""

import base64
import time

import pytest

from app.security import hash_password, verify_password

CLAVE = "clave-de-prueba-1"
OTRA_CLAVE = "clave-de-prueba-2"

# "ñ" compuesta (U+00F1) y descompuesta (n + tilde combinante U+0303).
CONTRASENA_COMPUESTA = "contrase\u00f1a"
CONTRASENA_DESCOMPUESTA = "contrase" + "n\u0303" + "a"


@pytest.fixture(scope="module")
def hashed():
    """Hash de una contraseña de prueba, compartido por los tests."""
    return hash_password(CLAVE)


def test_ida_y_vuelta():
    assert verify_password(CLAVE, hash_password(CLAVE)) is True


def test_contrasena_incorrecta(hashed):
    assert verify_password(OTRA_CLAVE, hashed) is False
    assert verify_password(CLAVE + " ", hashed) is False
    assert verify_password("", hashed) is False


def test_sal_distinta_en_cada_hash():
    primero = hash_password(CLAVE)
    segundo = hash_password(CLAVE)
    assert primero != segundo
    assert verify_password(CLAVE, primero) is True
    assert verify_password(CLAVE, segundo) is True


def test_formato_del_hash():
    stored = hash_password(CLAVE)
    assert stored.startswith("scrypt$32768$8$1$")
    assert CLAVE not in stored
    partes = stored.split("$")
    assert len(partes) == 6
    assert len(base64.b64decode(partes[4])) == 16
    assert len(base64.b64decode(partes[5])) == 32


def test_normalizacion_nfkc():
    # La ñ descompuesta y la compuesta verifican entre sí.
    stored = hash_password(CONTRASENA_COMPUESTA)
    assert verify_password(CONTRASENA_COMPUESTA, stored) is True
    assert verify_password(CONTRASENA_DESCOMPUESTA, stored) is True


def test_contrasena_vacia():
    with pytest.raises(ValueError):
        hash_password("")


def test_caracter_no_codificable_no_se_filtra_en_el_error():
    # Un sustituto suelto (U+D800) no se puede codificar en UTF-8; el error
    # de Python incluiría ese carácter y no debe llegar al mensaje.
    with pytest.raises(ValueError) as exc:
        hash_password("ab\ud800c")
    assert "\ud800" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert verify_password("ab\ud800c", hash_password(CLAVE)) is False


@pytest.mark.parametrize("stored", [None, b"scrypt$32768$8$1$c2FsdA==$aGFzaA==", 123])
def test_valor_guardado_que_no_es_texto(stored):
    assert verify_password(CLAVE, stored) is False


@pytest.mark.parametrize(
    "stored",
    [
        "",
        "scrypt",
        "scrypt$32768$8$1$c2FsdA==",
        "scrypt$32768$8$1$c2FsdA==$aGFzaA==$extra",
        "bcrypt$32768$8$1$c2FsdA==$aGFzaA==",
        "scrypt$abc$8$1$c2FsdA==$aGFzaA==",
        "scrypt$32768$xyz$1$c2FsdA==$aGFzaA==",
        "scrypt$32768$8$q$c2FsdA==$aGFzaA==",
        "scrypt$32768$8$1$!!!$aGFzaA==",
        "scrypt$32768$8$1$c2FsdA==$!!!",
    ],
)
def test_valor_guardado_mal_formado(stored):
    assert verify_password(CLAVE, stored) is False


@pytest.mark.parametrize(
    "stored",
    [
        "scrypt$2097152$8$1$c2FsdA==$aGFzaA==",  # n > 2**20
        "scrypt$3$8$1$c2FsdA==$aGFzaA==",  # n no es potencia de 2
        "scrypt$1$8$1$c2FsdA==$aGFzaA==",  # n < 2
        "scrypt$32768$17$1$c2FsdA==$aGFzaA==",  # r > 16
        "scrypt$32768$0$1$c2FsdA==$aGFzaA==",  # r < 1
        "scrypt$32768$8$5$c2FsdA==$aGFzaA==",  # p > 4
        "scrypt$32768$8$0$c2FsdA==$aGFzaA==",  # p < 1
    ],
)
def test_parametros_fuera_de_rango(stored):
    assert verify_password(CLAVE, stored) is False


def test_parametros_fuera_de_rango_no_se_calculan(monkeypatch):
    """Fuera de rango se devuelve False sin llamar a scrypt."""

    def _no_derivar(*args, **kwargs):
        raise AssertionError("no debía derivar")

    monkeypatch.setattr("app.security.hashlib.scrypt", _no_derivar)
    assert verify_password(CLAVE, "scrypt$2097152$8$1$c2FsdA==$aGFzaA==") is False
    assert verify_password(CLAVE, "scrypt$32768$17$1$c2FsdA==$aGFzaA==") is False
    assert verify_password(CLAVE, "scrypt$32768$8$5$c2FsdA==$aGFzaA==") is False


def test_parametros_fuera_de_rango_no_tardan(hashed):
    """El rechazo es mucho más rápido que una derivación real."""
    inicio = time.perf_counter()
    assert verify_password(CLAVE, hashed) is True
    coste_real = time.perf_counter() - inicio

    inicio = time.perf_counter()
    assert verify_password(CLAVE, "scrypt$2097152$8$1$c2FsdA==$aGFzaA==") is False
    coste_rechazo = time.perf_counter() - inicio

    assert coste_rechazo < coste_real / 2
