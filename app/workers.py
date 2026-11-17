"""Trabajadores: listado, alta (e2 2.1) y código de alta de su PC (e2 2.2).

El usuario se guarda en minúsculas y la columna es NOCASE: dos nombres que
solo difieren en mayúsculas chocan con la restricción única de la base, que
es la que decide (sin consultar antes, para no tener carrera entre dos altas).
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.admin import USERNAME_ERROR, USERNAME_RE
from app.audit import audit, now_local
from app.auth import AdminDep, SessionDep
from app.enroll import expiry, new_code
from app.models import EnrollCode, Worker
from app.web import templates

router = APIRouter()

DUPLICATE_ERROR = "Ese usuario ya existe."


async def _page(
    request: Request, session: AsyncSession, error: str | None = None, status: int = 200
):
    workers = (await session.scalars(select(Worker).order_by(Worker.username))).all()
    return templates.TemplateResponse(
        request, "workers.html", {"workers": workers, "error": error}, status_code=status
    )


@router.get("/workers", response_class=HTMLResponse)
async def list_workers(request: Request, session: SessionDep, admin: AdminDep):
    return await _page(request, session)


@router.post("/workers", response_class=HTMLResponse)
async def create_worker(
    request: Request,
    session: SessionDep,
    admin: AdminDep,
    username: Annotated[str, Form()] = "",
):
    username = username.strip().lower()
    if not USERNAME_RE.fullmatch(username):
        return await _page(request, session, USERNAME_ERROR, 400)

    # Se lee antes del rollback: después el objeto queda expirado y leerlo
    # en async lanzaría MissingGreenlet.
    actor = admin.username
    ip = request.client.host if request.client else None

    session.add(Worker(username=username, created_at=now_local()))
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        await audit(session, actor=actor, action="worker-created", target=username,
                    result="fail", ip=ip)
        await session.commit()
        return await _page(request, session, DUPLICATE_ERROR, 409)

    await audit(session, actor=actor, action="worker-created", target=username, ip=ip)
    await session.commit()
    return RedirectResponse("/workers", status_code=303)


@router.post("/workers/{worker_id}/enroll-code", response_class=HTMLResponse)
async def create_enroll_code(
    request: Request, worker_id: int, session: SessionDep, admin: AdminDep
):
    """Genera un código de alta y lo muestra una sola vez. (e2 2.2)"""
    worker = await session.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404)

    code, code_hash = new_code()
    now = datetime.now().astimezone()
    expires_at = expiry(now)
    session.add(
        EnrollCode(
            worker_id=worker.id,
            code_hash=code_hash,
            created_at=now.isoformat(timespec="seconds"),
            expires_at=expires_at,
        )
    )
    ip = request.client.host if request.client else None
    await audit(session, actor=admin.username, action="enroll-code-created",
                target=worker.username, ip=ip)
    await session.commit()
    return templates.TemplateResponse(
        request,
        "enroll_code.html",
        {"worker": worker.username, "code": code, "expires_at": expires_at},
        headers={"Cache-Control": "no-store"},
    )
