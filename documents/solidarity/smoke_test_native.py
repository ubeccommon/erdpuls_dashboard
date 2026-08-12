#!/usr/bin/env python3
"""Native-module smoke test — runs against the REAL Erdpuls app on :8600 with
the solidarity router registered. Verifies: Erdpuls session-cookie auth guards
the module; the member role is refused (403) while admin passes RBAC; and the
full financing flow works with sums-only screens. Synthetic data only."""

import urllib.request, urllib.parse, urllib.error, http.cookiejar, re, sys
import os, threading, time

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

config = uvicorn.Config(app, host="127.0.0.1", port=8600, log_level="warning")
server = uvicorn.Server(config)
threading.Thread(target=server.run, daemon=True).start()
time.sleep(2.5)

BASE = "http://127.0.0.1:8600"
SLUG = "synthetic-test-init"
P = f"/{SLUG}/solidarity"

def client():
    # Erdpuls sets its session cookie secure=True (right, behind the HTTPS
    # proxy). For this localhost http test only, permit sending it anyway.
    class LocalPolicy(http.cookiejar.DefaultCookiePolicy):
        def return_ok_secure(self, cookie, request):
            return True
    cj = http.cookiejar.CookieJar(policy=LocalPolicy())
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))

def call(op, path, data=None):
    d = urllib.parse.urlencode(data).encode() if data is not None else None
    try:
        with op.open(BASE + path, data=d, timeout=10) as r:
            return r.status, r.geturl(), r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.geturl(), e.read().decode()

failures = []
def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        failures.append(name)

# 1. Anonymous: Erdpuls auth guards the module
anon = client()
st, final, body = call(anon, P + "/")
check("anonymous is refused by Erdpuls auth", st in (401, 403) or "/login" in final)

# 2. Member role: logged in but below facilitator → 403
import psycopg2
from app.auth import hash_password
conn = psycopg2.connect("postgresql://erdpuls:erdpuls@localhost/ubec_erdpuls")
cur = conn.cursor()
cur.execute("""INSERT INTO erdpuls_threshold.users (id, email, password_hash, name, role, is_active, email_verified)
               VALUES (gen_random_uuid(), 'member@test.invalid', %s, 'Test Member', 'member', true, true)
               ON CONFLICT (email) DO UPDATE SET role='member'""",
            (hash_password("synthetic-test-pass"),))
# clean solidarity data for a deterministic run
for t in ("pledge", "token_mapping", "round_token", "bidding_round",
          "budget_line", "contribution", "supporter", "household",
          "settlement", "camp_session"):
    cur.execute(f"DELETE FROM solidarity.{t}")
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
               (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
               VALUES (gen_random_uuid(), %s, 'SYNTHETIC Test Initiative', 'Nowhere real',
                       'active', 'Synthetic initiative for tests.', 990, true, true)
               ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit(); cur.close(); conn.close()

member = client()
call(member, "/login", {"email": "member@test.invalid", "password": "synthetic-test-pass"})
st, final, body = call(member, P + "/")
check("member role is refused (RBAC 403)", st == 403)

# 3. Admin (>= facilitator): full flow
adm = client()
st, final, body = call(adm, "/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})
st, final, body = call(adm, P + "/")
check("admin passes RBAC, sessions page renders", st == 200 and "Sessions" in body)

# Sessions are created only through the offering form (v0.8).
call(adm, "/dashboard/create", {
    "title": "SYNTHETIC Session E",
    "description": ("A synthetic offering used only to open a session for this test. "
                    "It describes nothing real."),
    "delivery_language": "en", "facilitator_cost": "100", "materials_cost": "0",
    "catering_cost": "0", "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid", "initiative_id": INIT_ID,
    "solidarity_financing": "1"})
st, final, body = call(adm, P + "/")
m = re.search(P + r"/session/(\d+)", body)
check("session created via the offering form", bool(m))
sid = m.group(1)

for item, amt, ti in (("Food", "90000", ""), ("Fuel and transport", "25000", ""),
                      ("Helpers and cooks", "30000", ""), ("Supporter transfer-in", "40000", "on")):
    call(adm, f"{P}/session/{sid}/budget",
         {"line_item": item, "amount_uah": amt, "status": "estimate",
          "is_transfer_in": ti, "note": ""})
st, final, body = call(adm, f"{P}/session/{sid}")
check("remainder computed (105000.00)", "105000.00" in body)

st, final, body = call(adm, f"{P}/session/{sid}/budget",
    {"line_item": "Untagged", "amount_uah": "100", "status": "", "is_transfer_in": "", "note": ""})
check("untagged figure refused with message", "refusing to guess" in body)

for t in ("TEST-F1", "TEST-F2", "TEST-F3"):
    call(adm, f"{P}/session/{sid}/tokens", {"token": t, "household": ""})
call(adm, f"{P}/session/{sid}/tokens", {"token": "TEST-F4", "household": "SYNTHETIC Household E"})
st, final, body = call(adm, f"{P}/session/{sid}/tokens")
check("mapping optional: 'on paper' shown", "on paper" in body and "in registry" in body)

call(adm, f"{P}/session/{sid}/new-round", {})
st, final, body = call(adm, f"{P}/session/{sid}")
rid = re.search(P + r"/round/(\d+)", body).group(1)
for t, a in (("TEST-F1", "30000"), ("TEST-F2", "12000"), ("TEST-F3", "0"), ("TEST-F4", "18000")):
    call(adm, f"{P}/round/{rid}/pledge", {"token": t, "amount_uah": a})
st, final, body = call(adm, f"{P}/round/{rid}")
check("round OPEN with gap 45000.00", "OPEN" in body and "45000.00" in body)

call(adm, f"{P}/round/{rid}/pledge", {"token": "TEST-F1", "amount_uah": "85000"})
st, final, body = call(adm, f"{P}/round/{rid}")
check("re-pledge replaces: CLOSED, surplus 10000.00", "CLOSED" in body and "10000.00" in body)
check("round page sums only, no tokens", "TEST-F" not in body)

call(adm, f"{P}/supporters", {"token": "S-T1", "display_name": "", "note": ""})
call(adm, f"{P}/supporters/contribution",
     {"token": "S-T1", "period": "2026-09", "amount_uah": "550",
      "status": "settled", "note": "synthetic; stated rate 1 EUR = 45.8 UAH"})
st, final, body = call(adm, f"{P}/supporters")
check("period summary shows settled 550.00", "550.00" in body)

call(adm, f"{P}/session/{sid}/settlement",
     {"received_uah": "141000", "outstanding_uah": "4000", "spent_uah": "138000",
      "to_infrastructure_uah": "3000", "carried_by_hosts_uah": "0",
      "note": "synthetic native-module test"})
st, final, body = call(adm, f"{P}/session/{sid}/settlement")
check("settlement drawn up", "Update settlement" in body)

st, final, body = call(adm, f"{P}/report/{sid}")
check("report renders through Erdpuls base template", "Solidarity Financing" in body)
check("report: no tokens, no households",
      "TEST-F" not in body and "S-T1" not in body and "Household E" not in body)

# 4. Public initiative page untouched
st, final, body = call(anon, "/erdpuls-verkhovyna")
check("public initiative page contains no solidarity link", "solidarity" not in body.lower())

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL NATIVE-MODULE CHECKS PASSED")
