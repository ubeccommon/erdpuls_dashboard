#!/usr/bin/env python3
"""Contribution types stay, rates go per currency.
All three contribution types are offered on every offering. Token and
hours contributions need a rate in that offering's own currency: where
one exists they work, where none does they are shown as unavailable with
the reason, and the server refuses them. No rate is ever derived from
another currency. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8633
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
cur.execute("DELETE FROM erdpuls_threshold.token_rates WHERE currency <> 'EUR'")
cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE currency <> 'EUR'")
SLUG = "synthetic-rates"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Rates', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 910, true, true)
           ON CONFLICT (slug) DO NOTHING""", (SLUG,))
cur.execute("SELECT id FROM erdpuls_threshold.initiatives WHERE slug=%s", (SLUG,))
INIT_ID = cur.fetchone()[0]
cur.execute("""INSERT INTO erdpuls_threshold.initiative_members (initiative_id, user_id, role)
               SELECT %s, id, 'facilitator' FROM erdpuls_threshold.users
               WHERE email='steward@test.invalid'
               ON CONFLICT (initiative_id, user_id) DO UPDATE SET role='facilitator'""",
            (INIT_ID,))
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

DESC = ("A synthetic offering used only to test per-currency token and hours rates. "
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

uah = make("SYNTHETIC UAH Rates", "UAH")
eur = make("SYNTHETIC EUR Rates", "EUR")

# ── all three types are offered, whatever the currency ───────
st, body = call(f"/offering/{uah}/contribute")
check("UAH page renders", st == 200)
check("money type offered", 'value="euro"' in body)
check("token type still offered", 'value="token"' in body)
check("hours type still offered", 'value="hours"' in body)
check("token card marked unavailable without a rate", "unavailable" in body)
check("token card says no rate is set", "No rate set in UAH" in body)
check("hours card says no rates are set", "No rates set in UAH" in body)
check("the reason is explained", "become available once someone sets" in " ".join(body.split()))
check("no euro rate leaks onto the UAH page", "\u20ac" not in body)

# ── and the server refuses them while no rate exists ─────────
st, body = call(f"/offering/{uah}/contribute/submit", {
    "contribution_type": "token", "token_amount": "700",
    "name": "SYNTHETIC", "email": "synthetic@test.invalid"})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.contributions WHERE offering_id=%s", (uah,))
check("token contribution refused while no UAH rate exists", cur.fetchone()[0] == 0)

# ── an admin sets a UAH rate ─────────────────────────────────
st, body = call("/admin/settings")
check("settings screen offers a currency for rates", 'name="currency"' in body)

call("/admin/settings/token-rate", {"tokens_per_eur": "2.5", "currency": "UAH"})
cur.execute("""SELECT tokens_per_eur FROM erdpuls_threshold.token_rates
               WHERE currency='UAH' ORDER BY effective_from DESC LIMIT 1""")
row = cur.fetchone()
check("UAH token rate stored", row is not None and float(row[0]) == 2.5)

cur.execute("""SELECT tokens_per_eur FROM erdpuls_threshold.token_rates
               WHERE currency='EUR' ORDER BY effective_from DESC LIMIT 1""")
eur_row = cur.fetchone()
check("the EUR rate is untouched", eur_row is None or float(eur_row[0]) != 2.5)

call("/admin/settings/hours-rate", {"category": "synthetic_work", "eur_per_hour": "300",
                                    "currency": "UAH", "description": "Synthetic category"})
cur.execute("""SELECT eur_per_hour FROM erdpuls_threshold.hours_rates
               WHERE currency='UAH' AND category='synthetic_work'""")
row = cur.fetchone()
check("UAH hours rate stored", row is not None and float(row[0]) == 300.0)

# ── now the types work on the UAH offering ───────────────────
st, body = call(f"/offering/{uah}/contribute")
check("token card now shows the UAH rate", "2.5000 tokens = 1 UAH" in body)
check("token card no longer marked unavailable", "No rate set in UAH" not in body)
check("hours category now listed", "Synthetic category" in body or "synthetic_work" in body)
check("still no euro on the UAH page", "\u20ac" not in body)

st, body = call(f"/offering/{uah}/contribute/submit", {
    "pathway": "support_only",
    "contribution_type": "token", "token_amount": "1000",
    "contact_name": "SYNTHETIC", "contact_email": "synthetic@test.invalid"})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.contributions WHERE offering_id=%s", (uah,))
check("token contribution now accepted on the UAH offering", cur.fetchone()[0] == 1)
cur.execute("""SELECT amount_eur FROM erdpuls_threshold.contributions
               WHERE offering_id=%s""", (uah,))
row = cur.fetchone()
check("1000 tokens at 2.5 per UAH recorded as 400 UAH, not converted",
      row is not None and float(row[0]) == 400.0)

# ── the EUR offering is unchanged throughout ─────────────────
st, body = call(f"/offering/{eur}/contribute")
check("EUR page still shows its euro rate", "tokens = 1 EUR" in body)
check("EUR page unaffected by the UAH rate", "2.5000 tokens" not in body)

cur.execute("DELETE FROM erdpuls_threshold.contributions")
cur.execute("DELETE FROM erdpuls_threshold.token_rates WHERE currency <> 'EUR'")
cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE currency <> 'EUR'")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL PER-CURRENCY RATE CHECKS PASSED")
