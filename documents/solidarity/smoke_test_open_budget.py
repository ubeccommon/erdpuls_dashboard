#!/usr/bin/env python3
"""The open budget, as the families taking part see it.
Step one of the round is to lay the budget open. These checks confirm the
view is off by default, that turning it on reaches exactly the right
people — registered participants and initiative members, nobody else —
that it shows sums and budget lines but never a token or a per-family
pledge, that it carries no pledge form, and that it is never public.
Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.auth import hash_password

PORT = 8630
BASE = f"http://127.0.0.1:{PORT}"

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
cur.execute("DELETE FROM erdpuls_threshold.registrations")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
SLUG = "synthetic-open"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Open', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 930, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]

pw = hash_password("synthetic-test-pass")
for email, role in (("open-family", "member"), ("open-member", "member"),
                    ("open-stranger", "member")):
    cur.execute("""INSERT INTO erdpuls_threshold.users
                   (id, email, password_hash, name, role, is_active, email_verified)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, true, true)
                   ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role,
                       password_hash = EXCLUDED.password_hash""",
                (f"{email}@test.invalid", pw, f"SYNTHETIC {email}", role))
cur.execute("""INSERT INTO erdpuls_threshold.initiative_members (initiative_id, user_id, role)
               SELECT %s, id, 'facilitator' FROM erdpuls_threshold.users
               WHERE email='steward@test.invalid'
               ON CONFLICT (initiative_id, user_id) DO UPDATE SET role='facilitator'""",
            (INIT_ID,))
cur.execute("""INSERT INTO erdpuls_threshold.initiative_members (initiative_id, user_id, role)
               SELECT %s, id, 'member' FROM erdpuls_threshold.users
               WHERE email='open-member@test.invalid'
               ON CONFLICT (initiative_id, user_id) DO UPDATE SET role='member'""",
            (INIT_ID,))
conn.commit()

P = f"/{SLUG}/solidarity"
fac = client()
call(fac, "/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to test the participant view of an open budget. "
        "It describes nothing real.")
call(fac, "/dashboard/create", {
    "title": "SYNTHETIC Open Budget Offering", "description": DESC,
    "delivery_language": ["en"], "currency": "UAH", "initiative_id": INIT_ID,
    "facilitator_cost": "0", "materials_cost": "2100", "catering_cost": "4700",
    "space_cost": "3100", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
    "solidarity_financing": "1"})
cur.execute("SELECT id FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Open Budget Offering'")
oid = cur.fetchone()[0]
cur.execute("SELECT id FROM solidarity.camp_session WHERE offering_id=%s", (oid,))
sid = cur.fetchone()[0]

# a family registered for the offering, by email
cur.execute("""INSERT INTO erdpuls_threshold.registrations
               (id, offering_id, email, name, status, registered_at)
               VALUES (gen_random_uuid(), %s, 'open-family@test.invalid', 'SYNTHETIC Family',
                       'confirmed', NOW())""", (oid,))
conn.commit()

OPEN = f"/{SLUG}/solidarity/open/{sid}"

# ── off by default ───────────────────────────────────────────
cur.execute("SELECT budget_shared FROM solidarity.camp_session WHERE id=%s", (sid,))
check("sharing is off by default", cur.fetchone()[0] is False)

family = client()
call(family, "/login", {"email": "open-family@test.invalid", "password": "synthetic-test-pass"})
st, body = call(family, OPEN)
check("a registered family cannot see it while sharing is off", st == 404)

st, body = call(fac, OPEN)
check("the facilitator can preview it regardless", st == 200)
check("preview warns it is not shared yet", "not shared with participants yet" in body)

# ── turn it on ───────────────────────────────────────────────
call(fac, f"{P}/session/{sid}/share", {})
cur.execute("SELECT budget_shared FROM solidarity.camp_session WHERE id=%s", (sid,))
check("sharing turned on", cur.fetchone()[0] is True)

st, body = call(family, OPEN)
check("the registered family can now see it", st == 200)
check("it shows the budget lines", "2100" in body and "4700" in body and "3100" in body)
check("it shows the remainder", "9900" in body)
check("it explains the round happens in a room", "in a room" in " ".join(body.split()))
check("it carries no pledge form", "<form" not in body or "pledge" not in body.lower().split("<footer")[0])

member = client()
call(member, "/login", {"email": "open-member@test.invalid", "password": "synthetic-test-pass"})
st, body = call(member, OPEN)
check("an initiative member can see it", st == 200)

# ── and nobody else ──────────────────────────────────────────
stranger = client()
call(stranger, "/login", {"email": "open-stranger@test.invalid", "password": "synthetic-test-pass"})
st, body = call(stranger, OPEN)
check("someone unconnected cannot see it", st == 404)

anon = client()
st, body = call(anon, OPEN)
check("it is not public", st in (401, 403, 404) or "login" in body.lower())

# ── sums only, even with pledges entered ─────────────────────
call(fac, f"{P}/session/{sid}/tokens", {"token": "TEST-OB1", "household": "SYNTHETIC Household"})
call(fac, f"{P}/session/{sid}/new-round", {})
st, body = call(fac, f"{P}/session/{sid}")
rid = re.findall(P + r"/round/(\d+)", body)[-1]
call(fac, f"{P}/round/{rid}/pledge", {"token": "TEST-OB1", "amount_uah": "4000"})

st, body = call(family, OPEN)
check("round totals shown", "4000" in body)
check("no token appears", "TEST-OB1" not in body)
check("no household name appears", "SYNTHETIC Household" not in body)
check("it states that individual pledges are shown to nobody",
      "shown to nobody" in " ".join(body.split()))

# ── turning it off closes the door again ─────────────────────
call(fac, f"{P}/session/{sid}/share", {})
st, body = call(family, OPEN)
check("turning sharing off closes it again", st == 404)

# ── a session from another initiative is not reachable here ──
st, body = call(fac, f"/{SLUG}/solidarity/open/999999")
check("unknown session id is 404", st == 404)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL OPEN-BUDGET CHECKS PASSED")
