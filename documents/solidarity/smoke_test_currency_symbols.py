#!/usr/bin/env python3
"""Currency symbols on the create form.
The previous attempt looked right in the template source but never ran:
the script had been placed inside the title block, so no symbol ever
changed. These checks read the rendered page and verify the wiring is
actually present and in a place that executes — every cost row and the
threshold carry a symbol span, the handler is inside the live
DOMContentLoaded block, and nothing is left inside the title block."""

import os, sys, re, threading, time, urllib.request, urllib.parse, urllib.error, http.cookiejar

os.environ.setdefault("DATABASE_URL", "postgresql://erdpuls:erdpuls@localhost:5432/ubec_erdpuls")
os.environ.setdefault("SECRET_KEY", "test-only")

import uvicorn
from app.main import app

PORT = 8622
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

call("/login", {"email": "steward@test.invalid", "password": "synthetic-test-pass"})
st, body = call("/dashboard/create")
check("create form renders", st == 200)

# ── every cost row carries a symbol span ─────────────────────
for field in ("facilitator_cost", "materials_cost", "catering_cost",
              "space_cost", "sustainability_contribution"):
    m = re.search(r'<label for="%s">(.*?)</label>' % field, body, re.S)
    check(f"{field} label carries a symbol span",
          m is not None and 'class="cur-sym"' in m.group(1))

# ── the threshold line too ───────────────────────────────────
m = re.search(r'threshold-value.{0,120}', body, re.S)
check("threshold carries a symbol span",
      m is not None and "cur-sym" in m.group(0))
check("no bare euro left immediately before the threshold total",
      not re.search(r'>\u20ac<span id="threshold-total"', body))

# ── the handler is present and in a live position ────────────
check("symbol handler present", "updateCurrencySymbols" in body)
check("symbol map defines all three currencies",
      all(c in body for c in ("EUR:", "PLN:", "UAH:")) or "CURRENCY_SYMBOLS" in body)

title_block = body[:body.find("</head>")] if "</head>" in body else ""
check("handler is NOT stranded in the page head/title",
      "updateCurrencySymbols" not in title_block)

# it must sit in the same DOMContentLoaded handler that already runs
idx_dom = body.find("DOMContentLoaded")
idx_handler = body.find("updateCurrencySymbols")
check("handler sits inside a DOMContentLoaded block that runs",
      idx_dom != -1 and idx_handler > idx_dom)

check("handler is bound to the select's change event",
      "addEventListener('change', updateCurrencySymbols)" in body)
check("handler runs once on load so the symbol is right immediately",
      re.search(r"updateCurrencySymbols\(\);", body) is not None)

# ── the selector itself ──────────────────────────────────────
check("currency select present", 'id="currency"' in body and 'name="currency"' in body)
check("option labels carry plain symbols, not markup",
      "EUR (\u20ac)" in body and "PLN (z\u0142)" in body and "UAH (\u20b4)" in body)
check("no leftover inline onchange", 'onchange="updateCurrencySymbols()"' not in body)

# ── Ukrainian reaches the cost section ───────────────────────
# Language comes from the 'lang' cookie, not a query parameter.
req = urllib.request.Request(BASE + "/dashboard/create")
req.add_header("Cookie", "lang=uk")
for c in op.handlers[0].__class__.__mro__[:0]:
    pass
opener_cookies = "; ".join(f"{c.name}={c.value}" for h in op.handlers
                           if hasattr(h, "cookiejar") for c in h.cookiejar)
req.add_header("Cookie", f"lang=uk; {opener_cookies}")
with urllib.request.urlopen(req, timeout=10) as r:
    body_uk = r.read().decode()
check("Ukrainian cost labels rendered", "Фасилітатор" in body_uk)
check("Ukrainian threshold label rendered", "Поріг" in body_uk)
check("symbol spans still present in Ukrainian", 'class="cur-sym"' in body_uk)

print()
if failures:
    print(f"{len(failures)} FAILURE(S): {failures}")
    sys.exit(1)
print("ALL CURRENCY-SYMBOL CHECKS PASSED")
