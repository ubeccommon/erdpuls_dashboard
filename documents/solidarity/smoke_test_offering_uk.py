#!/usr/bin/env python3
"""Ukrainian offering fields (migration 015).
The site interface already speaks EN/DE/PL/UK and initiatives already
carry blurb_uk; offerings stopped at Polish. These checks confirm an
offering can be titled and described in Ukrainian, delivered in
Ukrainian, and that it falls back to English when the UK text is empty.
Synthetic data only."""

import os, sys, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app
from app.models import Offering

PORT = 8615
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
cur.execute("DELETE FROM erdpuls_threshold.offerings")
conn.commit()

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})

st, body = call("/dashboard/create")
check("form offers a Ukrainian title field", 'name="title_uk"' in body)
check("form offers a Ukrainian description field", 'name="description_uk"' in body)
check("form offers Ukrainian as a delivery language", 'value="uk"' in body)

EN_D = ("A synthetic offering used only to test Ukrainian language support on the "
        "offering form. It describes nothing real and should be deleted.")
UK_T = "СИНТЕТИЧНА пропозиція"
UK_D = ("Синтетична пропозиція, створена лише для перевірки підтримки української "
        "мови у формі. Вона не описує нічого реального.")

call("/dashboard/create", {
    "title": "SYNTHETIC Ukrainian Offering", "title_uk": UK_T,
    "description": EN_D, "description_uk": UK_D,
    "delivery_language": ["uk", "en"],
    "facilitator_cost": "100", "materials_cost": "0", "catering_cost": "0",
    "space_cost": "0", "sustainability_contribution": "0",
    "registration_deadline": "2026-09-01", "contribution_deadline_date": "2026-09-10",
    "organizer_name": "Synthetic Organizer", "organizer_email": "organizer@test.invalid"})

cur.execute("""SELECT title_uk, description_uk, delivery_language
               FROM erdpuls_threshold.offerings
               WHERE title = 'SYNTHETIC Ukrainian Offering'""")
row = cur.fetchone()
check("Ukrainian title stored", row is not None and row[0] == UK_T)
check("Ukrainian description stored", row is not None and row[1] == UK_D)
check("Ukrainian accepted as a delivery language",
      row is not None and "uk" in (row[2] or []))

# getters: uk when present, English fallback when not
from sqlalchemy.orm import Session as _S
from app.database import SessionLocal
db = SessionLocal()
o = db.query(Offering).filter(Offering.title == "SYNTHETIC Ukrainian Offering").first()
check("get_title returns Ukrainian for lang=uk", o.get_title("uk") == UK_T)
check("get_description returns Ukrainian for lang=uk", o.get_description("uk") == UK_D)
check("get_title still returns English for lang=en", o.get_title("en") == "SYNTHETIC Ukrainian Offering")
check("delivery language display names Ukrainian", "Ukrainian" in o.get_delivery_language_display("en"))

o.title_uk = None
db.commit()
check("falls back to English when Ukrainian title is empty",
      o.get_title("uk") == "SYNTHETIC Ukrainian Offering")
db.close()

cur.execute("DELETE FROM erdpuls_threshold.offerings WHERE title = 'SYNTHETIC Ukrainian Offering'")
conn.commit(); cur.close(); conn.close()

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL UKRAINIAN-OFFERING CHECKS PASSED")
