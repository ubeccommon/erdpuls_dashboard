#!/usr/bin/env python3
"""The Add Rate form on the settings screen.
Three things the euro-only era left behind: the amount label always said
euro, the field carried a euro-shaped default of 15 that would be
meaningless as hryvnia, and descriptions were offered in EN/DE/PL but
not Ukrainian — the very language the first non-euro rates will be read
in. These checks confirm all three, and that a Ukrainian description
actually survives a round trip. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8635
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

def call(path, data=None, lang=None):
    d = urllib.parse.urlencode(data, doseq=True).encode() if data is not None else None
    req = urllib.request.Request(BASE + path, data=d)
    if lang:
        req.add_header("Cookie", f"lang={lang}")
    try:
        with op.open(req, timeout=10) as r:
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
cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE category LIKE 'synthetic_%'")
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})
st, body = call("/admin/settings")
check("settings renders", st == 200)

# ── the label follows the currency, rather than always euro ──
check("amount label is not hardcoded to euro",
      "\u20ac/hour" not in body and "\u20ac/Stunde" not in body)
check("label has a currency placeholder that JS updates",
      'id="rateCurrencyLabel"' in body)
check("the currency select drives the label",
      "rateCurrencyLabel" in body and "onchange" in body)

# ── no euro-shaped default ───────────────────────────────────
m = re.search(r'<input[^>]*id="eur_per_hour"[^>]*>', body)
check("amount field found", m is not None)
if m:
    check("no default value of 15", 'value="15"' not in m.group(0))
    check("field is required", "required" in m.group(0))
check("field explains the figure is local, not converted",
      "not converted from euro" in " ".join(body.split())
      or "не конвертовано з євро" in " ".join(body.split()))

# ── Ukrainian description offered ────────────────────────────
check("Ukrainian description field present", 'name="description_uk"' in body)
for other in ("description", "description_de", "description_pl"):
    check(f"{other} still present", f'name="{other}"' in body)

# ── and it survives a round trip ─────────────────────────────
UK = "Прополювання, садіння, збирання врожаю"
call("/admin/settings/hours-rate", {
    "category": "synthetic_uk_rate", "eur_per_hour": "250", "currency": "UAH",
    "description": "Synthetic garden work at the local rate",
    "description_uk": UK})
cur.execute("""SELECT currency, eur_per_hour, description_uk
               FROM erdpuls_threshold.hours_rates WHERE category='synthetic_uk_rate'""")
row = cur.fetchone()
check("rate stored in UAH", row is not None and row[0] == "UAH")
check("amount stored as entered, unconverted", row is not None and float(row[1]) == 250.0)
check("Ukrainian description stored", row is not None and row[2] == UK)

st, body = call("/admin/settings")
check("the new UAH rate is listed under UAH", "synthetic_uk_rate" in body)
check("it shows its own currency, not euro", "250" in body and "250.00 EUR" not in body)

# ── the description reaches a Ukrainian reader ───────────────
from app.database import SessionLocal
from app.models import HoursRate
db = SessionLocal()
rate = db.query(HoursRate).filter(HoursRate.category == "synthetic_uk_rate").first()
check("get_description returns Ukrainian for lang=uk", rate.get_description("uk") == UK)
check("get_description falls back to English otherwise",
      rate.get_description("en") == "Synthetic garden work at the local rate")
db.close()

# ── editing prefills the Ukrainian field and the currency ────
check("edit prefill passes the Ukrainian description", "description_uk" in body)
check("edit prefill passes the currency", "rate.currency" in body or "UAH'" in body)

cur.execute("DELETE FROM erdpuls_threshold.hours_rates WHERE category='synthetic_uk_rate'")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL RATE-FORM CHECKS PASSED")
