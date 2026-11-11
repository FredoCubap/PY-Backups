"""Alta de administradores. (e1 2.2)"""

import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.audit import audit, now_local
from app.models import AdminUser
from app.security import hash_password

MIN_PASSWORD_LENGTH = 10
_USERNAME_RE = re.compile(r"[a-z0-9._-]{3,32}")


class AdminError(ValueError):
    """Error de validación al crear un admin. Nunca incluye la contraseña."""


async def create_admin(
    session_factory: async_sessionmaker[AsyncSession], username: str, password: str
) -> str:
    """Crea un admin y deja constancia en la auditoría. Devuelve el usuario normalizado.

    El usuario se guarda en minúsculas. La contraseña solo se guarda como hash.
    """
    username = username.strip().lower()
    if not _USERNAME_RE.fullmatch(username):
        raise AdminError("El usuario debe tener de 3 a 32 caracteres: letras, números, . _ -")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AdminError(f"La contraseña debe tener al menos {MIN_PASSWORD_LENGTH} caracteres.")
    try:
        password_hash = hash_password(password)
    except ValueError as exc:  # p. ej. caracteres que no se pueden codificar
        raise AdminError(str(exc)) from None

    async with session_factory() as session:
        if await session.scalar(select(AdminUser.id).where(AdminUser.username == username)):
            raise AdminError("Ese usuario ya existe.")
        session.add(
            AdminUser(username=username, password_hash=password_hash, created_at=now_local())
        )
        await audit(session, actor="cli", action="admin-created", target=username)
        await session.commit()
    return username
