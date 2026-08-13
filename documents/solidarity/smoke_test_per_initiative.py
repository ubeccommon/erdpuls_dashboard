#!/usr/bin/env python3
"""Per-initiative solidarity (v1.0, migration 017).
The module is no longer bound to one place: it mounts at
/{initiative_slug}/solidarity. These checks confirm each initiative sees
only its own sessions, that a session id from another initiative is a 404
rather than a readable page, that an unknown slug is a 404, that a session
keeps its place when its offering is deleted, and that an offering with no
initiative cannot open a session at all. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8623
BASE = f"http://127.0.0.1:{PORT}"

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
cur.execute("DELETE FROM erdpuls_threshold.initiatives WHERE slug LIKE 'synthetic-%'")
for slug, name, sort in (("synthetic-alpha", "SYNTHETIC Alpha", 900),
                         ("synthetic-beta", "SYNTHETIC Beta", 901)):
    cur.execute("""INSERT INTO erdpuls_threshold.initiatives
                   (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
                   VALUES (gen_random_uuid(), %s, %s, 'Nowhere real', 'active',
                           'Synthetic initiative for tests.', %s, true, true)""",
                (slug, name, sort))
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

def init_id(slug):
    cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (slug,))
    return cur.fetchone()[0]

DESC = ("A synthetic offering used only to test per-initiative solidarity. "
        "It describes nothing real.")

def make_offering(title, slug=None, solidarity=True, currency="UAH"):
    d = {"title": title, "description": DESC, "delivery_language": ["en"],
         "currency": currency, "facilitator_cost": "1000", "materials_cost": "0",
         "catering_cost": "0", "space_cost": "0", "sustainability_contribution": "0",
         "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
         "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"}
    if slug:
        d["initiative_id"] = init_id(slug)
    if solidarity:
        d["solidarity_financing"] = "1"
    return call("/dashboard/create", d)

# ── the form offers initiatives ──────────────────────────────
st, body = call("/dashboard/create")
check("form offers an initiative selector", 'name="initiative_id"' in body)
check("both synthetic initiatives listed", "SYNTHETIC Alpha" in body and "SYNTHETIC Beta" in body)
check("network-level option offered", "Network-level" in body)

# ── each initiative gets its own session ─────────────────────
make_offering("SYNTHETIC Alpha Session", "synthetic-alpha")
make_offering("SYNTHETIC Beta Session", "synthetic-beta")
cur.execute("""SELECT cs.id, i.slug FROM solidarity.camp_session cs
               JOIN erdpuls_threshold.initiatives i ON i.id = cs.initiative_id
               ORDER BY cs.id""")
sessions = dict((slug, sid) for sid, slug in cur.fetchall())
check("alpha session created under alpha", "synthetic-alpha" in sessions)
check("beta session created under beta", "synthetic-beta" in sessions)

# ── each initiative sees only its own ────────────────────────
st, body = call("/synthetic-alpha/solidarity/")
check("alpha module renders", st == 200)
check("alpha lists its own session", "SYNTHETIC Alpha Session" in body)
check("alpha does NOT list beta's session", "SYNTHETIC Beta Session" not in body)
check("alpha page names its initiative", "SYNTHETIC Alpha" in body)

st, body = call("/synthetic-beta/solidarity/")
check("beta lists its own session", "SYNTHETIC Beta Session" in body)
check("beta does NOT list alpha's session", "SYNTHETIC Alpha Session" not in body)

# ── a session id from another initiative is a 404 ────────────
st, body = call(f"/synthetic-alpha/solidarity/session/{sessions['synthetic-beta']}")
check("beta's session is 404 under alpha's mount", st == 404)
st, body = call(f"/synthetic-beta/solidarity/session/{sessions['synthetic-alpha']}")
check("alpha's session is 404 under beta's mount", st == 404)

# writes are scoped too
st, body = call(f"/synthetic-alpha/solidarity/session/{sessions['synthetic-beta']}/budget",
                {"line_item": "Cross", "amount_uah": "1", "status": "estimate",
                 "is_transfer_in": "", "note": ""})
check("cross-initiative budget write refused", st == 404)
cur.execute("""SELECT COUNT(*) FROM solidarity.budget_line
               WHERE session_id=%s AND line_item='Cross'""",
            (sessions["synthetic-beta"],))
check("no line written across initiatives", cur.fetchone()[0] == 0)

# ── unknown slug is a 404, not an empty module ───────────────
st, body = call("/synthetic-nowhere/solidarity/")
check("unknown initiative slug is 404", st == 404)

# ── network-level offering cannot open a session ─────────────
before = len(sessions)
make_offering("SYNTHETIC Networkwide Offering", slug=None)
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session")
check("offering with no initiative opens no session", cur.fetchone()[0] == before)

# ── the chooser lists initiatives ────────────────────────────
st, body = call("/solidarity")
check("chooser renders", st == 200)
check("chooser links each initiative", "/synthetic-alpha/solidarity/" in body
      and "/synthetic-beta/solidarity/" in body)

# ── a session keeps its place when its offering goes ─────────
sid_alpha = sessions["synthetic-alpha"]
cur.execute("DELETE FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Alpha Session'")
conn.commit()
cur.execute("SELECT offering_id, initiative_id FROM solidarity.camp_session WHERE id=%s", (sid_alpha,))
oid, iid = cur.fetchone()
check("session loses its offering", oid is None)
check("session keeps its initiative", iid is not None)
st, body = call(f"/synthetic-alpha/solidarity/session/{sid_alpha}")
check("orphaned session still reachable under its initiative", st == 200)

# ── an initiative holding sessions cannot be deleted ─────────
try:
    cur.execute("DELETE FROM erdpuls_threshold.initiatives WHERE slug='synthetic-alpha'")
    conn.commit()
    check("initiative with sessions cannot be deleted", False)
except psycopg2.errors.ForeignKeyViolation:
    conn.rollback()
    check("initiative with sessions cannot be deleted", True)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL PER-INITIATIVE CHECKS PASSED")
