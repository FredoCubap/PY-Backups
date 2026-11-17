"""La migración 0002 crea las tablas y el usuario es único sin distinguir mayúsculas. (e2 1.1)"""

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import Device, DeviceMac, Worker
from tests.conftest import run_with_session


def test_usuario_unico_sin_mayusculas(db_url):
    async def go(sf):
        async with sf() as s:
            s.add(Worker(username="Trabajador1", created_at="x"))
            await s.commit()
            s.add(Worker(username="TRABAJADOR1", created_at="x"))
            with pytest.raises(IntegrityError):
                await s.commit()

    run_with_session(db_url, go)


def test_mac_unica(db_url):
    async def go(sf):
        async with sf() as s:
            w = Worker(username="trabajador1", created_at="x")
            s.add(w)
            await s.flush()
            d1, d2 = (Device(worker_id=w.id, token_hash=h, created_at="x", expires_at="x")
                      for h in ("a" * 64, "b" * 64))
            s.add_all([d1, d2])
            await s.flush()
            s.add_all([DeviceMac(device_id=d1.id, mac="AA:BB:CC:00:11:22"),
                       DeviceMac(device_id=d2.id, mac="AA:BB:CC:00:11:22")])
            with pytest.raises(IntegrityError):
                await s.commit()

    run_with_session(db_url, go)
