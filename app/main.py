"""Aplicación FastAPI. Se crea con `create_app()` para poder usar bases temporales en tests.

Arranque: `uvicorn app.main:create_app --factory`
"""

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware

from app import __version__, auth
from app.config import Settings, load_or_create_secret, prepare_data_dir
from app.config import settings as default_settings
from app.database import make_engine, make_session_factory
from app.web import templates

SESSION_MAX_AGE = 8 * 60 * 60  # 8 horas


@asynccontextmanager
async def _lifespan(app: FastAPI):
    yield
    await app.state.engine.dispose()


def create_app(settings: Settings = default_settings) -> FastAPI:
    data_dir = prepare_data_dir(settings.data_dir)
    app = FastAPI(title="PY-Backups", version=__version__, lifespan=_lifespan)

    app.state.engine = make_engine(settings.database_url)
    app.state.session_factory = make_session_factory(app.state.engine)

    # HTTP en la LAN: la cookie no puede ser `secure`. Ceiling: sin TLS, quien
    # espíe la red local podría verla; se resuelve poniendo HTTPS delante.
    app.add_middleware(
        SessionMiddleware,
        secret_key=load_or_create_secret(data_dir),
        session_cookie="pybackups_session",
        max_age=SESSION_MAX_AGE,
        same_site="lax",
        https_only=False,
    )
    app.include_router(auth.router)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "version": __version__, "timestamp": datetime.now(UTC).isoformat()}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return templates.TemplateResponse(request, "index.html", {"title": "PY-Backups"})

    return app
