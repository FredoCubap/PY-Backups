"""Modelos de la base de datos. (e1 1.2)"""

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(String(32))


class AuditLog(Base):
    """Registro de solo-añadir: un trigger impide UPDATE y DELETE."""

    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(primary_key=True)
    ts: Mapped[str] = mapped_column(String(32))  # hora local con desfase (ISO 8601)
    actor: Mapped[str] = mapped_column(String(64))
    action: Mapped[str] = mapped_column(String(64))
    target: Mapped[str | None] = mapped_column(String(255))
    result: Mapped[str] = mapped_column(String(16))
    ip: Mapped[str | None] = mapped_column(String(45))


class Worker(Base):
    """Trabajador. El usuario es único sin distinguir mayúsculas. (e2 1.1)"""

    __tablename__ = "workers"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64, collation="NOCASE"), unique=True)
    created_at: Mapped[str] = mapped_column(String(32))


class Device(Base):
    """PC de un trabajador. Guarda solo el SHA-256 de su token."""

    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"))
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[str] = mapped_column(String(32))
    revoked_at: Mapped[str | None] = mapped_column(String(32))


class DeviceMac(Base):
    """MAC de una PC (varias por PC); cada MAC pertenece a una sola PC."""

    __tablename__ = "device_macs"

    id: Mapped[int] = mapped_column(primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"))
    mac: Mapped[str] = mapped_column(String(17), unique=True)


class EnrollCode(Base):
    """Código de alta de un solo uso. Guarda solo su hash."""

    __tablename__ = "enroll_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    worker_id: Mapped[int] = mapped_column(ForeignKey("workers.id"))
    code_hash: Mapped[str] = mapped_column(String(64), unique=True)
    created_at: Mapped[str] = mapped_column(String(32))
    expires_at: Mapped[str] = mapped_column(String(32))
    used_at: Mapped[str | None] = mapped_column(String(32))
