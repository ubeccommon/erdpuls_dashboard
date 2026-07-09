"""
Erdpuls — initiatives directory (data source).

Data-driven backing for the network landing (`/`, templates/network.html).
Each Erdpuls initiative is a place-based implementation of the open living lab
protocol; Müllrose is the flagship reference implementation, kept at /muellrose.

This is the lightweight config/data-module step for open thread #3 (make the
initiatives directory data-driven). When an `initiatives` table or the
"start an initiative" onboarding flow (open thread #4) is introduced, this
module is the single seam to replace — routes read initiatives from here.

Separation of concerns, consistent with the app's i18n pattern:
  * per-initiative CONTENT (name, location, per-language blurb) lives here;
  * translated card CHROME (badge words, "View initiative →") stays as inline
    Jinja conditionals in network.html.
"""
from dataclasses import dataclass
from typing import List, Optional

SUPPORTED_LANGS = ("en", "de", "pl", "uk")
FALLBACK_LANG = "en"

# Recognised statuses (drive badge label + card styling in the template).
STATUS_ACTIVE = "active"
STATUS_FORMING = "forming"
STATUS_COMING_SOON = "coming_soon"
VALID_STATUSES = (STATUS_ACTIVE, STATUS_FORMING, STATUS_COMING_SOON)


@dataclass(frozen=True)
class Initiative:
    """One place-based Erdpuls initiative in the network directory."""

    slug: str                        # stable id; internal route is /{slug} when has_page
    name: str                        # proper name, not translated (e.g. "Erdpuls Müllrose")
    status: str                      # one of VALID_STATUSES
    blurb: dict                      # {lang: str}; "en" required, others optional (fall back to en)
    location: Optional[str] = None   # place line, language-neutral (e.g. "Müllrose, Brandenburg · …")
    flagship: bool = False           # marks the reference implementation
    has_page: bool = True            # True → internal page at /{slug} (or a bespoke route)
    route: Optional[str] = None      # explicit internal path override (e.g. Müllrose → "/muellrose")
    url: Optional[str] = None        # external URL, used only when has_page is False
    languages: tuple = SUPPORTED_LANGS  # langs with reviewed copy (informational)

    @property
    def href(self) -> Optional[str]:
        """Card link target, or None for a directory-card-only entry."""
        if self.has_page:
            return self.route or f"/{self.slug}"
        return self.url  # may be None → card renders without a link

    def blurb_for(self, lang: str) -> str:
        """Blurb in `lang`, falling back to English when that language is absent."""
        return self.blurb.get(lang) or self.blurb.get(FALLBACK_LANG, "")


# Ordered directory. Flagship first. Extend/replace as initiatives are added.
_INITIATIVES: List[Initiative] = [
    Initiative(
        slug="muellrose",
        name="Erdpuls Müllrose",
        location="Müllrose, Brandenburg · Naturpark Schlaubetal",
        status=STATUS_ACTIVE,
        flagship=True,
        has_page=True,
        route="/muellrose",
        blurb={
            "en": "Center for Sustainability Literacy, Citizen Science & Reciprocal Economics.",
            "de": "Zentrum für Nachhaltigkeitsbildung, Citizen Science und reziproke Ökonomie.",
            "pl": "Centrum edukacji na rzecz zrównoważonego rozwoju, nauki obywatelskiej i ekonomii wzajemności.",
            "uk": "Центр екологічної грамотності, громадянської науки та економіки взаємності.",
        },
    ),
    # --- STAGING / DEMO entry -------------------------------------------------
    # Clearly-labelled placeholder used to validate the data-driven directory
    # end to end. Directory-card-only (no route). UK blurb intentionally omitted
    # to exercise the EN fallback. Operator: replace with the real initiative #2.
    Initiative(
        slug="staging-demo",
        name="Erdpuls — Staging Demo",
        location=None,
        status=STATUS_COMING_SOON,
        flagship=False,
        has_page=False,
        url=None,
        languages=("en", "de", "pl"),
        blurb={
            "en": "Staging entry (not a real place) — validates the data-driven "
                  "initiatives directory end to end. Replace with the next real "
                  "Erdpuls initiative.",
            "de": "Staging-Eintrag (kein realer Ort) — validiert das "
                  "datengetriebene Initiativen-Verzeichnis von Anfang bis Ende. "
                  "Durch die nächste reale Erdpuls-Initiative ersetzen.",
            "pl": "Wpis testowy (nie jest to prawdziwe miejsce) — weryfikuje "
                  "katalog inicjatyw oparty na danych od początku do końca. "
                  "Zastąp kolejną prawdziwą inicjatywą Erdpuls.",
            # uk intentionally omitted → falls back to EN
        },
    ),
]


def get_initiatives() -> List[Initiative]:
    """Return the ordered list of initiatives for the network directory."""
    return list(_INITIATIVES)


def get_initiative(slug: str) -> Optional[Initiative]:
    """Look up a single initiative by slug (None if not found)."""
    for init in _INITIATIVES:
        if init.slug == slug:
            return init
    return None
