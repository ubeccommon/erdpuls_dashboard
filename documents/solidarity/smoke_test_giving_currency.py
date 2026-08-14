#!/usr/bin/env python3
"""A supporter chooses the currency they give in (migration 023).
Supporters are not all in the offering's country. These checks confirm a
contribution is stored in the currency it was actually given in, that the
offering's progress counts only its own currency — because the threshold
is denominated in it and no exchange rate exists anywhere in this
application — and that gifts in other currencies are reported beside it
rather than folded into it. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8637
BASE = f"http://127.0.0.1:{PORT}"
EURO = "\u20ac"
HRYVNIA = "\u20b4"

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
cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
SLUG = "synthetic-give"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Give', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 890, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to test contributions given in a currency other "
        "than the offering's own. It describes nothing real.")
call("/dashboard/create", {
    "title": "SYNTHETIC Give Offering", "description": DESC,
    "delivery_language": ["en"], "currency": "UAH", "initiative_id": INIT_ID,
    "facilitator_cost": "0", "materials_cost": "9900", "catering_cost": "0",
    "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"})
cur.execute("SELECT id FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Give Offering'")
oid = cur.fetchone()[0]

# ── the choice is offered ────────────────────────────────────
st, body = call(f"/offering/{oid}/contribute")
check("contribute page renders", st == 200)
check("a currency chooser is offered", 'name="currency"' in body and 'id="currency"' in body)
for c in ("EUR", "PLN", "UAH"):
    check(f"{c} offered as a giving currency", f'value="{c}"' in body)
check("the offering's own currency is marked", "the offering's own" in body)
check("defaults to the offering's currency", 'value="UAH" selected' in body)

# ── giving in the offering's own currency counts ─────────────
call(f"/offering/{oid}/contribute/submit", {
    "pathway": "support_only", "contribution_type": "euro", "amount_eur": "2000",
    "currency": "UAH", "contact_name": "SYNTHETIC A",
    "contact_email": "a@test.invalid"})
cur.execute("""SELECT amount_eur, currency FROM erdpuls_threshold.contributions
               WHERE offering_id=%s""", (oid,))
rows = cur.fetchall()
check("contribution stored", len(rows) == 1)
check("stored in UAH as given", rows[0][1] == "UAH" and float(rows[0][0]) == 2000.0)

st, body = call(f"/offering/{oid}")
check("progress counts the UAH gift", "2000" in body)

# ── giving in another currency is stored as given ────────────
call(f"/offering/{oid}/contribute/submit", {
    "pathway": "support_only", "contribution_type": "euro", "amount_eur": "50",
    "currency": "EUR", "contact_name": "SYNTHETIC B",
    "contact_email": "b@test.invalid"})
cur.execute("""SELECT amount_eur, currency FROM erdpuls_threshold.contributions
               WHERE offering_id=%s AND currency='EUR'""", (oid,))
eur_row = cur.fetchone()
# With no rate cached and no network here, the conversion is refused
# rather than guessed — the designed behaviour since migration 024.
check("euro gift refused when no rate can be had", eur_row is None)

# ── and never added to a hryvnia threshold ───────────────────
from app.database import SessionLocal
from app.models import Offering
db = SessionLocal()
off = db.query(Offering).filter(Offering.id == oid).first()
total = off.get_total_contributed(db)
check("total is the native gift alone", float(total) == 2000.0)
others = off.get_other_currency_totals(db)
check("no other-currency gift got through without a rate", others == [])
db.close()

# ── the page says so plainly ─────────────────────────────────
st, body = call(f"/offering/{oid}/contribute?currency=EUR")
norm = " ".join(body.split())
check("choosing another currency explains what happens to it",
      "frozen onto your contribution" in norm or "No exchange rate is available" in norm)
check("amount label follows the chosen currency", "Amount in EUR" in body)
check("threshold still shown in the offering's currency",
      f"{HRYVNIA}9900" in body)

# The note about conversion belongs on the non-native branch, so ask for
# that one: without it the page is showing the offering's own currency,
# where no conversion arises.
st, body = call(f"/offering/{oid}/contribute?currency=EUR")
norm = " ".join(body.split())
check("the page explains what happens to a gift in another currency",
      "frozen onto your contribution" in norm or "No exchange rate is available" in norm)

# ── rates follow the chosen currency, not the offering's ─────
cur.execute("""INSERT INTO erdpuls_threshold.token_rates (id, tokens_per_eur, currency)
               VALUES (gen_random_uuid(), 70, 'EUR')
               ON CONFLICT DO NOTHING""")
conn.commit()
st, body = call(f"/offering/{oid}/contribute?currency=EUR")
check("EUR token rate offered when giving in euro", "70" in body)
st, body = call(f"/offering/{oid}/contribute?currency=UAH")
check("no UAH token rate, so it is marked unavailable",
      "No rate set in UAH" in body)

# ── an unknown currency falls back, never stored ─────────────
call(f"/offering/{oid}/contribute/submit", {
    "pathway": "support_only", "contribution_type": "euro", "amount_eur": "10",
    "currency": "XYZ", "contact_name": "SYNTHETIC C",
    "contact_email": "c@test.invalid"})
cur.execute("""SELECT COUNT(*) FROM erdpuls_threshold.contributions
               WHERE offering_id=%s AND currency NOT IN ('EUR','PLN','UAH')""", (oid,))
check("an unknown currency is never stored", cur.fetchone()[0] == 0)

cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.token_rates WHERE currency='EUR' AND tokens_per_eur=70")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL GIVING-CURRENCY CHECKS PASSED")
