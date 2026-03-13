from pathlib import Path

from starlette.templating import Jinja2Templates

BASE_DIR = Path(__file__).parent.parent

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.globals["url_for"] = lambda name, **kwargs: f"/{name}/{kwargs.get('path', kwargs.get('filename', ''))}"


def static_url(filename: str):
    return f"/static/{filename}"


templates.env.globals["static_url"] = static_url
