#!/usr/bin/env python3
"""Sticky-sidebar checks for the offering and contribute pages.

The progress card is pinned with position:sticky so it stays beside the
text on a wide screen. Below 900px the layout is a single column, so
there is nothing to sit beside: pinned, the card covers what is being
read as the page scrolls. These checks confirm the unpinning rule is
present AND that it comes after the sticky rule in the same stylesheet,
since both carry the same specificity and source order decides.

No database, no server: this reads the templates.
"""

import re
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))

failures = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


PAGES = [("offering.html", "offering-sidebar"), ("contribute.html", "progress-sidebar")]

for page, cls in PAGES:
    src = (ROOT / "templates" / page).read_text(encoding="utf-8")

    try:
        env.parse(src)
        check(f"{page}: template parses", True)
    except Exception as exc:
        check(f"{page}: template parses", False, str(exc))
        continue

    sticky = src.find(f".{cls} {{\n    position: sticky;")
    check(f"{page}: sidebar still pinned on a wide screen", sticky != -1)

    unstick = src.find(f".{cls} {{ position: static;")
    check(f"{page}: sidebar unpinned on a narrow screen", unstick != -1)
    check(f"{page}: unpinning wins the cascade (comes after the pin)",
          sticky != -1 and unstick > sticky,
          f"pin at {sticky}, unpin at {unstick}")

    # the unpinning rule must sit inside a max-width:900px block
    block = src[max(unstick - 200, 0):unstick]
    check(f"{page}: unpinned at the point the grid collapses",
          "@media (max-width: 900px)" in block)

    # and the wide-screen rule must clear the fixed UBEC bar
    wide = re.search(r"@media \(min-width: 901px\) \{\s*\." + cls + r"\s*\{(.*?)\}", src, re.S)
    check(f"{page}: pinned card held clear of the fixed nav",
          bool(wide) and "var(--nav-height" in wide.group(1))
    check(f"{page}: pinned card capped to the window height",
          bool(wide) and "max-height" in wide.group(1) and "overflow-y" in wide.group(1))

    # the single-column order is untouched: the card still leads on a phone
    check(f"{page}: card still leads the page on a phone", f".{cls} {{\n        order: -1;" in src
          or re.search(r"\." + cls + r"\s*\{\s*order: -1;", src) is not None)

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    sys.exit(1)
print("ALL CHECKS PASSED")
