from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="PYBACKUPS_", extra="ignore")

    # La base de datos vive fuera del repo (el repo es público).
    data_dir: Path = Path.home() / "PY-Backups-data"
    # Raíz de las copias en el disco externo; sin definir hasta montar el disco.
    backups_root: Path | None = None


settings = Settings()
