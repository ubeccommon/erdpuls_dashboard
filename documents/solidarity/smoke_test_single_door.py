#!/usr/bin/env python3
"""Offerings are the only door (v0.8).
A session exists to finance something, so it may only begin with that
thing: the offering form. These checks confirm the module offers no
create form, its endpoint refuses even a hand-crafted POST, the offering
path still works, and sessions already created remain fully manageable —
including one whose offering was later deleted, since a settlement
account must outlive the listing. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8618
BASE = f"http://127.0.0.1:{PORT}"
SLUG = "synthetic-test-init"
P = f"/{SLUG}/solidarity"

threading.Thread(target=uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")).run,
    daemon=True).start()
time.sleep(2.5)

class LocalPolicy(http.cookiejar.DefaultCookiePolicy):
    def return_ok_secure(self, cookie, request):
        return True

op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(
    http.cookiejar.CookieJar(policy=LocalPolicy())))

def call(path, data=None):
    d = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
    try:
        with op.open(BASE + path, data=d, timeout=10) as r:
            return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

failures = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name)

import psycopg2
conn = psycopg2.connect(os.environ["DATABASE_URL"]); cur = conn.cursor()
for t in ("pledge", "token_mapping", "round_token", "bidding_round",
          "budget_line", "settlement", "camp_session"):
    cur.execute(f"DELETE FROM solidarity.{t}")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
               (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
               VALUES (gen_random_uuid(), %s, 'SYNTHETIC Test Initiative', 'Nowhere real',
                       'active', 'Synthetic initiative for tests.', 990, true, true)
               ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

# ── the module offers no create form ─────────────────────────
st, body = call(P + "/")
check("no 'New session' form in the module", "New session" not in body)
check("module points at the offering form instead", "/dashboard/create" in body)

# ── and refuses a hand-crafted POST ──────────────────────────
st, body = call(P + "/", {"label": "SYNTHETIC Sneaky Session", "days": "9",
                          "adopted_on": "", "description": "", "note": ""})
check("create endpoint refuses with an explanation",
      "Sessions are created by ticking solidarity financing" in body)
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session")
check("no session created by the refused POST", cur.fetchone()[0] == 0)

# ── the offering path still opens one ────────────────────────
DESC = ("A synthetic offering used only to check that the offering form is the single "
        "door to a solidarity session. It describes nothing real.")
def offering(title, solidarity=True):
    d = {"title": title, "description": DESC, "delivery_language": ["en"],
         "facilitator_cost": "300", "materials_cost": "0", "catering_cost": "0",
         "space_cost": "0", "sustainability_contribution": "0",
         "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
         "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid", "initiative_id": INIT_ID}
    if solidarity:
        d["solidarity_financing"] = "1"
    return d

call("/dashboard/create", offering("SYNTHETIC Door Offering"))
cur.execute("SELECT id, offering_id, description FROM solidarity.camp_session")
rows = cur.fetchall()
check("offering opened exactly one session", len(rows) == 1)
sid, oid, desc = rows[0]
check("session carries its offering", oid is not None)
check("session carries the offering description", desc == DESC)

# ── every session now has a thing it finances ────────────────
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE offering_id IS NULL")
check("no session exists without an offering", cur.fetchone()[0] == 0)

# ── an existing session stays fully manageable ───────────────
st, body = call(f"{P}/session/{sid}/budget",
                {"line_item": "Food", "amount_uah": "50000", "status": "estimate",
                 "is_transfer_in": "", "note": ""})
st, body = call(f"{P}/session/{sid}")
check("budget still editable on an existing session", "50000.00" in body)
call(f"{P}/session/{sid}/tokens", {"token": "TEST-K1", "household": ""})
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
check("rounds still open on an existing session", "/round/" in body)

# ── a session whose offering is deleted survives ─────────────
cur.execute("DELETE FROM erdpuls_threshold.offerings WHERE id=%s", (oid,))
conn.commit()
st, body = call(f"{P}/session/{sid}")
check("session outlives its deleted offering", st == 200 and "Open budget" in body)
st, body = call(P + "/")
check("orphaned session still listed", "SYNTHETIC Door Offering" in body)

# ── unticked offering still creates none ─────────────────────
call("/dashboard/create", offering("SYNTHETIC Plain Door Offering", solidarity=False))
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session")
check("unticked offering creates no session", cur.fetchone()[0] == 1)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL SINGLE-DOOR CHECKS PASSED")
