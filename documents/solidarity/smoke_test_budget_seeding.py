#!/usr/bin/env python3
"""Budget seeding from the offering.
A UAH offering's cost lines ARE the session's figures, so copying them is
not a conversion and they are seeded at creation, tagged estimate and
editable until the first round. An offering in any other currency seeds
nothing: converting silently is the one thing this module must not do.
These checks also cover the two display bugs found alongside — the
session page hardcoded EUR, and the note explaining the link was stored
but never shown. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8628
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
SLUG = "synthetic-seed"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Seed', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 950, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
cur.execute("""INSERT INTO erdpuls_threshold.initiative_members (initiative_id, user_id, role)
               SELECT %s, id, 'facilitator' FROM erdpuls_threshold.users
               WHERE email = 'steward@test.invalid'
               ON CONFLICT (initiative_id, user_id) DO UPDATE SET role='facilitator'""",
            (INIT_ID,))
conn.commit()

P = f"/{SLUG}/solidarity"
call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to test whether cost lines are seeded into the "
        "session budget. It describes nothing real.")

def make(title, currency, costs=("90000", "25000", "0", "0", "5000")):
    call("/dashboard/create", {
        "title": title, "description": DESC, "delivery_language": ["en"],
        "currency": currency, "initiative_id": INIT_ID,
        "facilitator_cost": costs[0], "materials_cost": costs[1],
        "catering_cost": costs[2], "space_cost": costs[3],
        "sustainability_contribution": costs[4],
        "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
        "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
        "solidarity_financing": "1"})
    cur.execute("""SELECT cs.id FROM solidarity.camp_session cs
                   JOIN erdpuls_threshold.offerings o ON o.id = cs.offering_id
                   WHERE o.title = %s""", (title,))
    return cur.fetchone()[0]

# ── a UAH offering seeds its cost lines ──────────────────────
sid = make("SYNTHETIC UAH Seeded", "UAH")
cur.execute("""SELECT line_item, amount_uah, status, note FROM solidarity.budget_line
               WHERE session_id=%s ORDER BY line_item""", (sid,))
lines = cur.fetchall()
check("cost lines copied from the offering", len(lines) == 3)
by_item = {l[0]: l for l in lines}
check("facilitator cost copied", "Facilitator" in by_item and float(by_item["Facilitator"][1]) == 90000.0)
check("materials cost copied", "Materials" in by_item and float(by_item["Materials"][1]) == 25000.0)
check("sustainability contribution copied", "Sustainability contribution" in by_item)
check("zero-value lines are not copied", "Catering" not in by_item and "Space" not in by_item)
check("copied lines are tagged estimate", all(l[2] == "estimate" for l in lines))
check("copied lines say where they came from",
      all("from the offering" in (l[3] or "") for l in lines))

cur.execute("SELECT cost_uah, remainder_uah FROM solidarity.v_session_budget WHERE session_id=%s", (sid,))
cost, remainder = cur.fetchone()
check("session total matches the offering threshold", float(cost) == 120000.0)
check("remainder equals the cost with no cover yet", float(remainder) == 120000.0)

st, body = call(f"{P}/session/{sid}")
check("session page shows the seeded figures", "120000.00" in body)
check("session page states the currency matched",
      "without conversion" in " ".join(body.split()))
check("session page shows the note", "editable until the first round" in " ".join(body.split()))
check("no hardcoded EUR on a UAH offering", "threshold 120000.00 EUR" not in body)

# lines remain editable, since no round has opened
check("seeded lines are still editable", "Save" in body and "Delete" in body)

# ── a EUR offering seeds nothing ─────────────────────────────
sid_eur = make("SYNTHETIC EUR Not Seeded", "EUR", costs=("300", "100", "0", "0", "0"))
cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid_eur,))
check("EUR offering seeds no budget lines", cur.fetchone()[0] == 0)
st, body = call(f"{P}/session/{sid_eur}")
norm = " ".join(body.split())
check("EUR threshold shown in EUR, not converted", "400.00 EUR" in norm)
check("page says nothing was converted", "nothing was converted" in norm)
check("note explains the currency difference", "enter the session budget in UAH" in norm)

# ── a PLN offering likewise ──────────────────────────────────
sid_pln = make("SYNTHETIC PLN Not Seeded", "PLN", costs=("1200", "0", "0", "0", "0"))
cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid_pln,))
check("PLN offering seeds no budget lines", cur.fetchone()[0] == 0)
st, body = call(f"{P}/session/{sid_pln}")
check("PLN threshold shown in PLN", "1200.00 PLN" in " ".join(body.split()))

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL BUDGET-SEEDING CHECKS PASSED")
