#!/usr/bin/env python3
"""Exchange rates: fetched, cached, and frozen (migration 024).
EUR is the benchmark; rates come from Frankfurter. These checks use an
injected fetcher rather than the network, so they test the behaviour that
matters: a past rate is fetched once and never again, a rate is frozen
onto the contribution that used it and never recomputed, an outage falls
back to the last known rate and says so, and with nothing cached at all
a conversion is refused rather than guessed. Synthetic data only."""

import os, sys, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar
from datetime import date, timedelta
from decimal import Decimal

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app import fx
from app.database import SessionLocal
from app.models import Offering, Contribution

PORT = 8638
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
cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.fx_rate")
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
conn.commit()

db = SessionLocal()
TODAY = date.today()

# ── a counting fetcher, so we can see how often it is called ──
calls = {"n": 0}
def fake_fetch(base, quote, on):
    calls["n"] += 1
    rates = {("EUR", "UAH"): Decimal("51.0244"),
             ("EUR", "PLN"): Decimal("4.2500"),
             ("PLN", "EUR"): Decimal("0.2353")}
    if (base, quote) not in rates:
        raise fx.RateUnavailable(f"no stub rate for {base}/{quote}")
    return rates[(base, quote)], on

def failing_fetch(base, quote, on):
    raise OSError("simulated outage")

# ── fetched once, then cached ────────────────────────────────
rate, rdate, provider, stale = fx.get_rate(db, "EUR", "UAH", TODAY, fetcher=fake_fetch)
check("live rate fetched", rate == Decimal("51.0244") and calls["n"] == 1)
check("rate is not marked stale", stale is False)

rate2, _, _, _ = fx.get_rate(db, "EUR", "UAH", TODAY, fetcher=fake_fetch)
check("second call served from cache, no refetch", rate2 == rate and calls["n"] == 1)

cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.fx_rate WHERE base='EUR' AND quote='UAH'")
check("exactly one cached row for the pair and date", cur.fetchone()[0] == 1)

# ── an outage falls back, and says it is stale ───────────────
tomorrow = TODAY + timedelta(days=1)
rate3, rdate3, _, stale3 = fx.get_rate(db, "EUR", "UAH", tomorrow, fetcher=failing_fetch)
check("outage falls back to the last known rate", rate3 == Decimal("51.0244"))
check("the fallback is marked stale", stale3 is True)
check("the fallback carries its own date, not the one asked for", rdate3 == TODAY)

# ── with nothing cached, a conversion is refused ─────────────
try:
    fx.get_rate(db, "EUR", "SEK", TODAY, fetcher=failing_fetch)
    check("refuses when nothing is cached", False)
except fx.RateUnavailable:
    check("refuses when nothing is cached", True)

# ── same currency needs no rate at all ───────────────────────
same, r, _, _ = fx.convert(db, Decimal("100"), "UAH", "UAH", fetcher=failing_fetch)[:4]
check("same currency converts to itself", same == Decimal("100") and r == Decimal("1"))

# ── conversion pivots through the benchmark ──────────────────
conv, rate_used, _, _, _ = fx.convert(db, Decimal("100"), "PLN", "UAH",
                                      TODAY, fetcher=fake_fetch)
expected = (Decimal("100") * Decimal("0.2353") * Decimal("51.0244")).quantize(Decimal("0.01"))
check("PLN->UAH pivots through EUR", conv == expected)

db.close()

# ── the rate is frozen onto the contribution ─────────────────
call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})
SLUG = "synthetic-fx"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC FX', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 880, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
conn.commit()

call("/dashboard/create", {
    "title": "SYNTHETIC FX Offering",
    "description": ("A synthetic offering used only to test that exchange rates are "
                    "frozen onto contributions. It describes nothing real."),
    "delivery_language": ["en"], "currency": "UAH", "initiative_id": INIT_ID,
    "facilitator_cost": "0", "materials_cost": "9900", "catering_cost": "0",
    "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"})
cur.execute("SELECT id FROM erdpuls_threshold.offerings WHERE title='SYNTHETIC FX Offering'")
oid = cur.fetchone()[0]

call(f"/offering/{oid}/contribute/submit", {
    "pathway": "support_only", "contribution_type": "euro", "amount_eur": "50",
    "currency": "EUR", "contact_name": "SYNTHETIC", "contact_email": "s@test.invalid"})
cur.execute("""SELECT amount_eur, currency, amount_converted, fx_rate, fx_rate_date, fx_provider
               FROM erdpuls_threshold.contributions WHERE offering_id=%s""", (oid,))
row = cur.fetchone()
check("contribution recorded", row is not None)
if row:
    check("amount kept as given, in euro", float(row[0]) == 50.0 and row[1] == "EUR")
    check("converted figure frozen (50 x 51.0244 = 2551.22)", float(row[2]) == 2551.22)
    check("the rate itself is stored", float(row[3]) == 51.0244)
    check("the rate's date is stored", row[4] is not None)
    check("the provider is stored", row[5] == "frankfurter")

# ── the total counts it, and does not move when rates move ───
db = SessionLocal()
off = db.query(Offering).filter(Offering.id == oid).first()
total_before = off.get_total_contributed(db)
check("converted gift counts toward the threshold", float(total_before) == 2551.22)

cur.execute("""UPDATE erdpuls_threshold.fx_rate SET rate = 99.9999
               WHERE base='EUR' AND quote='UAH'""")
conn.commit()
db.expire_all()
total_after = off.get_total_contributed(db)
check("the total does not move when the rate changes", total_after == total_before)
db.close()

# ── a gift in the offering's own currency needs no rate ──────
call(f"/offering/{oid}/contribute/submit", {
    "pathway": "support_only", "contribution_type": "euro", "amount_eur": "1000",
    "currency": "UAH", "contact_name": "SYNTHETIC B", "contact_email": "b@test.invalid"})
cur.execute("""SELECT amount_converted, fx_rate FROM erdpuls_threshold.contributions
               WHERE offering_id=%s AND currency='UAH'""", (oid,))
native = cur.fetchone()
check("native gift stored with no rate", native is not None and native[1] is None)
check("native gift converts to itself", float(native[0]) == 1000.0)

db = SessionLocal()
off = db.query(Offering).filter(Offering.id == oid).first()
check("total now 2551.22 + 1000", float(off.get_total_contributed(db)) == 3551.22)
db.close()

cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.fx_rate")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL EXCHANGE-RATE CHECKS PASSED")
