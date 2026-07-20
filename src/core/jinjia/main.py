from pathlib import Path

from fastapi.templating import Jinja2Templates
from jinja2 import ChoiceLoader, FileSystemLoader

BASE_DIR = Path(__file__).resolve().parents[2]

CORE_TEMPLATES = BASE_DIR / "core" / "templates"

APPS_DIR = BASE_DIR / "apps"


def discover_template_directories() -> list[str]:
    """
    Discover every feature template directory.

    Example:

        src/apps/auth/templates
        src/apps/chat/templates
        src/apps/website/templates
    """
    template_dirs: list[str] = []
    if APPS_DIR.exists():
        for app in APPS_DIR.iterdir():
            template_dir = app / "templates"
            if template_dir.exists() and template_dir.is_dir():
                template_dirs.append(str(template_dir))
    return template_dirs


loader = ChoiceLoader(
    [
        FileSystemLoader(discover_template_directories()),
        FileSystemLoader(str(CORE_TEMPLATES)),
    ]
)

templates = Jinja2Templates(directory=str(CORE_TEMPLATES))
templates.env.loader = loader
