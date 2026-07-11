"""
OER Library Service — GitHub API Integration
Fetches educational resources from ubeccommon.github.io repository
and renders them for the Erdpuls dashboard.

Repo structure convention:
  Pattern_Language_of_Place/
    oer/docs/{EN,DE,PL}/          ← main curriculum documents
    oer/docs/{EN,DE,PL}/soil/     ← soil sub-collections
    oer/docs/{EN,DE,PL}/pdf/      ← companion PDFs (same stem, .pdf)
    Learning_Pathways/{EN,DE,PL}/ ← learning pathway documents

Language is detected from the path segment EN / DE / PL (case-insensitive),
NOT from filename suffixes.

© 2024–2026 Michel Garand | License: GNU AGPL v3.0
https://www.gnu.org/licenses/agpl-3.0.html
"""

import os
import re
from datetime import datetime, timedelta
from typing import Optional

import asyncio
import httpx
import markdown

# ── Configuration ─────────────────────────────────────────────────────────────
GITHUB_ORG    = "ubeccommon"
GITHUB_REPO   = "ubeccommon.github.io"
GITHUB_BRANCH = "main"
GITHUB_API    = "https://api.github.com"
RAW_BASE      = f"https://raw.githubusercontent.com/{GITHUB_ORG}/{GITHUB_REPO}/{GITHUB_BRANCH}"
PAGES_BASE    = f"https://{GITHUB_ORG}.github.io"

CACHE_TTL_MINUTES = 30

# Read from environment — set via systemd service file:
# Environment="GITHUB_TOKEN=ghp_yourtoken"
# Raises limit from 60 to 5,000 req/hour.
GITHUB_TOKEN: Optional[str] = os.environ.get("GITHUB_TOKEN")

# ── Paths that are content (indexed) vs tooling (excluded) ───────────────────
# Only Markdown files under these path prefixes are included.
CONTENT_ROOTS = (
    "Pattern_Language_of_Place/oer/docs/",
    "Pattern_Language_of_Place/Learning_Pathways/",
)

# Files matching these patterns are always excluded even inside content roots.
EXCLUDE_PATTERNS = (
    r"(^|/)index\.md$",
    r"(^|/)README",
    r"/standards/",
    r"/audit/",
    r"00_METADATA",
    r"update_markdown_metadata\.py",
    r"fix_erdpuls_markdown\.py",
    r"md_to_pdf\.py",
    r"ERDPULS_CLAUDE_PROMPT",
    r"ERDPULS_MARKDOWN_STANDARD",
)
_EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS))

# Language directory segments → language code
_LANG_DIRS = {"EN": "en", "DE": "de", "PL": "pl", "UK": "uk"}

# Human-readable collection labels derived from path segments
_COLLECTION_LABELS = {
    "oer/docs":          {"en": "OER Curriculum",        "de": "OER-Lehrplan",          "pl": "Program OER",         "uk": "Навчальна програма OER"},
    "Learning_Pathways": {"en": "Learning Pathways",      "de": "Lernpfade",             "pl": "Ścieżki uczenia",     "uk": "Навчальні шляхи"},
    "soil_art":          {"en": "Soil Art & Physics",     "de": "Bodenkunst & Physik",   "pl": "Sztuka gleby",        "uk": "Мистецтво та фізика ґрунту"},
    "soil_questions":    {"en": "Questions to the Soil",  "de": "Fragen an den Boden",   "pl": "Pytania do gleby",    "uk": "Запитання до ґрунту"},
    "soil":              {"en": "Soil Studies",           "de": "Bodenstudien",          "pl": "Badania gleby",       "uk": "Дослідження ґрунту"},
}


# ── In-memory cache ───────────────────────────────────────────────────────────
_cache: dict = {}


def _cache_get(key: str):
    entry = _cache.get(key)
    if entry and datetime.utcnow() < entry["expires"]:
        return entry["value"]
    return None


def _cache_set(key: str, value):
    _cache[key] = {
        "value": value,
        "expires": datetime.utcnow() + timedelta(minutes=CACHE_TTL_MINUTES),
    }


