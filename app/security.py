"""Hash y verificación de contraseñas del admin con scrypt. (e1 2.1)

Los parámetros y el formato de guardado los fija la ficha de la tarea, no se
cambian. El formato es `scrypt$<n>$<r>$<p>$<sal_b64>$<hash_b64>`.

Se usa solo la librería estándar: nada de bcrypt, argon2 ni passlib.
"""

import base64
import hashlib
import hmac
import secrets
import unicodedata

# Parámetros de derivación fijados por la ficha.
_ALGORITHM = "scrypt"
_N = 32768
_R = 8
_P = 1
_DKLEN = 32

# Bytes de sal por contraseña: distinta en cada llamada.
_SALT_BYTES = 16

# Con estos parámetros el límite por defecto de Python no alcanza y falla.
_MAXMEM = 64 * 1024 * 1024

# Topes para leer los parámetros de un hash guardado. Así un valor
# manipulado no puede pedir una derivación enorme. Fuera de rango se
# devuelve False sin calcular nada.
_MIN_N = 2
_MAX_N = 2**20
_MIN_R = 1
_MAX_R = 16
_MIN_P = 1
_MAX_P = 4


def _normalize(password: str) -> bytes:
    """Normaliza la contraseña a bytes con NFKC, para que una ñ compuesta y
    una descompuesta den el mismo resultado.
    """
    return unicodedata.normalize("NFKC", password).encode("utf-8")


def hash_password(password: str) -> str:
    """Devuelve el hash de la contraseña en formato
    `scrypt$<n>$<r>$<p>$<sal_b64>$<hash_b64>`.

    Lanza `ValueError` si la contraseña está vacía. El mensaje nunca
    incluye el valor recibido.
    """
    if not password:
        raise ValueError("La contraseña no puede estar vacía.")

    try:
        password_bytes = _normalize(password)
    except UnicodeEncodeError:
        # El mensaje original de Python incluiría el carácter recibido.
        raise ValueError("La contraseña contiene caracteres no válidos.") from None

    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password_bytes,
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
        maxmem=_MAXMEM,
    )
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(derived).decode("ascii")
    return f"{_ALGORITHM}${_N}${_R}${_P}${salt_b64}${hash_b64}"


def verify_password(password: str, stored: str) -> bool:
    """Comprueba la contraseña contra el hash guardado.

    Lee n, r, p y la sal del valor guardado, para poder subirlos más
    adelante sin romper los hashes viejos.

    Devuelve False, sin lanzar excepciones, si el valor guardado está mal
    formado o si sus parámetros quedan fuera de rango.
    """
    if not stored:
        return False

    parts = stored.split("$")
    if len(parts) != 6:
        return False
    algorithm, n_raw, r_raw, p_raw, salt_b64, hash_b64 = parts

    if algorithm != _ALGORITHM:
        return False

    try:
        n = int(n_raw)
        r = int(r_raw)
        p = int(p_raw)
    except ValueError:
        return False

    # Fuera de rango: se rechaza sin derivar nada.
    if n < _MIN_N or n > _MAX_N or (n & (n - 1)) != 0:
        return False
    if r < _MIN_R or r > _MAX_R:
        return False
    if p < _MIN_P or p > _MAX_P:
        return False

    try:
        salt = base64.b64decode(salt_b64, validate=True)
        expected = base64.b64decode(hash_b64, validate=True)
        derived = hashlib.scrypt(
            _normalize(password),
            salt=salt,
            n=n,
            r=r,
            p=p,
            dklen=_DKLEN,
            maxmem=_MAXMEM,
        )
    except (ValueError, MemoryError, OverflowError):
        return False

    return hmac.compare_digest(derived, expected)
