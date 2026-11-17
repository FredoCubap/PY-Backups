"""Códigos de alta de un solo uso. (e2 2.2)

El código son 128 bits aleatorios en base32 (sin distinguir mayúsculas y
sin 0/1/8, fácil de dictar y teclear), mostrado en grupos de 4. Solo se
guarda su SHA-256: el código es aleatorio, no necesita scrypt.
"""

import base64
import hashlib
import secrets
from datetime import datetime, timedelta

CODE_TTL = timedelta(hours=24)


def hash_code(value: str) -> str:
    """SHA-256 del código normalizado (sin guiones ni espacios, en mayúsculas)."""
    normalized = "".join(value.split()).replace("-", "").upper()
    return hashlib.sha256(normalized.encode()).hexdigest()


def new_code() -> tuple[str, str]:
    """Devuelve `(código para mostrar, hash para guardar)`."""
    raw = base64.b32encode(secrets.token_bytes(16)).decode().rstrip("=")
    display = "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))
    return display, hash_code(display)


def expiry(now: datetime) -> str:
    """Caducidad del código, en el mismo formato que `now_local()`."""
    return (now + CODE_TTL).isoformat(timespec="seconds")