def _headers() -> dict:
    h = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if GITHUB_TOKEN:
        h["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return h


# ── Path analysis helpers ─────────────────────────────────────────────────────

def _detect_lang_from_path(path: str) -> Optional[str]:
    """
    Detect language from a path segment named EN, DE, or PL.
    e.g. 'Pattern_Language_of_Place/oer/docs/DE/04_teachers_guide_DE.md' → 'de'
    Returns None if no language segment found (file is language-neutral).
    """
    parts = path.split("/")
    for part in parts:
        if part.upper() in _LANG_DIRS:
            return _LANG_DIRS[part.upper()]
    return None


def _detect_collection(path: str) -> str:
    """
    Infer collection name from path segments, returning the most specific match.
    """
    for key in ("soil_art", "soil_questions", "soil", "Learning_Pathways", "oer/docs"):
        if key in path:
            return key
    return "oer/docs"


def _companion_pdf_path(md_path: str, pdf_set: set) -> Optional[str]:
    """
    Given a Markdown path, find the matching PDF in the pdf/ subdirectory.

    Repo convention:
      .../DE/04_teachers_guide_DE.md  →  .../DE/pdf/04_teachers_guide_DE.pdf
    """
    parts = md_path.rsplit("/", 1)         # ['dir', 'file.md']
    if len(parts) != 2:
        return None
    directory, filename = parts
    stem = filename.rsplit(".", 1)[0]
    pdf_path = f"{directory}/pdf/{stem}.pdf"
    return pdf_path if pdf_path in pdf_set else None


def _is_excluded(path: str) -> bool:
    return bool(_EXCLUDE_RE.search(path))


def _is_in_pdf_subdir(path: str) -> bool:
    """Skip .md files that live inside a /pdf/ subdirectory (shouldn't exist, but guard)."""
    return "/pdf/" in path


# ── GitHub API calls ──────────────────────────────────────────────────────────

async def _fetch_tree() -> list[dict]:
    """Fetch the full recursive file tree from GitHub (cached)."""
    key = f"tree:{GITHUB_REPO}:{GITHUB_BRANCH}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    url = f"{GITHUB_API}/repos/{GITHUB_ORG}/{GITHUB_REPO}/git/trees/{GITHUB_BRANCH}?recursive=1"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, headers=_headers())
        r.raise_for_status()
        tree = r.json().get("tree", [])

    _cache_set(key, tree)
    return tree


async def _fetch_raw(path: str) -> str:
    """
    Fetch raw file content via raw.githubusercontent.com CDN.
    This endpoint has NO API rate limit — no auth token required.
    Only _fetch_tree() uses the GitHub API and counts against rate limits.
    """
    key = f"raw:{GITHUB_REPO}:{path}"
    cached = _cache_get(key)
    if cached is not None:
        return cached

    url = f"{RAW_BASE}/{path}"
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url)   # no auth needed for public raw content
        r.raise_for_status()
        raw = r.text

    _cache_set(key, raw)
    return raw


async def fetch_raw_html(repo_path: str) -> str:
    """
    Public wrapper around _fetch_raw for callers that need to re-serve a raw
    HTML file (e.g. the Learning Pathway Maps) same-origin through the app,
    avoiding cross-origin iframe restrictions. `repo_path` is repo-relative,
    e.g. 'Pattern_Language_of_Place/Learning_Pathways/EN/…_EN.html'.
    Cached with the same 30-min TTL as all other raw fetches.
    """
    return await _fetch_raw(repo_path.lstrip("/"))


# ── Markdown parsing helpers ──────────────────────────────────────────────────

