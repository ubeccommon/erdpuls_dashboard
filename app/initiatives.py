"""
Erdpuls — initiatives directory (data access + registration helpers).

Backs the network landing (`/`, templates/network.html) from the
`erdpuls_threshold.initiatives` table, and supports the admin
"register an initiative" flow (/admin/initiatives).

Deploy-model note: dashboard-created per-initiative folders are written to an
external, gitignored data directory (settings.initiatives_data_dir, e.g.
/srv/ubec/erdpuls-data/initiatives/<slug>/), NEVER inside the version-controlled
repo tree. Curated developer docs stay in documents/initiatives/ in the repo.
This keeps runtime writes entirely out of git (deploy-by-pull safe).
"""
import os
import re
import shutil
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from .config import get_settings
from .models import Initiative

SUPPORTED_LANGS = ("en", "de", "pl", "uk")

SLUG_RE = re.compile(r"^[a-z0-9-]+$")

# Slugs that would collide with existing/likely app routes — refuse these so a
# dashboard-created initiative can never shadow a real page.
RESERVED_SLUGS = {
    "muellrose", "about", "model", "offering", "offerings", "library", "admin",
    "login", "logout", "register", "dashboard", "fund", "privacy", "legal",
    "set-lang", "static", "health", "create-offering", "api", "contribute",
    "engage", "participate",
}

# Path to the docs template inside the repo (relative to the app working dir).
_TEMPLATE_README = Path("documents/initiatives/_TEMPLATE/README.md")


# ── Reads ─────────────────────────────────────────────────────────────────────

def get_initiatives(db: Session) -> List[Initiative]:
    """Ordered list of initiatives for the network directory (flagship first)."""
    return (
        db.query(Initiative)
        .order_by(Initiative.sort_order, Initiative.name)
        .all()
    )


def get_initiative(db: Session, slug: str) -> Optional[Initiative]:
    """Look up a single initiative by slug (None if not found)."""
    return db.query(Initiative).filter(Initiative.slug == slug).first()


# ── Slug handling / validation ────────────────────────────────────────────────

def slugify(value: str) -> str:
    """Derive a url-safe slug from arbitrary text."""
    value = (value or "").strip().lower()
    # Common transliterations so 'Müllrose' → 'mullrose', not 'mllrose'.
    value = (value.replace("ü", "u").replace("ö", "o").replace("ä", "a")
                  .replace("ß", "ss").replace("ø", "o").replace("å", "a"))
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def validate_slug(db: Session, slug: str) -> Tuple[bool, Optional[str]]:
    """Return (ok, error_key). error_key is a template-friendly reason on failure."""
    if not slug or not SLUG_RE.match(slug):
        return False, "slug_invalid"
    if slug in RESERVED_SLUGS:
        return False, "slug_reserved"
    if get_initiative(db, slug) is not None:
        return False, "slug_taken"
    return True, None


# ── External data-dir folder creation (deploy-safe) ───────────────────────────

def initiative_data_path(slug: str) -> Path:
    """Absolute path to an initiative's external data folder (outside the repo)."""
    base = Path(get_settings().initiatives_data_dir)
    # slug is validated (SLUG_RE) before this is called; guard anyway.
    safe = slugify(slug)
    return base / safe


def create_data_dir(slug: str, name: str, status: str) -> Path:
    """Create the external per-initiative folder from _TEMPLATE (idempotent).

    Writes to settings.initiatives_data_dir/<slug>/, never into the repo tree.
    Returns the created directory path. Never raises on a benign existing dir.
    """
    target = initiative_data_path(slug)
    target.mkdir(parents=True, exist_ok=True)

    readme = target / "README.md"
    if not readme.exists():
        if _TEMPLATE_README.exists():
            body = _TEMPLATE_README.read_text(encoding="utf-8")
            body = (body.replace("<Initiative Name>", name)
                        .replace("<initiative-slug>", slug)
                        .replace("<place · region · landscape>", "—")
                        .replace("<planned / active / flagship>", status))
        else:
            body = f"# {name}\n\n**Slug:** `{slug}`\n**Status:** {status}\n\n" \
                   "Place-specific material for this initiative.\n"
        readme.write_text(body, encoding="utf-8")

    return target
