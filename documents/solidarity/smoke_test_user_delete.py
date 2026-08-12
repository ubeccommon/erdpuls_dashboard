#!/usr/bin/env python3
"""User deletion, guarded (admin users screen).
Deletion is for accounts that left no trace — spam registrations and
mistakes. These checks confirm a clean account goes, that an account
which authored an offering is refused with a reason, that admins and
your own account are refused, that memberships go with a deleted account
while its financing records and email-keyed registrations stay, and that
every refusal holds at the endpoint and not only in the UI.
Synthetic data only."""

import os, sys, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.auth import hash_password

PORT = 8627
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
cur.execute("DELETE FROM erdpuls_threshold.users WHERE email LIKE 'del-%'")
pw = hash_password("synthetic-test-pass")
for email, role in (("del-spam", "member"), ("del-author", "facilitator"),
                    ("del-admin", "admin"), ("del-member", "member")):
    cur.execute("""INSERT INTO erdpuls_threshold.users
                   (id, email, password_hash, name, role, is_active, email_verified)
                   VALUES (gen_random_uuid(), %s, %s, %s, %s, true, true)""",
                (f"{email}@test.invalid", pw, f"SYNTHETIC {email}", role))
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), 'synthetic-del', 'SYNTHETIC Del', 'Nowhere real',
                   'active', 'Synthetic initiative for tests.', 960, true, true)
           ON CONFLICT (slug) DO NOTHING""")
conn.commit()

def uid(email):
    cur.execute("SELECT id FROM erdpuls_threshold.users WHERE email=%s", (f"{email}@test.invalid",))
    r = cur.fetchone()
    return r[0] if r else None

cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug='synthetic-del'")
init_id = cur.fetchone()[0]

# del-author authored an offering; del-member belongs to an initiative
cur.execute("""INSERT INTO erdpuls_threshold.offerings
               (id, title, description, threshold_amount, status, creator_id,
                registration_deadline, contribution_deadline, currency)
               VALUES (gen_random_uuid(), 'SYNTHETIC Authored Offering',
                       'A synthetic offering used only to test user deletion guards.',
                       100, 'draft', %s, NOW(), NOW(), 'EUR')""", (uid("del-author"),))
cur.execute("""INSERT INTO erdpuls_threshold.initiative_members (initiative_id, user_id, role)
               VALUES (%s, %s, 'member')""", (init_id, uid("del-member")))
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

# ── the list shows a delete control only where allowed ───────
st, body = call("/admin/users")
check("users list renders", st == 200)
check("delete control offered for a clean account",
      f'/admin/users/{uid("del-spam")}/delete' in body)
check("no delete control for an account with offerings",
      f'/admin/users/{uid("del-author")}/delete' not in body)
check("no delete control for an admin account",
      f'/admin/users/{uid("del-admin")}/delete' not in body)
check("reason shown instead of a control", "not deletable" in body)

# ── a clean account goes ─────────────────────────────────────
spam_id = uid("del-spam")
st, body = call(f"/admin/users/{spam_id}/delete", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.users WHERE id=%s", (spam_id,))
check("clean account deleted", cur.fetchone()[0] == 0)

# ── an author is refused, at the endpoint ────────────────────
author_id = uid("del-author")
st, body = call(f"/admin/users/{author_id}/delete", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.users WHERE id=%s", (author_id,))
check("account with offerings survives a hand-crafted delete", cur.fetchone()[0] == 1)
check("refusal explains why", "authored" in body.lower() or "deactivate" in body.lower())
cur.execute("""SELECT creator_id FROM erdpuls_threshold.offerings
               WHERE title='SYNTHETIC Authored Offering'""")
check("the offering keeps its author", cur.fetchone()[0] == author_id)

# ── admins and self are refused ──────────────────────────────
admin_id = uid("del-admin")
st, body = call(f"/admin/users/{admin_id}/delete", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.users WHERE id=%s", (admin_id,))
check("admin account survives", cur.fetchone()[0] == 1)

cur.execute("SELECT id FROM erdpuls_threshold.users WHERE email='steward@test.invalid'")
self_id = cur.fetchone()[0]
st, body = call(f"/admin/users/{self_id}/delete", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.users WHERE id=%s", (self_id,))
check("own account survives", cur.fetchone()[0] == 1)
check("self-deletion explains why", "your own account" in body.lower())

# ── membership goes with the account; records stay ───────────
member_id = uid("del-member")
cur.execute("""INSERT INTO solidarity.camp_session (label, initiative_id)
               VALUES ('SYNTHETIC Delete-Guard Session', %s) RETURNING id""", (init_id,))
sid = cur.fetchone()[0]
cur.execute("""INSERT INTO erdpuls_threshold.registrations
               (id, offering_id, email, name, status, registered_at)
               SELECT gen_random_uuid(), id, 'del-member@test.invalid', 'SYNTHETIC',
                      'confirmed', NOW()
               FROM erdpuls_threshold.offerings LIMIT 1""")
conn.commit()

st, body = call(f"/admin/users/{member_id}/delete", {})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.users WHERE id=%s", (member_id,))
check("member account deleted", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.initiative_members WHERE user_id=%s", (member_id,))
check("their membership went with them", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE id=%s", (sid,))
check("the financing record stays", cur.fetchone()[0] == 1)
cur.execute("""SELECT COUNT(*) FROM erdpuls_threshold.registrations
               WHERE email='del-member@test.invalid'""")
check("their registration stays: it records an event", cur.fetchone()[0] == 1)

cur.execute("DELETE FROM erdpuls_threshold.registrations WHERE email='del-member@test.invalid'")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
cur.execute("DELETE FROM erdpuls_threshold.users WHERE email LIKE 'del-%'")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL USER-DELETE CHECKS PASSED")
