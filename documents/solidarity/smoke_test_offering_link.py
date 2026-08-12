#!/usr/bin/env python3
"""Offering link tests (v0.7).
An offering may be financed through the solidarity module, chosen at
creation. These checks confirm: the choice is offered only to roles that
can use the module; ticking it opens exactly one linked session carrying
the offering's words; no EUR figure is converted into the UAH budget; a
creator cannot open a session they could not reach; and the two ledgers
stay separate. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.auth import hash_password

PORT = 8614
BASE = f"http://127.0.0.1:{PORT}"
P = "/erdpuls-verkhovyna/solidarity"

threading.Thread(target=uvicorn.Server(
    uvicorn.Config(app, host="127.0.0.1", port=PORT, log_level="warning")).run,
    daemon=True).start()
time.sleep(2.5)

class LocalPolicy(http.cookiejar.DefaultCookiePolicy):
    def return_ok_secure(self, cookie, request):
        return True

def client():
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(
        http.cookiejar.CookieJar(policy=LocalPolicy())))

def call(op, path, data=None):
    d = urllib.parse.urlencode(data).encode() if data is not None else None
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
pw = hash_password("synthetic-test-pass")
for role in ("creator", "facilitator"):
    cur.execute("""INSERT INTO erdpuls_threshold.users
                   (id, email, password_hash, name, role, is_active, email_verified)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, true, true)
                   ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role,
                       password_hash = EXCLUDED.password_hash""",
                (f"{role}@test.invalid", pw, f"Test {role.title()}", role))
conn.commit()

def login_as(email):
    op = client()
    call(op, "/login", {"email": email, "password": "synthetic-test-pass"})
    return op

DESC = ("A synthetic test offering used only to check the link between an Erdpuls "
        "offering and a solidarity financing session. It describes nothing real.")

def offering_form(title, solidarity=None):
    d = {"title": title, "description": DESC, "delivery_language": "en",
         "facilitator_cost": "300", "materials_cost": "100", "catering_cost": "0",
         "space_cost": "0", "sustainability_contribution": "0",
         "registration_deadline": "2026-09-01",
         "contribution_deadline_date": "2026-09-10",
         "organizer_name": "Synthetic Organizer",
         "organizer_email": "organizer@test.invalid"}
    if solidarity:
        d["solidarity_financing"] = "1"
    return d

# ── the choice is only offered to roles that can use it ──────
op_creator = login_as("creator@test.invalid")
st, body = call(op_creator, "/dashboard/create")
check("checkbox hidden from creator", "solidarity_financing" not in body)

op_fac = login_as("facilitator@test.invalid")
st, body = call(op_fac, "/dashboard/create")
check("checkbox offered to facilitator", "solidarity_financing" in body)

# ── creator ticking it anyway must not open a session ────────
call(op_creator, "/dashboard/create", offering_form("SYNTHETIC Creator Offering", solidarity=True))
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session")
check("creator cannot open a session by posting the field", cur.fetchone()[0] == 0)

# ── unticked: offering created, no session ───────────────────
call(op_fac, "/dashboard/create", offering_form("SYNTHETIC Plain Offering"))
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session")
check("unticked creates no session", cur.fetchone()[0] == 0)

# ── ticked: exactly one linked session ───────────────────────
call(op_fac, "/dashboard/create", offering_form("SYNTHETIC Financed Offering", solidarity=True))
cur.execute("""SELECT cs.id, cs.label, cs.description, cs.offering_id, cs.note,
                      o.title, o.threshold_amount
               FROM solidarity.camp_session cs
               JOIN erdpuls_threshold.offerings o ON o.id = cs.offering_id""")
rows = cur.fetchall()
check("exactly one linked session created", len(rows) == 1)
sid, label, desc, oid, note, otitle, threshold = rows[0]
check("session label carries the offering title", label == "SYNTHETIC Financed Offering")
check("session description carries the offering description", desc == DESC)
check("offering threshold is 400 EUR", float(threshold) == 400.0)

# ── no EUR figure became a UAH budget line ───────────────────
cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid,))
check("no budget lines auto-created (no silent conversion)", cur.fetchone()[0] == 0)
cur.execute("SELECT cost_uah, remainder_uah FROM solidarity.v_session_budget WHERE session_id=%s", (sid,))
cost, remainder = cur.fetchone()
check("session budget starts at zero UAH", float(cost) == 0.0 and float(remainder) == 0.0)
check("EUR appears in the note only as a stated reference",
      "400.00 EUR" in note and "not converted" in note)

# ── the module shows the link, and says what it is not ───────
st, body = call(op_fac, f"{P}/session/{sid}")
check("session page names the linked offering", "SYNTHETIC Financed Offering" in body)
norm = " ".join(body.split())
check("session page states the EUR figure is reference only", "reference only" in norm)
check("session page states the ledgers do not reconcile", "do not reconcile per person" in norm)

st, body = call(op_fac, P + "/")
check("sessions index marks the link", "linked to an Erdpuls offering" in body)

# ── one offering, at most one session ────────────────────────
try:
    cur.execute("""INSERT INTO solidarity.camp_session (label, offering_id)
                   VALUES ('SYNTHETIC Duplicate', %s)""", (oid,))
    conn.commit()
    check("a second session for the same offering is refused", False)
except psycopg2.errors.UniqueViolation:
    conn.rollback()
    check("a second session for the same offering is refused", True)

# ── deleting the offering keeps the financing record ─────────
cur.execute("DELETE FROM erdpuls_threshold.offerings WHERE id=%s", (oid,))
conn.commit()
cur.execute("SELECT offering_id FROM solidarity.camp_session WHERE id=%s", (sid,))
row = cur.fetchone()
check("session survives offering deletion, unlinked", row is not None and row[0] is None)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL OFFERING-LINK CHECKS PASSED")
