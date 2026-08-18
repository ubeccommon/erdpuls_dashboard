#!/usr/bin/env python3
"""Phone-layout checks for the solidarity templates.

Renders every solidarity screen through Jinja2 with synthetic context —
no database, no server — and checks the markup the phone stylesheet
depends on:

  - each template pulls in the one shared stylesheet, and no template
    still carries its own copy of it
  - the stylesheet declares a max-width:640px block, hides header rows,
    and prints cell labels from data-label
  - every table marked class=stack has its header row marked class=hdr
    and no unlabelled data cell other than the deliberate action cell
  - inputs are 16px on the phone, so iOS does not zoom on focus
  - the participant-facing open budget carries Ukrainian cell labels
    when lang is uk

Synthetic data only. No child data, no real household, no real figure.
"""

import re
import sys
from types import SimpleNamespace as N
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parents[2]
env = Environment(loader=FileSystemLoader(str(ROOT / "templates")))

failures = []


def check(name, ok, detail=""):
    print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        failures.append(name)


initiative = N(id=1, slug="test-initiative", name="Test Initiative", location="Testplace")
offering = N(id=7, title="Test offering", threshold_amount=1000, currency="UAH")
line = N(id=3, line_item="Food", amount_uah=12000, status="estimate",
         is_transfer_in=False, note="per nine days")
sess = N(id=2, label="Test session", days=9, adopted_on=None, description="",
         note="", budget_shared=False, offering_id=7)
vb = N(label="Test session", cost_uah=40000, cover_uah=5000, remainder_uah=35000)
rnd = N(id=4, round_id=4, round_no=1, state="open", pledge_count=3,
        total_pledged_uah=20000, gap_uah=15000, label="Test session", session_id=2)
vt = N(pledge_count=3, total_pledged_uah=20000, remainder_uah=35000, gap_uah=15000)

BASE = {"lang": "en", "user": None, "flash_messages": [], "request": None,
        "prefix": "/test-initiative/solidarity", "error": None,
        "initiative": initiative}

PAGES = {
    "choose.html": {"initiatives": [N(slug="a", name="A", location="L", sessions=2)]},
    "index.html": {"sessions": [N(id=2, label="Test session", days=9, adopted_on=None,
                                  cost_uah=40000, cover_uah=5000, remainder_uah=35000,
                                  offering_id=7)]},
    "session.html": {"s": sess, "lines": [line], "vb": vb, "rounds": [rnd],
                     "statuses": ["estimate", "budget", "pledge", "settled"],
                     "locked": False, "pledges_exist": False, "can_seed": True,
                     "offering": offering, "stl": None, "delete_block": None},
    "open_budget.html": {"s": sess, "lines": [line], "vb": vb, "rounds": [rnd],
                         "offering": offering, "is_facilitator": True},
    "round.html": {"r": rnd, "vt": vt},
    "tokens.html": {"s": sess, "toks": [N(token="F-01", mapping="on paper")]},
    "settlement.html": {"s": sess, "stl": None},
    "supporters.html": {"periods": [N(period="2026-08", contributions=2,
                                      pledged_uah=1000, settled_uah=800)],
                        "sups": [N(token="S-01", display_name=None, n=2, total=1800)]},
    "report.html": {"vb": vb, "rounds": [rnd],
                    "periods": [N(period="2026-08", contributions=2,
                                  pledged_uah=1000, settled_uah=800)]},
}

# ── the shared stylesheet ────────────────────────────────────
css = (ROOT / "templates/solidarity/_styles.html").read_text(encoding="utf-8")
check("stylesheet has a phone breakpoint", "@media (max-width:640px)" in css)
check("stylesheet hides stacked header rows", "table.stack tr.hdr{display:none}" in css)
check("stylesheet lays totals out as a line", "tr.total{background:#faf9f5;display:flex" in css)
check("stylesheet prints labels from data-label", "content:attr(data-label)" in css)
check("stylesheet sets 16px inputs on the phone", "font-size:16px" in css)
check("stylesheet keeps unstacked tables inside their own box",
      "table:not(.stack){display:block;overflow-x:auto" in css)

# ── every page renders, and renders the same stylesheet once ─
rendered = {}
for name, ctx in PAGES.items():
    src = (ROOT / "templates/solidarity" / name).read_text(encoding="utf-8")
    check(f"{name}: includes the shared stylesheet",
          '{% include "solidarity/_styles.html" %}' in src)
    check(f"{name}: carries no private copy of the stylesheet",
          "border-collapse:collapse" not in src)
    try:
        html = env.get_template(f"solidarity/{name}").render(**{**BASE, **ctx})
        rendered[name] = html
        check(f"{name}: renders", True)
    except Exception as exc:
        check(f"{name}: renders", False, f"{type(exc).__name__}: {exc}")
        continue
    check(f"{name}: stylesheet reached the page", "attr(data-label)" in html)
    check(f"{name}: viewport meta present",
          'name="viewport" content="width=device-width' in html)

# ── stacked tables are labelled ──────────────────────────────
for name, html in rendered.items():
    for table in re.findall(r"<table class=stack>.*?</table>", html, re.S):
        rows = re.findall(r"<tr[^>]*>.*?</tr>", table, re.S)
        head = rows[0] if rows else ""
        check(f"{name}: stacked table header row is marked hdr",
              "class=hdr" in head, head[:60])
        heads = re.findall(r"<th[^>]*>(.*?)</th>", head, re.S)
        action_column = bool(heads) and not heads[-1].strip()
        for row in rows[1:]:
            if "class=total" in row.split(">", 1)[0]:
                continue          # totals read as name-and-figure, no label
            cells = re.findall(r"<td[^>]*>(?:(?!</td>).)*</td>", row, re.S)
            for i, cell in enumerate(cells):
                inner = re.sub(r"<[^>]+>", "", cell).strip()
                attrs = cell.split(">", 1)[0]
                exempt = (
                    "data-label=" in attrs
                    or "colspan" in attrs
                    or "<form" in cell
                    or not inner
                    or (action_column and i == len(cells) - 1)
                )
                check(f"{name}: data cell labelled or deliberately bare",
                      exempt, cell[:70])

# ── the participant view speaks Ukrainian ────────────────────
uk = env.get_template("solidarity/open_budget.html").render(
    **{**BASE, **PAGES["open_budget.html"], "lang": "uk"})
check("open budget: Ukrainian cell labels", 'data-label="Стаття"' in uk)
check("open budget: Ukrainian header kept", "Відкритий бюджет" in uk)
check("open budget: no pledge form on the participant view",
      "<form" not in uk.split('<div class=sol>')[1].split("<footer")[0])

print()
if failures:
    print(f"{len(failures)} FAILURE(S)")
    sys.exit(1)
print("ALL CHECKS PASSED")
