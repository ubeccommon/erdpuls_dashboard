"""
Per-initiative public landing pages  (/{slug}).

Each PUBLISHED, has_page initiative gets its own page — the generic equivalent
of the Müllrose reference page at /muellrose. Anything that isn't a live
initiative returns 404.

Routing safety: this router owns a catch-all /{slug}, so app.main includes it
DEAD LAST (after api/web/auth/admin). Because Starlette matches routes in
include order, every explicit route in every other router is matched first —
/login, /about, /admin/..., /muellrose, etc. are never shadowed.

The page body is the initiative's data-folder README.md (created on approval),
rendered as Markdown; identity/status/blurb come from the initiatives row
(autoescaped by Jinja).
"""
import logging

import markdown
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from ..database import get_db
from ..auth import get_current_user_optional
from ..initiatives import get_initiative, initiative_data_path

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory="templates")


def _get_lang(request: Request) -> str:
    return request.cookies.get("lang", "en")


def _read_initiative_readme(slug: str) -> str:
    """Render the initiative's data-folder README.md to HTML, if present.

    Path is resolved via initiative_data_path (slug is re-slugified there), so
    it stays inside the configured external data dir — no traversal.
    """
    readme = initiative_data_path(slug) / "README.md"
    try:
        if readme.is_file():
            return markdown.markdown(
                readme.read_text(encoding="utf-8"),
                extensions=["extra", "sane_lists"],
            )
    except Exception as e:
        logger.warning("could not render README for initiative %s: %s", slug, e)
    return ""


@router.get("/{slug}", response_class=HTMLResponse)
def initiative_page(slug: str, request: Request, db: Session = Depends(get_db)):
    """Public landing page for a single published initiative."""
    initiative = get_initiative(db, slug)
    if not initiative or not initiative.is_published or not initiative.has_page:
        raise HTTPException(status_code=404)

    lang = _get_lang(request)
    user = get_current_user_optional(request, db)
    body_html = _read_initiative_readme(slug)

    return templates.TemplateResponse(
        "initiative.html",
        {
            "request": request,
            "lang": lang,
            "user": user,
            "initiative": initiative,
            "body_html": body_html,
        },
    )
