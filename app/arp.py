"""Búsqueda de MAC por ARP sobre la tabla ARP de Windows. (e2 1.3)

Lee la salida de `arp -a` y devuelve la MAC canónica de una IP dada.
La MAC devuelta es la prueba de identidad del equipo: ante cualquier duda
devuelve None, nunca adivina.
"""

import ipaddress
import subprocess
from collections.abc import Callable

from app.mac import normalize_mac


def _run_arp() -> str:
    """Ejecuta `arp -a` y devuelve su salida como str.

    Siempre devuelve str. Deja propagar FileNotFoundError,
    subprocess.TimeoutExpired y OSError; quien llama (mac_lookup) los
    captura y devuelve None.
    """
    result = subprocess.run(
        ["arp", "-a"],
        capture_output=True,
        timeout=5,
        check=False,
    )
    return result.stdout.decode("ascii", errors="replace")


def parse_arp(output: str, ip: str) -> str | None:
    """Devuelve la MAC canónica de `ip` parseando la salida de `arp -a`.

    Función pura. Ignora cabeceras, líneas de interfaz, vacías y basura
    sin depender del idioma de Windows. Exige IPv4 explícitamente: IPv6
    devuelve None.

    Lanza TypeError si `ip` u `output` no son str.
    Devuelve None si no hay entrada, la IP no es IPv4, la MAC no es de un
    equipo, o la misma IP aparece con MACs distintas (ambigüedad).
    Si una línea tiene la IP buscada pero una MAC inválida, hay evidencia
    contradictoria y devuelve None.
    """
    if not isinstance(output, str):
        raise TypeError("output must be str")
    if not isinstance(ip, str):
        raise TypeError("ip must be str")

    try:
        target = ipaddress.ip_address(ip)
    except ValueError:
        return None
    if not isinstance(target, ipaddress.IPv4Address):
        return None

    found_macs: set[str] = set()

    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 2:
            continue
        candidate_ip = fields[0]
        candidate_mac = fields[1]
        try:
            line_ip = ipaddress.ip_address(candidate_ip)
        except ValueError:
            continue
        if not isinstance(line_ip, ipaddress.IPv4Address):
            continue
        if line_ip != target:
            continue
        # Es la IP buscada: evidencia directa.
        try:
            canonical = normalize_mac(candidate_mac)
        except ValueError:
            # MAC inválida para la IP buscada: evidencia contradictoria.
            return None
        found_macs.add(canonical)

    if len(found_macs) == 0:
        return None
    if len(found_macs) > 1:
        # MACs distintas para la misma IP: ambiguo.
        return None
    return found_macs.pop()


def mac_lookup(ip: str, run: Callable[[], str] = _run_arp) -> str | None:
    """Devuelve la MAC del equipo con IP `ip` leyendo la tabla ARP.

    Llama a `run()` (por defecto `_run_arp`) y pasa el resultado a
    `parse_arp`. Si `run` falla (arp no existe, timeout, OSError),
    devuelve None.
    """
    try:
        output = run()
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    return parse_arp(output, ip)
