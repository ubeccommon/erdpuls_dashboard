#!/usr/bin/env python3
"""Session description + round deletion tests (v0.5).
Checks that: a session carries a description that is editable even while
the budget is frozen; a round with no pledges can be deleted and doing so
unfreezes the budget; a round holding even one pledge refuses deletion at
the endpoint; and the frozen notice states which case actually holds.
Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8612
BASE = f"http://127.0.0.1:{PORT}"
SLUG = "synthetic-test-init"
P = f"/{SLUG}/solidarity"

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
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
               (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
               VALUES (gen_random_uuid(), %s, 'SYNTHETIC Test Initiative', 'Nowhere real',
                       'active', 'Synthetic initiative for tests.', 990, true, true)
               ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = "Nine days on the homestead: shared meals, woodland work, evening songs."

# ── description at creation ──────────────────────────────────
# Sessions are created only through the offering form (v0.8); the
# description travels from the offering into the session.
def make_offering(title, description, solidarity=True):
    d = {"title": title, "description": description, "delivery_language": ["en"],
         "facilitator_cost": "100", "materials_cost": "0", "catering_cost": "0",
         "space_cost": "0", "sustainability_contribution": "0",
         "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
         "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid", "initiative_id": INIT_ID}
    if solidarity:
        d["solidarity_financing"] = "1"
    call("/dashboard/create", d)

make_offering("SYNTHETIC Session D", DESC)
st, body = call(P + "/")
sid = re.findall(P + r"/session/(\d+)", body)[-1]
st, body = call(f"{P}/session/{sid}")
check("description saved at creation and shown", DESC in body)

# ── description editable ─────────────────────────────────────
DESC2 = DESC + " Families bring boots."
call(f"{P}/session/{sid}/details",
     {"label": "SYNTHETIC Session D", "days": "9", "adopted_on": "", "description": DESC2})
st, body = call(f"{P}/session/{sid}")
check("description editable", DESC2 in body)

# duplicate label refused
make_offering("SYNTHETIC Other", DESC + " A second one.")
st, body = call(f"{P}/session/{sid}/details",
     {"label": "SYNTHETIC Other", "days": "9", "adopted_on": "", "description": DESC2})
check("duplicate label on edit refused", "another session already has that label" in body)

# ── budget, then an empty round ──────────────────────────────
call(f"{P}/session/{sid}/budget",
     {"line_item": "Food", "amount_uah": "2000", "status": "estimate",
      "is_transfer_in": "", "note": ""})
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
norm = " ".join(body.split())
check("frozen notice says no pledges yet (not 'families have pledged')",
      "No pledges have been entered yet" in norm and "Families have pledged" not in norm)
check("delete-round control offered for empty round", "Delete round" in body)

# description still editable while frozen
DESC3 = DESC2 + " Bring a raincoat."
call(f"{P}/session/{sid}/details",
     {"label": "SYNTHETIC Session D", "days": "9", "adopted_on": "", "description": DESC3})
st, body = call(f"{P}/session/{sid}")
check("description editable even when budget frozen", DESC3 in body)

# ── delete the empty round: budget unfreezes ─────────────────
rid = re.search(P + r"/round/(\d+)", body).group(1)
call(f"{P}/round/{rid}/delete", {})
st, body = call(f"{P}/session/{sid}")
check("empty round deleted, budget unfrozen", "Budget frozen" not in body and "Add line" in body)

# correcting the figure is now possible
cur.execute("SELECT id FROM solidarity.budget_line WHERE session_id=%s", (sid,))
lid = cur.fetchone()[0]
call(f"{P}/session/{sid}/budget/{lid}/edit",
     {"line_item": "Food", "amount_uah": "20000", "status": "estimate",
      "is_transfer_in": "", "note": "corrected after deleting empty round"})
st, body = call(f"{P}/session/{sid}")
check("budget corrected after unfreeze", "20000.00" in body)

# ── a round WITH a pledge must refuse deletion ───────────────
call(f"{P}/session/{sid}/tokens", {"token": "TEST-D1", "household": ""})
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}")
rid2 = re.search(P + r"/round/(\d+)", body).group(1)
call(f"{P}/round/{rid2}/pledge", {"token": "TEST-D1", "amount_uah": "5000"})

st, body = call(f"{P}/session/{sid}")
check("notice now states families have pledged", "Families have pledged" in body)
check("no delete control once round holds pledges",
      "Delete round" not in body and "holds pledges" in body)

st, body = call(f"{P}/round/{rid2}/delete", {})
check("delete endpoint refuses round with pledges", "cannot be deleted" in body)

cur.execute("SELECT COUNT(*) FROM solidarity.bidding_round WHERE id=%s", (rid2,))
check("round with pledges still present after refused delete", cur.fetchone()[0] == 1)
cur.execute("SELECT COUNT(*) FROM solidarity.pledge WHERE round_id=%s", (rid2,))
check("pledge survived refused delete", cur.fetchone()[0] == 1)

st, body = call(f"{P}/session/{sid}/budget",
     {"line_item": "Late", "amount_uah": "1", "status": "estimate",
      "is_transfer_in": "", "note": ""})
check("budget still frozen with pledges present", "frozen" in body.lower())

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL DESCRIPTION + ROUND-DELETE CHECKS PASSED")
