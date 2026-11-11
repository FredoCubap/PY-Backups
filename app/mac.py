"""Normalización de direcciones MAC para el registro de PCs. (e2 1.2)

La forma canónica del proyecto es `AA:BB:CC:DD:EE:FF`: mayúsculas y dos
puntos. Una MAC mal normalizada rompe el enlace entre equipo y registro,
por eso la función es estricta y falla en vez de adivinar.
"""

import string

# Solo dígitos hexadecimales ASCII. `str.isdigit()` y `str.isalnum()` aceptan
# dígitos Unicode (por ejemplo "٣"), que no son MACs válidas.
_HEX_DIGITS = frozenset(string.hexdigits)

# Dígitos hexadecimales con el bit menos significativo en 1. El bit de
# multicast es el último del primer byte, es decir, el de su segundo dígito.
_ODD_HEX_DIGITS = frozenset("13579bdfBDF")

# Separadores admitidos entre los bytes.
_SEPARATORS = frozenset(":-.")

_ZERO_MAC = "00:00:00:00:00:00"
_BROADCAST_MAC = "FF:FF:FF:FF:FF:FF"


def normalize_mac(value: str) -> str:
    """Devuelve la MAC en forma canónica `AA:BB:CC:DD:EE:FF`.

    Acepta los formatos `aa-bb-cc-dd-ee-ff`, `AA:BB:CC:DD:EE:FF`,
    `aabb.ccdd.eeff` y `AABBCCDDEEFF`, con espacios alrededor o dentro.
    Los separadores pueden mezclarse: se quitan todos y el resto debe
    quedar en 12 dígitos hexadecimales.

    Lanza `ValueError` si no son 12 dígitos hexadecimales, o si la MAC no
    corresponde a un equipo individual (todos ceros, broadcast o multicast).
    """
    digits = "".join(ch for ch in value if ch not in _SEPARATORS and not ch.isspace())
    if len(digits) != 12:
        raise ValueError("La MAC debe tener 12 dígitos hexadecimales.")
    for ch in digits:
        if ch not in _HEX_DIGITS:
            raise ValueError("La MAC solo admite dígitos hexadecimales (0-9, A-F).")

    octets = [a.upper() + b.upper() for a, b in zip(digits[::2], digits[1::2], strict=True)]
    canonical = ":".join(octets)
    if canonical == _ZERO_MAC:
        raise ValueError("La MAC de todos ceros no corresponde a un equipo.")
    if canonical == _BROADCAST_MAC:
        raise ValueError("La MAC de broadcast no corresponde a un equipo.")
    if digits[1] in _ODD_HEX_DIGITS:
        raise ValueError("La MAC multicast no corresponde a un equipo.")
    return canonical
