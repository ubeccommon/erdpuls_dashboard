#!/usr/bin/env python3
"""No euro on a non-EUR contribute page.
The amount label, the money card and the quick-select buttons must all
name the offering's own currency, and the euro-rated contribution types
(tokens, hours) must not be offered at all — the server refuses them on
a non-EUR offering, and a form should not offer what will be refused.
On a EUR offering everything stays as it was. Synthetic data only."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8631
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
cur.execute("DELETE FROM solidarity.camp_session")
cur.execute("DELETE FROM erdpuls_threshold.offerings")
SLUG = "synthetic-contrib"
cur.execute("""INSERT INTO erdpuls_threshold.initiatives
           (id, slug, name, location, status, blurb_en, sort_order, is_published, has_page)
           VALUES (gen_random_uuid(), %s, 'SYNTHETIC Contrib', 'Nowhere real', 'active',
                   'Synthetic initiative for tests.', 920, true, true)
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

DESC = ("A synthetic offering used only to check that no euro appears on the contribute "
        "page of an offering priced in another currency. It describes nothing real.")

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

uah = make("SYNTHETIC UAH Contribute", "UAH")
eur = make("SYNTHETIC EUR Contribute", "EUR")

# ── the UAH contribute page ──────────────────────────────────
for path, label in ((f"/offering/{uah}/contribute", "support only"),
                    (f"/offering/{uah}/contribute?participate=1", "support and participate")):
    st, body = call(path)
    if st != 200:
        check(f"{label} page renders", False)
        continue
    check(f"{label}: amount label names UAH", "Amount in UAH" in body)
    check(f"{label}: money card named UAH, not Euro",
          ">UAH</div>" in body and ">Euro</div>" not in body)
    check(f"{label}: quick-select buttons in hryvnia", f"{HRYVNIA}10" in body)
    leftovers = [" ".join(m.group(0).split())
                 for m in re.finditer(r'.{0,60}' + EURO + r'.{0,60}', body)]
    check(f"{label}: no euro sign anywhere", not leftovers)
    for lo in leftovers[:4]:
        print("      euro at:", lo)
    check(f"{label}: token option not offered", "UBECrc Tokens" not in body)
    check(f"{label}: hours option not offered", 'value="hours"' not in body)
    check(f"{label}: explains why they are absent",
          "only on offerings priced in euro" in " ".join(body.split()))

# ── the EUR contribute page is unchanged ─────────────────────
st, body = call(f"/offering/{eur}/contribute")
check("EUR page renders", st == 200)
check("EUR page: amount label names EUR", "Amount in EUR" in body)
check("EUR page: money card named EUR", ">EUR</div>" in body)
check("EUR page: euro sign present", EURO in body)
check("EUR page: token option offered", "UBECrc Tokens" in body)
check("EUR page: hours option offered", 'value="hours"' in body)
check("EUR page: no hryvnia", HRYVNIA not in body)

# ── the server still refuses euro-rated types on a UAH offering ──
st, body = call(f"/offering/{uah}/contribute", {
    "contribution_type": "token", "token_amount": "700",
    "name": "SYNTHETIC", "email": "synthetic@test.invalid"})
cur.execute("SELECT COUNT(*) FROM erdpuls_threshold.contributions WHERE offering_id=%s", (uah,))
check("token contribution to a UAH offering still refused server-side",
      cur.fetchone()[0] == 0)

conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL CONTRIBUTE-CURRENCY CHECKS PASSED")
