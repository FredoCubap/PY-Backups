"""Comandos de administración: `python -m app.cli crear-admin`. (e1 2.2)

La contraseña se pide por teclado: nunca por argumento, variable de entorno
ni archivo, para que no quede en el historial ni en el repo.
"""

import argparse
import asyncio
import getpass
import sys

from app.admin import AdminError, create_admin
from app.config import settings
from app.database import make_engine, make_session_factory


async def _crear(username: str, password: str) -> str:
    engine = make_engine(settings.database_url)
    try:
        return await create_admin(make_session_factory(engine), username, password)
    finally:
        await engine.dispose()


def _crear_admin(username: str | None) -> int:
    # No conectar si la base no existe: SQLite crearía un archivo vacío.
    if not settings.database_path.exists():
        print("La base de datos no existe. Primero ejecuta: alembic upgrade head", file=sys.stderr)
        return 1
    username = username or input("Usuario: ")
    password = getpass.getpass("Contraseña: ")
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden.", file=sys.stderr)
        return 1
    try:
        creado = asyncio.run(_crear(username, password))
    except AdminError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(f"Admin '{creado}' creado.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="comando", required=True)
    crear = sub.add_parser(
        "crear-admin", help="Crea el administrador (pide la contraseña por teclado)"
    )
    crear.add_argument("--usuario", help="Nombre de usuario (si falta, se pregunta)")
    args = parser.parse_args(argv)
    return _crear_admin(args.usuario)


if __name__ == "__main__":
    sys.exit(main())
