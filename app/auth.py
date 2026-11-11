"""Login del admin, sesión y rutas protegidas. (e1 2.3)

Decisiones de seguridad:
- Mismo mensaje y mismo coste si falla el usuario o la contraseña: con un
  usuario inexistente se verifica contra un hash ficticio.
- La auditoría nunca guarda lo que se escribió como usuario si no existe
  (la gente a veces escribe la contraseña en ese campo).
- La derivación scrypt corre en un hilo para no bloquear el servidor.
"""

import asyncio
from collections.abc import AsyncGenerator
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.models import AdminUser
from app.security import hash_password, verify_password
from app.web import templates

router = APIRouter()

GENERIC_ERROR = "Usuario o contraseña incorrectos."
MAX_PASSWORD_LENGTH = 1024  # más largo no es una contraseña: se rechaza sin derivar
UNKNOWN_ACTOR = "desconocido"


@lru_cache(maxsize=1)
def _dummy_hash() -> str:
    return hash_password("contraseña-ficticia-para-igualar-tiempos")


async def get_session(request: Request) -> AsyncGenerator[AsyncSession]:
    async with request.app.state.session_factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def require_admin(request: Request, session: SessionDep) -> AdminUser:
    """Exige sesión de admin; sin ella redirige a /login sin devolver datos."""
    admin_id = request.session.get("admin_id")
    admin = await session.get(AdminUser, admin_id) if isinstance(admin_id, int) else None
    if admin is None:
        request.session.clear()
        raise HTTPException(status_code=303, headers={"Location": "/login"})
    return admin


AdminDep = Annotated[AdminUser, Depends(require_admin)]


def _redirect(url: str) -> RedirectResponse:
    return RedirectResponse(url, status_code=303)


@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if request.session.get("admin_id"):
        return _redirect("/panel")
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    session: SessionDep,
    username: Annotated[str, Form()] = "",
    password: Annotated[str, Form()] = "",
):
    username = username.strip().lower()
    ip = request.client.host if request.client else None
    admin = (
        await session.scalar(select(AdminUser).where(AdminUser.username == username))
        if username
        else None
    )

    if len(password) > MAX_PASSWORD_LENGTH:
        valid = False
    else:
        stored = admin.password_hash if admin else _dummy_hash()
        valid = await asyncio.to_thread(verify_password, password, stored) and admin is not None

    if valid:
        request.session.clear()  # sesión nueva en cada login
        request.session["admin_id"] = admin.id
        await audit(session, actor=admin.username, action="login", ip=ip)
        await session.commit()
        return _redirect("/panel")

    await audit(
        session,
        actor=admin.username if admin else UNKNOWN_ACTOR,
        action="login",
        result="fail",
        ip=ip,
    )
    await session.commit()
    return templates.TemplateResponse(
        request, "login.html", {"error": GENERIC_ERROR}, status_code=401
    )


@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return _redirect("/login")


@router.get("/panel", response_class=HTMLResponse)
async def panel(request: Request, admin: AdminDep):
    return templates.TemplateResponse(request, "panel.html", {"username": admin.username})
