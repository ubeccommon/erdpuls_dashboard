#!/usr/bin/env python3
"""Initiative membership (v1.1, migration 018).
Access to financing is now place-bound: the global role says what a
person may do, membership says where. These checks confirm both must
allow an action, that a facilitator of one initiative is refused at
another, that platform admins keep oversight without a membership row,
that membership alone grants nothing without the global role, and that
removing someone leaves the financing record they took part in intact.
Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.auth import hash_password

PORT = 8625
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
cur.execute("DELETE FROM erdpuls_threshold.offerings")
cur.execute("DELETE FROM erdpuls_threshold.initiative_members")
cur.execute("DELETE FROM erdpuls_threshold.initiatives WHERE slug LIKE 'synthetic-%'")

for slug, name, sort in (("synthetic-north", "SYNTHETIC North", 980),
                         ("synthetic-south", "SYNTHETIC South", 981)):
    cur.execute("""INSERT INTO erdpuls_threshold.initiatives
                   (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
                   VALUES (gen_random_uuid(), %s, %s, 'Nowhere real', 'active',
                           'Synthetic initiative for tests.', %s, true, true)""",
                (slug, name, sort))

pw = hash_password("synthetic-test-pass")
people = {
    "north-fac": "facilitator",   # global facilitator, member of North
    "south-fac": "facilitator",   # global facilitator, member of South
    "plain-member": "member",     # member of North but no global power
    "unplaced-fac": "facilitator" # global facilitator, member of nowhere
}
for email, role in people.items():
    cur.execute("""INSERT INTO erdpuls_threshold.users
                   (id, email, password_hash, name, role, is_active, email_verified)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, true, true)
                   ON CONFLICT (email) DO UPDATE SET role = EXCLUDED.role,
                       password_hash = EXCLUDED.password_hash""",
                (f"{email}@test.invalid", pw, f"Test {email}", role))
conn.commit()

def uid(email):
    cur.execute("SELECT id FROM erdpuls_threshold.users WHERE email=%s", (f"{email}@test.invalid",))
    return cur.fetchone()[0]

def iid(slug):
    cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (slug,))
    return cur.fetchone()[0]

def join(email, slug, role):
    cur.execute("""INSERT INTO erdpuls_threshold.initiative_members
                   (initiative_id, user_id, role) VALUES (%s, %s, %s)
                   ON CONFLICT (initiative_id, user_id) DO UPDATE SET role=EXCLUDED.role""",
                (iid(slug), uid(email), role))
    conn.commit()

join("north-fac", "synthetic-north", "facilitator")
join("south-fac", "synthetic-south", "facilitator")
join("plain-member", "synthetic-north", "facilitator")  # membership, but global role too low

def login(email):
    op = client()
    call(op, "/login", {"email": f"{email}@test.invalid", "password": "synthetic-test-pass"})
    return op

# ── membership decides WHERE ─────────────────────────────────
north = login("north-fac")
st, body = call(north, "/synthetic-north/solidarity/")
check("facilitator of North reaches North", st == 200)

st, body = call(north, "/synthetic-south/solidarity/")
check("facilitator of North is refused at South (403)", st == 403)
check("refusal explains it is place-bound", "not a facilitator of this initiative" in body.lower())

south = login("south-fac")
st, body = call(south, "/synthetic-south/solidarity/")
check("facilitator of South reaches South", st == 200)
st, body = call(south, "/synthetic-north/solidarity/")
check("facilitator of South is refused at North", st == 403)

# ── membership alone grants nothing ──────────────────────────
plain = login("plain-member")
st, body = call(plain, "/synthetic-north/solidarity/")
check("member-level global role refused despite facilitator membership", st == 403)

# ── a global facilitator belonging nowhere gets in nowhere ───
unplaced = login("unplaced-fac")
st, body = call(unplaced, "/synthetic-north/solidarity/")
check("global facilitator with no membership is refused", st == 403)

# ── platform oversight passes without a membership row ───────
admin = login("steward")
st, body = call(admin, "/synthetic-north/solidarity/")
check("admin reaches North without a membership row", st == 200)
st, body = call(admin, "/synthetic-south/solidarity/")
check("admin reaches South too", st == 200)
cur.execute("""SELECT COUNT(*) FROM erdpuls_threshold.initiative_members m
               JOIN erdpuls_threshold.users u ON u.id = m.user_id
               WHERE u.email = 'steward@test.invalid'""")
check("admin holds no membership rows", cur.fetchone()[0] == 0)

# ── the chooser shows only what you may open ─────────────────
st, body = call(north, "/solidarity")
check("chooser shows North to its facilitator", "SYNTHETIC North" in body)
check("chooser hides South from North's facilitator", "SYNTHETIC South" not in body)
st, body = call(admin, "/solidarity")
check("chooser shows both to an admin", "SYNTHETIC North" in body and "SYNTHETIC South" in body)

# ── the offering form offers only your places ────────────────
st, body = call(north, "/dashboard/create")
check("create form lists North for its member", "SYNTHETIC North" in body)
check("create form hides South", "SYNTHETIC South" not in body)

# ── and the server refuses a hand-crafted attachment ─────────
DESC = ("A synthetic offering used only to test initiative membership. It describes "
        "nothing real and should be deleted.")
st, body = call(north, "/dashboard/create", {
    "title": "SYNTHETIC Cross Attachment", "description": DESC,
    "delivery_language": ["en"], "currency": "UAH", "initiative_id": iid("synthetic-south"),
    "facilitator_cost": "100", "materials_cost": "0", "catering_cost": "0",
    "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Cross Attachment'")
check("offering cannot be attached to an initiative you do not belong to",
      cur.fetchone()[0] == 0)

# ── admin can manage membership ──────────────────────────────
st, body = call(admin, f"/admin/initiatives/{iid('synthetic-north')}/members")
check("membership screen renders", st == 200 and "Role here" in body)
check("screen lists the existing member", "north-fac" in body)
check("screen warns when the global role is too low",
      "needs the global facilitator role" in body)

st, body = call(admin, f"/admin/initiatives/{iid('synthetic-north')}/members",
                {"user_id": uid("unplaced-fac"), "role": "facilitator", "note": "synthetic"})
cur.execute("""SELECT role FROM erdpuls_threshold.initiative_members
               WHERE user_id=%s AND initiative_id=%s""",
            (uid("unplaced-fac"), iid("synthetic-north")))
row = cur.fetchone()
check("admin added a member", row is not None and row[0] == "facilitator")

nowplaced = login("unplaced-fac")
st, body = call(nowplaced, "/synthetic-north/solidarity/")
check("newly added facilitator now reaches the initiative", st == 200)

# ── removal does not erase what happened ─────────────────────
cur.execute("""SELECT id FROM erdpuls_threshold.initiative_members
               WHERE user_id=%s AND initiative_id=%s""",
            (uid("unplaced-fac"), iid("synthetic-north")))
mid = cur.fetchone()[0]
cur.execute("""INSERT INTO solidarity.camp_session (label, initiative_id)
               VALUES ('SYNTHETIC Membership Session', %s) RETURNING id""",
            (iid("synthetic-north"),))
sid = cur.fetchone()[0]
conn.commit()

st, body = call(admin, f"/admin/initiatives/{iid('synthetic-north')}/members/{mid}/remove", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.initiative_members WHERE id=%s", (mid,))
check("member removed", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE id=%s", (sid,))
check("the financing record survives the removal", cur.fetchone()[0] == 1)
cur.execute("SELECT role FROM erdpuls_threshold.users WHERE email='unplaced-fac@test.invalid'")
check("removal does not touch the global role", cur.fetchone()[0] == "facilitator")

removed = login("unplaced-fac")
st, body = call(removed, "/synthetic-north/solidarity/")
check("removed person loses access", st == 403)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL MEMBERSHIP CHECKS PASSED")
