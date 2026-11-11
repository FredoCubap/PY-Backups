"""Bloqueo temporal tras intentos de login fallidos. (e1 2.4)

Clave: (usuario tecleado, IP). Se usa lo tecleado aunque el usuario no exista,
para que el bloqueo no delate qué usuarios existen. Solo vive en memoria.

# ponytail: contador en memoria, se reinicia al reiniciar el servidor y no
# suma intentos repartidos entre muchas IPs; subir a la base si hace falta.
"""

import time
from collections.abc import Callable

MAX_ATTEMPTS = 5
LOCK_SECONDS = 300  # 5 minutos
MAX_KEYS = 10_000  # tope de memoria ante usuarios inventados en masa


class LoginLimiter:
    def __init__(
        self,
        max_attempts: int = MAX_ATTEMPTS,
        lock_seconds: float = LOCK_SECONDS,
        max_keys: int = MAX_KEYS,
        now: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_attempts = max_attempts
        self.lock_seconds = lock_seconds
        self.max_keys = max_keys
        self._now = now
        # clave -> [fallos seguidos, hora del último fallo, bloqueado hasta]
        self._entries: dict[tuple[str, str | None], list[float]] = {}

    def blocked_for(self, key: tuple[str, str | None]) -> float:
        """Segundos que faltan para poder reintentar (0 si no está bloqueado)."""
        entry = self._entries.get(key)
        if entry is None:
            return 0.0
        return max(0.0, entry[2] - self._now())

    def register_failure(self, key: tuple[str, str | None]) -> bool:
        """Anota un fallo. Devuelve True si con este fallo empieza el bloqueo."""
        now = self._now()
        entry = self._entries.get(key)
        if entry is None or now - entry[1] > self.lock_seconds:
            entry = self._entries[key] = [0, now, 0.0]  # los fallos viejos no suman
        entry[0] += 1
        entry[1] = now
        locked_now = entry[0] >= self.max_attempts and entry[2] <= now
        if locked_now:
            entry[2] = now + self.lock_seconds
        self._prune()
        return locked_now

    def reset(self, key: tuple[str, str | None]) -> None:
        self._entries.pop(key, None)

    def _prune(self) -> None:
        if len(self._entries) <= self.max_keys:
            return
        now = self._now()
        vivas = {
            k: e
            for k, e in self._entries.items()
            if e[2] > now or now - e[1] <= self.lock_seconds  # bloqueada o con fallos recientes
        }
        if len(vivas) > self.max_keys:  # todo sigue vigente: se descartan las más antiguas
            ordenadas = sorted(vivas.items(), key=lambda kv: kv[1][1])
            vivas = dict(ordenadas[len(vivas) - self.max_keys :])
        self._entries = vivas
