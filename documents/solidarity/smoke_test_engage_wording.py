#!/usr/bin/env python3
"""The Support Only card names the offering's own currency.
It read "Euro, tokens, or hours" on every offering, including one priced
in hryvnia — and promised token and hours contributions even where no
rate exists in that currency, which the server refuses. The bullet now
names the offering's currency and lists only the types actually
available on it. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8636
BASE = f"http://127.0.0.1:{PORT}"
EURO = "\u20ac"

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
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE category LIKE 'synthetic_%'")
cur.execute("DELETE FROM erdpuls_threshold.token_rates WHERE currency <> 'EUR'")
SLUG = "synthetic-engage"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Engage', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 900, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to check the wording of the engagement cards. "
        "It describes nothing real.")

def make(title, currency):
    call("/dashboard/create", {
        "title": title, "description": DESC, "delivery_language": ["en"],
        "currency": currency, "initiative_id": INIT_ID,
        "facilitator_cost": "0", "materials_cost": "2100", "catering_cost": "4700",
        "space_cost": "3100", "sustainability_contribution": "0",
        "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
        "organizer_name": "Synthetic Organizer",
        "organizer_email": "organizer@test.invalid"})
    cur.execute("SELECT id FROM erdpuls_threshold.offerings WHERE title=%s", (title,))
    return cur.fetchone()[0]

uah = make("SYNTHETIC UAH Engage", "UAH")
eur = make("SYNTHETIC EUR Engage", "EUR")
pln = make("SYNTHETIC PLN Engage", "PLN")

# ── UAH with no rates: currency named, no false promises ─────
st, body = call(f"/offering/{uah}/engage")
check("UAH engage page renders", st == 200)
check("bullet names UAH", "UAH" in body)
check("bullet no longer says Euro on a UAH offering", "Euro, tokens, or hours" not in body)
check("no euro sign on the page", EURO not in body)
check("tokens not promised without a UAH rate", "UAH, tokens" not in body)
check("hours not promised without UAH rates", "or hours" not in body)

# ── give UAH a token rate only ───────────────────────────────
call("/admin/settings/token-rate", {"tokens_per_eur": "3000", "currency": "UAH"})
st, body = call(f"/offering/{uah}/engage")
check("tokens listed once a UAH token rate exists", "UAH, tokens" in body)
check("hours still not promised", "hours" not in body.split("Plant generosity")[0].split("Support Only")[-1])

# ── and hours rates too ──────────────────────────────────────
call("/admin/settings/hours-rate", {
    "category": "synthetic_engage_work", "eur_per_hour": "250", "currency": "UAH",
    "description": "Synthetic work at the local rate"})
st, body = call(f"/offering/{uah}/engage")
norm = " ".join(body.split())
check("both types listed once both rates exist", "UAH, tokens, or hours" in norm)
check("still no euro anywhere", EURO not in body)

# ── EUR offering keeps its own wording ───────────────────────
st, body = call(f"/offering/{eur}/engage")
norm = " ".join(body.split())
check("EUR offering names EUR", "EUR, tokens" in norm)
check("EUR offering does not name UAH", "UAH" not in body)

# ── PLN with no rates at all ─────────────────────────────────
st, body = call(f"/offering/{pln}/engage")
norm = " ".join(body.split())
check("PLN offering names PLN", "PLN" in body)
check("PLN promises no types without rates",
      "PLN, tokens" not in norm and "PLN, hours" not in norm)

cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE category='synthetic_engage_work'")
cur.execute("DELETE FROM erdpuls_threshold.token_rates WHERE currency='UAH'")
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL ENGAGE-WORDING CHECKS PASSED")
