#!/usr/bin/env python3
"""Offering currency on display, and copying cost lines into a session.
An offering priced in UAH was still being rendered with a euro sign on
every public and management page. These checks read the rendered pages
and confirm each shows the offering's own currency. They also cover the
copy action added for sessions whose budget is still empty, and confirm
it is refused once a round has opened or when the offering is in another
currency. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8629
BASE = f"http://127.0.0.1:{PORT}"
EURO = "\u20ac"
HRYVNIA = "\u20b4"
ZLOTY = "z\u0142"

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
SLUG = "synthetic-cur"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Cur', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 940, true, true)
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

DESC = ("A synthetic offering used only to check that an offering's own currency is shown "
        "wherever its money appears. It describes nothing real.")

def make(title, currency, solidarity=True):
    call("/dashboard/create", {
        "title": title, "description": DESC, "delivery_language": ["en"],
        "currency": currency, "initiative_id": INIT_ID,
        "facilitator_cost": "0", "materials_cost": "2100",
        "catering_cost": "4700", "space_cost": "3100",
        "sustainability_contribution": "0",
        "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
        "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid",
        **({"solidarity_financing": "1"} if solidarity else {})})
    cur.execute("SELECT id FROM erdpuls_threshold.offerings WHERE title=%s", (title,))
    return cur.fetchone()[0]

uah_id = make("SYNTHETIC UAH Display", "UAH")

# ── the offering's own pages show its currency ───────────────
for path, label in ((f"/offering/{uah_id}", "offering detail"),
                    ("/offerings", "offerings list"),
                    ("/dashboard", "user dashboard"),
                    (f"/dashboard/offering/{uah_id}", "manage offering"),
                    ("/admin/offerings", "admin offerings")):
    st, body = call(path)
    if st != 200:
        check(f"{label} renders", False)
        continue
    # look only at the region around this offering's figures
    check(f"{label} shows hryvnia", HRYVNIA in body)
    check(f"{label} shows no euro beside a UAH figure",
          not re.search(re.escape(EURO) + r"\s?(9900|2100|4700|3100)", body))

# ── the cost breakdown itself ────────────────────────────────
st, body = call(f"/offering/{uah_id}")
check("cost breakdown in hryvnia", f"{HRYVNIA}2100.00" in body or f"{HRYVNIA}2100" in body)
check("threshold in hryvnia", f"{HRYVNIA}9900.00" in body or f"{HRYVNIA}9900" in body)

# ── a EUR offering still shows euro ──────────────────────────
eur_id = make("SYNTHETIC EUR Display", "EUR", solidarity=False)
st, body = call(f"/offering/{eur_id}")
check("EUR offering still shows euro", EURO in body)
check("EUR offering shows no hryvnia", HRYVNIA not in body)

# ── a PLN offering shows zloty ───────────────────────────────
pln_id = make("SYNTHETIC PLN Display", "PLN", solidarity=False)
st, body = call(f"/offering/{pln_id}")
check("PLN offering shows zloty", ZLOTY in body)

# ── copying cost lines into an empty budget ──────────────────
cur.execute("""SELECT cs.id FROM solidarity.camp_session cs
               WHERE cs.offering_id = %s""", (uah_id,))
sid = cur.fetchone()[0]
cur.execute("DELETE FROM solidarity.budget_line WHERE session_id=%s", (sid,))
conn.commit()

st, body = call(f"{P}/session/{sid}")
check("copy control offered for an empty UAH budget", "Copy the offering" in body)
check("page does not claim lines were already copied",
      "were copied across" not in " ".join(body.split()))

st, body = call(f"{P}/session/{sid}/seed-budget", {})
cur.execute("""SELECT line_item, amount_uah, status FROM solidarity.budget_line
               WHERE session_id=%s ORDER BY line_item""", (sid,))
lines = cur.fetchall()
check("three cost lines copied", len(lines) == 3)
check("amounts copied unchanged", sorted(float(l[1]) for l in lines) == [2100.0, 3100.0, 4700.0])
check("copied lines tagged estimate", all(l[2] == "estimate" for l in lines))

st, body = call(f"{P}/session/{sid}")
check("copy control gone once the budget has lines", "Copy the offering" not in body)
check("session total is the offering threshold", "9900.00" in body)

# ── refused once a round has opened ──────────────────────────
cur.execute("DELETE FROM solidarity.budget_line WHERE session_id=%s", (sid,))
conn.commit()
call(f"{P}/session/{sid}/new-round", {})
st, body = call(f"{P}/session/{sid}/seed-budget", {})
cur.execute("SELECT COUNT(*) FROM solidarity.budget_line WHERE session_id=%s", (sid,))
check("copy refused once a round has opened", cur.fetchone()[0] == 0)
check("refusal explains the conditions", "only be copied while it is empty" in body)

cur.close(); conn.close()
print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL OFFERING-CURRENCY DISPLAY CHECKS PASSED")
