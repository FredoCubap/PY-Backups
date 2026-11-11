"""Plantillas HTML compartidas por las rutas. (e1 2.3)"""

from pathlib import Path

from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory=Path(__file__).parent / "templates")
