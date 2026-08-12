#!/usr/bin/env python3
"""Admin overview card for solidarity financing.
Solidarity activity appears on the admin dashboard alongside offerings and
contributions — as counts and sums only, with UAH reported as UAH and never
added to the EUR totals beside it. These checks confirm the figures are
right, that no token or household reaches the overview, and that the EUR
totals are unaffected by UAH pledges. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8617
BASE = f"http://127.0.0.1:{PORT}"
P = "/erdpuls-verkhovyna/solidarity"

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
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

# Sessions are created only through the offering form (v0.8), so tests
# open one the same way a facilitator would.
SYNTH_DESC = ("A synthetic offering used only to open a session for this test. "
              "It describes nothing real and should never resemble a real one.")

def make_session(title):
    """Create an offering with solidarity financing ticked; return its session id."""
    call("/dashboard/create", {
        "title": title, "description": SYNTH_DESC, "delivery_language": ["en"],
        "facilitator_cost": "100", "materials_cost": "0", "catering_cost": "0",
        "space_cost": "0", "sustainability_contribution": "0",
        "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
        "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
        "solidarity_financing": "1"})
    st, body = call(P + "/")
    ids = re.findall(re.escape(P) + r"/session/(\d+)", body)
    return ids[-1]



# empty state
st, body = call("/admin")
check("overview renders with no sessions", st == 200 and "Solidarity sessions" in body)
m = re.search(r'stat-value">(\d+)</div>\s*<div class="stat-label">\s*<a href="/erdpuls-verkhovyna', body)
check("session count starts at zero", m and m.group(1) == "0")

# one standalone session, budget, round, pledges
sid = make_session("SYNTHETIC Overview Session")
call(f"{P}/session/{sid}/budget", {"line_item": "Food", "amount_uah": "50000",
                                   "status": "estimate", "is_transfer_in": "", "note": ""})
for tok in ("TEST-O1", "TEST-O2"):
    call(f"{P}/session/{sid}/tokens", {"token": tok, "household": ""})
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
rid = re.search(P + r"/round/(\d+)", body).group(1)
call(f"{P}/round/{rid}/pledge", {"token": "TEST-O1", "amount_uah": "12000"})
call(f"{P}/round/{rid}/pledge", {"token": "TEST-O2", "amount_uah": "8000"})

st, body = call("/admin")
norm = " ".join(body.split())
check("session count reflects the new session", ">1</div>" in body)
check("open round counted", "1 open rounds" in norm)
check("total pledged shown in UAH", "20000.00 UAH" in norm)
check("UAH is marked as not converted", "not converted to EUR" in norm)
check("EUR contribution total untouched by UAH pledges", "€0" in body or "€ 0" in norm)

# sums only: nothing identifying reaches the overview
check("no token appears in the overview", "TEST-O" not in body)
check("no per-pledge figure appears", "12000" not in body and "8000" not in body)

# linked-session count
call("/dashboard/create", {
    "title": "SYNTHETIC Overview Offering",
    "description": ("A synthetic offering used only to check that linked sessions are "
                    "counted on the admin overview. It describes nothing real."),
    "delivery_language": ["en"], "facilitator_cost": "100", "materials_cost": "0",
    "catering_cost": "0", "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
    "solidarity_financing": "1"})
st, body = call("/admin")
norm = " ".join(body.split())
check("linked session counted", "2 linked to an offering" in norm)
check("session count now two", ">2</div>" in body)

# the card links into the module
check("card links to the module", 'href="/erdpuls-verkhovyna/solidarity/"' in body)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL ADMIN-OVERVIEW CHECKS PASSED")
