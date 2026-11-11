"""Registro de auditoría. (e1 3.1)"""

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog


def now_local() -> str:
    """Hora local del servidor con desfase, p. ej. `2026-11-11T16:03:51-05:00`."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


async def audit(
    session: AsyncSession,
    actor: str,
    action: str,
    target: str | None = None,
    result: str = "ok",
    ip: str | None = None,
) -> None:
    """Añade una entrada a la sesión; quien llama hace el `commit`.

    Nunca recibe contraseñas ni tokens: solo quién, qué, sobre qué y el resultado.
    """
    session.add(
        AuditLog(ts=now_local(), actor=actor, action=action, target=target, result=result, ip=ip)
    )
