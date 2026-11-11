# Changelog

Formato [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado [SemVer](https://semver.org/lang/es/) (`MAJOR.MINOR.PATCH`).

## [Sin publicar]

## [0.2.0] - 2026-11-11

Etapa e1 (cimientos): base de datos y acceso del admin.

### Agregado

- Base SQLite con SQLAlchemy y Alembic (`migrations/`), fuera del repo. La app se niega a usar una carpeta de datos dentro de un repositorio git.
- Auditoría de solo-añadir (triggers contra UPDATE y DELETE) con hora local y desfase.
- Hash de contraseñas con scrypt, normalización NFKC y comparación en tiempo constante.
- CLI `python -m app.cli crear-admin` (la contraseña se pide por teclado).
- Login, logout y sesión firmada (`HttpOnly`, `SameSite=Lax`, 8 h) con `/panel` protegido.
- Bloqueo de 5 minutos tras 5 intentos fallidos (por usuario tecleado e IP).
- `normalize_mac()` para direcciones MAC (adelanto de e2).

### Cambiado

- La app se crea con `create_app()`: arranque con `uvicorn app.main:create_app --factory`.
- `/` redirige a `/login` o `/panel`; se elimina la página del esqueleto.

## [0.1.0] - 2026-11-11

### Agregado

- Esqueleto del servidor: FastAPI con `/health` (incluye la versión) y una página de inicio.
- Documentación: visión (`docs/vision.md`) y flujo (`docs/flujo.md`).
- `.gitignore` y `.env.example` pensados para repo público.
