#!/usr/bin/env python3
"""Budget edit/delete + freeze-on-first-round tests (v0.4).
Runs the real Erdpuls app in-process and checks that budget lines are
editable while no round exists, and that opening a round freezes them —
in the UI *and* at the endpoints, so a hand-crafted POST cannot bypass
a hidden button. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8611
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


sid = make_session("SYNTHETIC Session L")

# ── unlocked: add, edit, delete ──────────────────────────────
call(f"{P}/session/{sid}/budget",
     {"line_item": "Food", "amount_uah": "2000", "status": "estimate",
      "is_transfer_in": "", "note": ""})
st, body = call(f"{P}/session/{sid}")
check("edit controls shown while no round exists", "Save" in body and "Delete" in body)
check("add form available", "Add line" in body)

cur.execute("SELECT id FROM solidarity.budget_line WHERE session_id=%s", (sid,))
lid = cur.fetchone()[0]

call(f"{P}/session/{sid}/budget/{lid}/edit",
     {"line_item": "Food", "amount_uah": "20000", "status": "estimate",
      "is_transfer_in": "", "note": "corrected typo"})
st, body = call(f"{P}/session/{sid}")
check("edit applied (2000 -> 20000)", "20000.00" in body and "corrected typo" in body)

# a second line, then delete it
call(f"{P}/session/{sid}/budget",
     {"line_item": "Facilitator", "amount_uah": "90000", "status": "estimate",
      "is_transfer_in": "", "note": ""})
cur.execute("SELECT id FROM solidarity.budget_line WHERE session_id=%s AND line_item='Facilitator'", (sid,))
lid2 = cur.fetchone()[0]
call(f"{P}/session/{sid}/budget/{lid2}/delete", {})
st, body = call(f"{P}/session/{sid}")
check("delete applied", "Facilitator" not in body)
check("totals recalculated after edit+delete", "20000.00" in body)

# invalid edit still refused
st, body = call(f"{P}/session/{sid}/budget/{lid}/edit",
     {"line_item": "Food", "amount_uah": "20000", "status": "",
      "is_transfer_in": "", "note": ""})
check("edit with blank status refused", "refusing to guess" in body)

# ── open a round: budget must freeze ─────────────────────────
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
check("frozen notice shown", "Budget frozen" in body)
# "Save details" (session description) is intentionally still present when
# frozen; what must be gone is the per-line budget edit/delete controls.
check("budget edit controls gone when frozen",
      "/budget/" not in body and "Delete</button>" not in body)
check("add form gone when frozen", "Add line" not in body)

# endpoints must refuse independently of the UI
st, body = call(f"{P}/session/{sid}/budget/{lid}/edit",
     {"line_item": "Sneaky", "amount_uah": "1", "status": "estimate",
      "is_transfer_in": "", "note": ""})
check("edit endpoint refuses when frozen", "budget is frozen" in body.lower())

st, body = call(f"{P}/session/{sid}/budget/{lid}/delete", {})
check("delete endpoint refuses when frozen", "budget is frozen" in body.lower())

st, body = call(f"{P}/session/{sid}/budget",
     {"line_item": "Late line", "amount_uah": "500", "status": "estimate",
      "is_transfer_in": "", "note": ""})
check("add endpoint refuses when frozen", "budget is frozen" in body.lower())

cur.execute("SELECT line_item, amount_uah FROM solidarity.budget_line WHERE session_id=%s", (sid,))
remaining = cur.fetchall()
check("database unchanged after refused attempts",
      len(remaining) == 1 and remaining[0][0] == "Food" and str(remaining[0][1]) == "20000.00")

# cross-session isolation: another session stays editable
sid2 = make_session("SYNTHETIC Session M")
st, body = call(f"{P}/session/{sid2}")
check("other session remains editable", "Add line" in body and "Budget frozen" not in body)

# wrong-session line id refused
st, body = call(f"{P}/session/{sid2}/budget/{lid}/edit",
     {"line_item": "X", "amount_uah": "1", "status": "estimate",
      "is_transfer_in": "", "note": ""})
check("line from another session refused (404)", st == 404)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL BUDGET-EDIT CHECKS PASSED")
