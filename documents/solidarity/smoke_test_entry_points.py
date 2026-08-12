#!/usr/bin/env python3
"""Entry-point visibility tests (v0.6).
The solidarity module is reachable from the dashboard — but only for
roles that may actually use it. These checks confirm the link appears
for facilitator, moderator and admin, is absent for member and creator,
and that visibility never substitutes for the server-side role gate:
a member who types the URL is still refused."""

import os, sys, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.auth import hash_password

PORT = 8613
BASE = f"http://127.0.0.1:{PORT}"
P = "/erdpuls-verkhovyna/solidarity"
LINK = 'href="/erdpuls-verkhovyna/solidarity/"'

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
pw = hash_password("synthetic-test-pass")
for role in ("member", "creator", "facilitator", "moderator"):
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

# ── link visibility on the user dashboard ────────────────────
for role, should_see in (("member", False), ("creator", False),
                         ("facilitator", True), ("moderator", True)):
    op = login_as(f"{role}@test.invalid")
    st, body = call(op, "/dashboard")
    seen = LINK in body
    check(f"dashboard link {'shown' if should_see else 'hidden'} for {role}", seen == should_see)

op_admin = login_as("steward@test.invalid")
st, body = call(op_admin, "/dashboard")
check("dashboard link shown for admin", LINK in body)

# ── admin nav item ───────────────────────────────────────────
st, body = call(op_admin, "/admin")
check("admin nav shows the solidarity item", LINK in body)
check("admin nav item sits with the others", "admin-nav-item" in body)

# ── visibility is not the gate: the server still decides ─────
op_member = login_as("member@test.invalid")
st, body = call(op_member, P + "/")
check("member typing the URL is still refused (403)", st == 403)

op_creator = login_as("creator@test.invalid")
st, body = call(op_creator, P + "/")
check("creator typing the URL is still refused (403)", st == 403)

op_fac = login_as("facilitator@test.invalid")
st, body = call(op_fac, P + "/")
check("facilitator reaches the module (200)", st == 200 and "Sessions" in body)

# ── the public page still shows nothing ──────────────────────
anon = client()
st, body = call(anon, "/erdpuls-verkhovyna")
check("public initiative page still has no solidarity link", "solidarity" not in body.lower())

st, body = call(anon, "/")
check("public home page has no solidarity link", "solidarity" not in body.lower())

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL ENTRY-POINT CHECKS PASSED")
