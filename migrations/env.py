"""Entorno de Alembic (síncrono: las migraciones no necesitan async). (e1 1.2)"""

from alembic import context
from sqlalchemy import create_engine

import app.models  # noqa: F401 -- registra los modelos en Base.metadata
from app.config import prepare_data_dir, settings
from app.database import Base

config = context.config
url = config.get_main_option("sqlalchemy.url")
if not url:
    # Uso normal: la base de la app, en su carpeta de datos fuera del repo.
    prepare_data_dir(settings.data_dir)
    url = settings.database_url
url = url.replace("+aiosqlite", "")  # las migraciones usan el driver síncrono

engine = create_engine(url)
with engine.connect() as connection:
    context.configure(connection=connection, target_metadata=Base.metadata)
    with context.begin_transaction():
        context.run_migrations()
engine.dispose()
