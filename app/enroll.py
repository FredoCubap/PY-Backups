"""Códigos de alta de un solo uso (e2 2.2) y su canje por una PC (e2 2.3).

El código son 128 bits aleatorios en base32 (sin distinguir mayúsculas y
sin 0/1/8, fácil de dictar y teclear), mostrado en grupos de 4. El token de
la PC son 256 bits. De ambos solo se guarda el SHA-256: son aleatorios, no
necesitan scrypt.

Canje: la MAC que prueba la identidad la resuelve el servidor por ARP; las
MACs que declara la PC solo sirven para comprobar que la de la ARP está
entre ellas y para guardarlas todas (spec "Server-side MAC resolution").
"""

import asyncio
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.audit import audit
from app.auth import SessionDep
from app.mac import normalize_mac
from app.models import Device, DeviceMac, EnrollCode, Worker

CODE_TTL = timedelta(hours=24)
TOKEN_TTL = timedelta(days=365)
MAX_MACS = 16  # una PC con más interfaces que esto no es una PC de oficina

BAD_CODE = "Código no válido, ya usado o caducado."
NO_ARP = "No se pudo verificar el equipo."
MAC_MISMATCH = "El equipo no coincide con las MAC declaradas."
MAC_TAKEN = "Alguna de las MAC ya pertenece a otra PC."
BAD_MAC = "Alguna de las MAC no es válida."

router = APIRouter()


def hash_code(value: str) -> str:
    """SHA-256 del código normalizado (sin guiones ni espacios, en mayúsculas)."""
    normalized = "".join(value.split()).replace("-", "").upper()
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def new_code() -> tuple[str, str]:
    """Devuelve `(código para mostrar, hash para guardar)`."""
    raw = base64.b32encode(secrets.token_bytes(16)).decode().rstrip("=")
    display = "-".join(raw[i : i + 4] for i in range(0, len(raw), 4))
    return display, hash_code(display)


def expiry(now: datetime, ttl: timedelta = CODE_TTL) -> str:
    """Caducidad, en el mismo formato que `now_local()`."""
    return (now + ttl).isoformat(timespec="seconds")


class RedeemRequest(BaseModel):
    code: Annotated[str, Field(max_length=64)]
    macs: Annotated[list[Annotated[str, Field(max_length=64)]], Field(min_length=1,
                                                                     max_length=MAX_MACS)]


@router.post("/enroll/redeem")
async def redeem(request: Request, body: RedeemRequest, session: SessionDep):
    """Canjea un código de alta: crea la PC y devuelve su token una sola vez."""
    ip = request.client.host if request.client else None
    try:
        macs = sorted({normalize_mac(m) for m in body.macs})
    except ValueError:
        raise HTTPException(status_code=422, detail=BAD_MAC) from None

    now = datetime.now().astimezone()
    enroll = await session.scalar(
        select(EnrollCode).where(EnrollCode.code_hash == hash_code(body.code))
    )
    worker = await session.get(Worker, enroll.worker_id) if enroll else None
    target = worker.username if worker else None  # se lee antes de cualquier rollback

    # ponytail: cada intento fallido se audita y no hay límite de intentos;
    # el código tiene 128 bits (no se adivina), pero un equipo de la LAN
    # podría inflar la auditoría. Límite por IP si llega a pasar.
    async def reject(status: int, result: str, detail: str):
        await session.rollback()
        await audit(session, actor="pc", action="pc-enroll", target=target, result=result, ip=ip)
        await session.commit()
        raise HTTPException(status_code=status, detail=detail)

    if enroll is None or enroll.used_at is not None or datetime.fromisoformat(
        enroll.expires_at
    ) <= now:
        await reject(403, "bad-code", BAD_CODE)

    # Sin IP no hay ARP. `resolve_mac` hace ping y lee la ARP: va en un hilo.
    arp_mac = await asyncio.to_thread(request.app.state.resolve_mac, ip) if ip else None
    if arp_mac is None:
        await reject(403, "no-arp", NO_ARP)
    if arp_mac not in macs:
        await reject(403, "mac-mismatch", MAC_MISMATCH)

    # Se marca usado solo si nadie lo marcó antes: de dos canjes simultáneos
    # del mismo código gana uno.
    now_iso = now.isoformat(timespec="seconds")
    claimed = await session.execute(
        update(EnrollCode)
        .where(EnrollCode.id == enroll.id, EnrollCode.used_at.is_(None))
        .values(used_at=now_iso)
    )
    if claimed.rowcount != 1:
        await reject(403, "bad-code", BAD_CODE)

    token = secrets.token_urlsafe(32)  # 256 bits
    expires_at = expiry(now, TOKEN_TTL)
    device = Device(worker_id=enroll.worker_id, token_hash=hash_token(token),
                    created_at=now_iso, expires_at=expires_at)
    session.add(device)
    try:
        await session.flush()
        session.add_all(DeviceMac(device_id=device.id, mac=m) for m in macs)
        await session.flush()
    except IntegrityError:
        # Una MAC ya es de otra PC: se deshace todo, también el uso del código.
        await reject(409, "mac-taken", MAC_TAKEN)

    await audit(session, actor="pc", action="pc-enroll", target=target, ip=ip)
    await session.commit()
    return JSONResponse(
        {"token": token, "expires_at": expires_at}, headers={"Cache-Control": "no-store"}
    )
