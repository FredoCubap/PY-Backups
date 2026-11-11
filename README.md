# PY-Backups

Sistema de copias de seguridad para la oficina: servidor web en la PC del admin, script en cada PC de los trabajadores. Diseño en [`docs/flujo.md`](docs/flujo.md).

> **Repo público.** Solo código y documentación. Usuarios, MACs, tokens, bases de datos y copias nunca se suben (ver `.gitignore`). Los datos de prueba son inventados.

## Arranque (desarrollo)

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-dev.txt
copy .env.example .env        # y ajusta los valores
.venvScriptslembic upgrade head   # crea la base en PYBACKUPS_DATA_DIR (fuera del repo)
.venvScriptspython -m app.cli crear-admin --usuario tu-usuario   # pide la contraseña por teclado
.venv\Scripts\python -m uvicorn app.main:create_app --factory --reload
```

## Versionado

[SemVer](https://semver.org/lang/es/) `MAJOR.MINOR.PATCH`. La versión vive en un solo lugar, `app/__init__.py` (`__version__`), y se refleja en `/health`, el `CHANGELOG.md` y la etiqueta de git `vX.Y.Z`.

- **PATCH:** corrección de un error, sin cambiar lo que hace.
- **MINOR:** funcionalidad nueva compatible. Mientras sea `0.x`, cada etapa de `docs/vision.md` completada sube un MINOR: e1 → `0.2.0`, e2 → `0.3.0`… e8 → `0.9.0`.
- **MAJOR:** cambio incompatible (por ejemplo, del protocolo entre el servidor y el script de las PCs). `1.0.0` será la primera versión en uso real en la oficina.

Cada versión: actualizar `__version__`, mover lo de "Sin publicar" a su sección en el `CHANGELOG.md` y crear la etiqueta.

Commits en español con prefijo: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

## Tests y lint

```powershell
.venv\Scripts\python -m pytest
.venv\Scripts\python -m ruff check .
```
