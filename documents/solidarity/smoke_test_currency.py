#!/usr/bin/env python3
"""Per-offering currency (migration 016).
An offering declares its own currency; its costs, threshold and
contributions are all in it, and nothing is converted between currencies.
These checks confirm the choice is offered and stored, that an unknown
code is refused, that token and hours contributions stay EUR-only because
their rates are denominated in euro, and that admin totals report each
currency separately instead of adding unlike things together.
Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8620
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
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to test per-offering currency. It describes "
        "nothing real and should be deleted after the test runs.")

def make(title, currency=None, facilitator="300"):
    d = {"title": title, "description": DESC, "delivery_language": ["en"],
         "facilitator_cost": facilitator, "materials_cost": "0", "catering_cost": "0",
         "space_cost": "0", "sustainability_contribution": "0",
         "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
         "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"}
    if currency:
        d["currency"] = currency
    return call("/dashboard/create", d)

# ── the choice is offered ────────────────────────────────────
st, body = call("/dashboard/create")
check("form offers a currency selector", 'name="currency"' in body)
for code in ("EUR", "PLN", "UAH"):
    check(f"{code} offered", f'value="{code}"' in body)
check("form says nothing is converted", "Nothing is converted" in " ".join(body.split()))

# ── stored per offering ──────────────────────────────────────
make("SYNTHETIC EUR Offering", "EUR", "300")
make("SYNTHETIC PLN Offering", "PLN", "1200")
make("SYNTHETIC UAH Offering", "UAH", "90000")
cur.execute("""SELECT title, currency, threshold_amount FROM erdpuls_threshold.offerings
               ORDER BY title""")
rows = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
check("EUR offering stored as EUR", rows["SYNTHETIC EUR Offering"][0] == "EUR")
check("PLN offering stored as PLN", rows["SYNTHETIC PLN Offering"][0] == "PLN")
check("UAH offering stored as UAH", rows["SYNTHETIC UAH Offering"][0] == "UAH")
check("UAH threshold kept as entered, unconverted",
      float(rows["SYNTHETIC UAH Offering"][1]) == 90000.0)

# ── default and invalid ──────────────────────────────────────
make("SYNTHETIC Default Currency Offering")
cur.execute("SELECT currency FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Default Currency Offering'")
check("currency defaults to EUR when unspecified", cur.fetchone()[0] == "EUR")

make("SYNTHETIC Bad Currency Offering", "XYZ")
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC Bad Currency Offering'")
check("unknown currency code refused", cur.fetchone()[0] == 0)

# ── the model reports the right symbol ───────────────────────
from app.database import SessionLocal
from app.models import Offering
db = SessionLocal()
pln = db.query(Offering).filter(Offering.title == "SYNTHETIC PLN Offering").first()
uah = db.query(Offering).filter(Offering.title == "SYNTHETIC UAH Offering").first()
eur = db.query(Offering).filter(Offering.title == "SYNTHETIC EUR Offering").first()
check("PLN symbol is zloty", pln.currency_symbol == "z\u0142")
check("UAH symbol is hryvnia", uah.currency_symbol == "\u20b4")
check("EUR symbol is euro", eur.currency_symbol == "\u20ac")

# ── token and hours stay EUR-only ────────────────────────────
# Availability follows whether a rate exists in that currency, not the
# currency itself: rates are set per region in the admin area.
check("EUR offering allows token and hours (euro rates exist)",
      eur.allows_token_and_hours(db) is True)
check("PLN offering has no rates set, so no token or hours",
      pln.allows_token_and_hours(db) is False)
check("UAH offering has no rates set, so no token or hours",
      uah.allows_token_and_hours(db) is False)
eur_id, pln_id = str(eur.id), str(pln.id)
db.close()

# ── totals are reported per currency, never merged ───────────
for oid, amount in ((eur_id, "100"), (pln_id, "500")):
    cur.execute("""INSERT INTO erdpuls_threshold.contributions
                   (id, offering_id, amount_eur, contribution_type, contributed_at, status)
                   VALUES (gen_random_uuid(), %s, %s, 'euro', NOW(), 'confirmed')""",
                (oid, amount))
conn.commit()

st, body = call("/admin")
norm = " ".join(body.split())
check("EUR total counts only EUR offerings", "100" in norm)
check("PLN total reported separately", "500" in norm and "PLN" in norm)
check("non-EUR total marked as not converted", "not converted to EUR" in norm)
# The merged figure would be 600 as a money amount. Font weights in the
# page CSS are also "600", so check the money contexts specifically.
money_600 = re.search(r'[€\u20ac]\s?600(\.00)?\b|600(\.00)?\s?(EUR|PLN|UAH)', norm)
check("EUR and PLN totals are never merged into one figure", money_600 is None)

cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL CURRENCY CHECKS PASSED")
