#!/usr/bin/env python3
"""Session deletion discipline (v0.9).
A session may be deleted only while nothing has been committed against
it. These checks confirm: a fresh session goes cleanly, taking its budget
lines, tokens and empty rounds; a single pledge makes it permanent; a
settlement account makes it permanent; the refusal holds at the endpoint,
not just in the UI; and the offering it financed is never touched.
Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8619
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

SYNTH_DESC = ("A synthetic offering used only to open a session for this deletion test. "
              "It describes nothing real.")

def make_session(title):
    call("/dashboard/create", {
        "title": title, "description": SYNTH_DESC, "delivery_language": ["en"],
        "facilitator_cost": "100", "materials_cost": "0", "catering_cost": "0",
        "space_cost": "0", "sustainability_contribution": "0",
        "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
        "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
        "solidarity_financing": "1"})
    st, body = call(P + "/")
    return re.findall(P + r"/session/(\d+)", body)[-1]

def furnish(sid, tokens=("TEST-X1",)):
    call(f"{P}/session/{sid}/budget", {"line_item": "Food", "amount_uah": "50000",
                                       "status": "estimate", "is_transfer_in": "", "note": ""})
    for tok in tokens:
        call(f"{P}/session/{sid}/tokens", {"token": tok, "household": ""})

# ── a fresh session can go ───────────────────────────────────
sid = make_session("SYNTHETIC Deletable Session")
furnish(sid)
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
check("delete control offered on an uncommitted session", "Delete session" in body)

cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid,))
check("session has a budget line before deletion", cur.fetchone()[0] == 1)

st, body = call(f"{P}/session/{sid}/delete", {})
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE id=%s", (sid,))
check("session deleted", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid,))
check("budget lines went with it", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM solidarity.round_token WHERE session_id=%s", (sid,))
check("tokens went with it", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM solidarity.bidding_round WHERE session_id=%s", (sid,))
check("empty round went with it", cur.fetchone()[0] == 0)
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Deletable Session'")
check("the offering it financed is untouched", cur.fetchone()[0] == 1)

# ── one pledge makes it permanent ────────────────────────────
sid2 = make_session("SYNTHETIC Pledged Session")
furnish(sid2, tokens=("TEST-X2",))
call(f"{P}/session/{sid2}/new-round", {})
st, body = call(f"{P}/session/{sid2}")
rid = re.findall(P + r"/round/(\d+)", body)[-1]
call(f"{P}/round/{rid}/pledge", {"token": "TEST-X2", "amount_uah": "12000"})

st, body = call(f"{P}/session/{sid2}")
check("no delete control once a pledge exists", "Delete session" not in body)
check("reason given for the refusal", "holds pledges" in " ".join(body.split()))

st, body = call(f"{P}/session/{sid2}/delete", {})
check("endpoint refuses a pledged session", "cannot be deleted" in body)
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE id=%s", (sid2,))
check("pledged session survives the refused delete", cur.fetchone()[0] == 1)
cur.execute("SELECT COUNT(*) FROM solidarity.pledge")
check("the pledge itself survives", cur.fetchone()[0] == 1)

# ── a settlement makes it permanent even with no pledges ─────
sid3 = make_session("SYNTHETIC Settled Session")
furnish(sid3, tokens=("TEST-X3",))
call(f"{P}/session/{sid3}/settlement", {
    "received_uah": "50000", "outstanding_uah": "0", "spent_uah": "50000",
    "to_infrastructure_uah": "0", "carried_by_hosts_uah": "0",
    "note": "synthetic settled cycle"})
st, body = call(f"{P}/session/{sid3}")
check("no delete control once a settlement exists", "Delete session" not in body)
check("settlement reason given", "has a settlement account" in " ".join(body.split()))

st, body = call(f"{P}/session/{sid3}/delete", {})
cur.execute("SELECT COUNT(*) FROM solidarity.camp_session WHERE id=%s", (sid3,))
check("settled session survives the refused delete", cur.fetchone()[0] == 1)

# ── an unknown session id is a 404, not a silent success ─────
st, body = call(f"{P}/session/999999/delete", {})
check("unknown session id returns 404", st == 404)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL SESSION-DELETE CHECKS PASSED")