def _extract_title(text: str, fallback: str) -> str:
    """Return first H1 heading, or fallback."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
    return fallback


def _extract_description(text: str, max_chars: int = 220) -> str:
    """Return the first non-heading, non-empty paragraph line."""
    in_front_matter = False
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if i == 0 and line.strip() == "---":
            in_front_matter = True
            continue
        if in_front_matter:
            if line.strip() == "---":
                in_front_matter = False
            continue
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("!"):
            return stripped[:max_chars] + ("…" if len(stripped) > max_chars else "")
    return ""


def _render_markdown(text: str) -> str:
    extensions = ["tables", "fenced_code", "toc", "attr_list", "def_list", "nl2br"]
    return markdown.markdown(text, extensions=extensions)


# ── Resource metadata builder ─────────────────────────────────────────────────

def _build_resource_meta(path: str, pdf_set: set) -> Optional[dict]:
    """
    Build a metadata dict for a single Markdown file.
    Returns None if the file should be excluded.
    """
    # Must be inside a content root
    if not any(path.startswith(root) for root in CONTENT_ROOTS):
        return None
    # Must not be excluded by pattern
    if _is_excluded(path):
        return None
    # Must not be inside a pdf/ subdir
    if _is_in_pdf_subdir(path):
        return None

    lang = _detect_lang_from_path(path)
    # Skip files with no language segment (language-neutral tooling docs)
    if lang is None:
        return None

    filename = path.split("/")[-1]
    stem = filename.rsplit(".", 1)[0]
    collection_key = _detect_collection(path)
    pdf_path = _companion_pdf_path(path, pdf_set)

    return {
        "path":             path,
        "filename":         filename,
        "stem":             stem,
        "lang":             lang,
        "collection_key":   collection_key,
        "title":            None,       # populated by get_resource_list_with_previews
        "description":      None,
        "pdf_path":         pdf_path,
        "raw_md_url":       f"{RAW_BASE}/{path}",
        "pdf_url":          f"{RAW_BASE}/{pdf_path}" if pdf_path else None,
        "github_pages_url": f"{PAGES_BASE}/{path.replace('.md', '.html')}",
    }


# ── Public API ────────────────────────────────────────────────────────────────

async def get_resource_list(lang_filter: Optional[str] = None) -> list[dict]:
    """
    Return filtered list of OER resource metadata dicts (no content fetching).
    lang_filter: 'en', 'de', 'pl', or None for all.
    """
    tree = await _fetch_tree()

    pdf_set = {
        item["path"]
        for item in tree
        if item["type"] == "blob" and item["path"].endswith(".pdf")
    }

    resources = []
    for item in tree:
        if item["type"] != "blob" or not item["path"].endswith(".md"):
            continue
        meta = _build_resource_meta(item["path"], pdf_set)
        if meta is None:
            continue
        if lang_filter and meta["lang"] != lang_filter.lower():
            continue
        resources.append(meta)

    # Sort: by language, then collection, then filename
    resources.sort(key=lambda r: (r["lang"], r["collection_key"], r["filename"]))
    return resources


async def _enrich_resource(res: dict) -> dict:
    """Fetch and attach title + description to a single resource dict."""
    try:
        raw = await _fetch_raw(res["path"])
        res["title"] = _extract_title(raw, res["stem"])
        res["description"] = _extract_description(raw)
    except Exception:
        res["title"] = res["stem"]
        res["description"] = ""
    return res


async def get_resource_list_with_previews(lang_filter: Optional[str] = None) -> list[dict]:
    """
    Like get_resource_list but enriches each resource with title + description.
    All file fetches run concurrently via asyncio.gather — fast even for large repos.
    Individual results are cached, so subsequent page loads are instant.
    """
    resources = await get_resource_list(lang_filter)
    enriched = await asyncio.gather(*[_enrich_resource(res) for res in resources])
    return list(enriched)


async def get_resource_detail(path: str) -> dict:
    """
    Return full resource data for a single file, including rendered HTML content.
    Raises httpx.HTTPStatusError if the file cannot be fetched.
    """
    raw = await _fetch_raw(path)

    tree = await _fetch_tree()
    pdf_set = {
        item["path"]
        for item in tree
        if item["type"] == "blob" and item["path"].endswith(".pdf")
    }

    filename  = path.split("/")[-1]
    stem      = filename.rsplit(".", 1)[0]
    lang      = _detect_lang_from_path(path) or "en"
    collection_key = _detect_collection(path)
    pdf_path  = _companion_pdf_path(path, pdf_set)

    return {
        "path":             path,
        "filename":         filename,
        "stem":             stem,
        "lang":             lang,
        "collection_key":   collection_key,
        "collection_label": _COLLECTION_LABELS.get(collection_key, {}).get(lang, collection_key),
        "title":            _extract_title(raw, stem),
        "description":      _extract_description(raw),
        "html_content":     _render_markdown(raw),
        "pdf_path":         pdf_path,
        "raw_md_url":       f"{RAW_BASE}/{path}",
        "pdf_url":          f"{RAW_BASE}/{pdf_path}" if pdf_path else None,
        "github_pages_url": f"{PAGES_BASE}/{path.replace('.md', '.html')}",
        "attribution":      "© Michel Garand | License: CC BY-SA 4.0 | https://creativecommons.org/licenses/by-sa/4.0/",
    }


async def get_collections(lang_filter: Optional[str] = None) -> dict[str, list[dict]]:
    """
    Return resources grouped by collection key.
    Useful for rendering a categorised library index.
    """
    resources = await get_resource_list_with_previews(lang_filter)
    grouped: dict[str, list] = {}
    for res in resources:
        grouped.setdefault(res["collection_key"], []).append(res)
    return grouped
