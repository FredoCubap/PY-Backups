import secrets
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PYBACKUPS_", extra="ignore")

    # La base de datos vive fuera del repo (el repo es público).
    data_dir: Path = Path.home() / "PY-Backups-data"
    # Raíz de las copias en el disco externo; sin definir hasta montar el disco.
    backups_root: Path | None = None

    @property
    def database_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def database_url(self) -> str:
        return f"sqlite+aiosqlite:///{self.database_path.as_posix()}"


settings = Settings()


def prepare_data_dir(data_dir: Path) -> Path:
    """Crea `data_dir` si falta y se niega a usarla dentro de un repo git. (e1 1.1)

    El repo es público: si la base cayera dentro de un árbol git, un
    `git add .` podría subir datos reales.
    """
    path = data_dir.expanduser().resolve()
    for folder in (path, *path.parents):
        if (folder / ".git").exists():
            raise RuntimeError(
                "PYBACKUPS_DATA_DIR no puede estar dentro de un repositorio git; "
                "usa una carpeta fuera de cualquier repo."
            )
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_or_create_secret(data_dir: Path) -> str:
    """Clave para firmar las cookies de sesión. (e1 2.3)

    Se genera la primera vez y se guarda en `data_dir`, nunca en el repo.
    Si se borra, las sesiones abiertas se invalidan y se genera otra.
    """
    key_file = data_dir / "session.key"
    if key_file.exists():
        key = key_file.read_text(encoding="ascii").strip()
        if len(key) >= 64:
            return key
    key = secrets.token_hex(32)
    key_file.write_text(key, encoding="ascii")
    return key
