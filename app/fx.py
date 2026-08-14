"""
Exchange rates — fetching, caching, and freezing.
=================================================
Project: Erdpuls / Solidarity Financing — Michel Garand
Added August 2026 with migration 024.

EUR is the benchmark. Rates come from Frankfurter
(https://api.frankfurter.dev), which blends daily reference rates from
84 central banks and covers EUR, PLN and UAH among 201 currencies. It
needs no API key and imposes no quota.

Three rules shape everything here:

1. A rate for a past date is fetched once and cached forever. A rate
   that was true on a day stays true for that day; re-fetching could
   only introduce drift into records already written.

2. A rate is FROZEN onto the contribution that used it. Totals are
   never recomputed from today's rate, because a settled figure that
   moves overnight is not settled.

3. When the API cannot be reached, the most recent cached rate is used
   and carries its own date, so the page can say how old it is. Only
   when nothing has ever been cached is a conversion refused — an
   outage should not silently invent a number, but nor should it turn
   every supporter away.

The fetcher is injectable so the behaviour above can be tested without
network access, and so a different provider can be substituted without
touching the callers.

Changelog:
  v0.1 (August 2026) — first version.
"""

import json
import logging
import urllib.request
import urllib.error
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BENCHMARK = "EUR"
PROVIDER = "frankfurter"
API_ROOT = "https://api.frankfurter.dev/v2"
TIMEOUT_SECONDS = 6


class RateUnavailable(Exception):
    """No rate could be found, live or cached."""


def _http_fetch(base: str, quote: str, on: date):
    """Ask Frankfurter for one pair on one date.

    Returns (rate, rate_date). The rate_date is the API's own, not the
    one requested: reference rates are not published at weekends or on
    holidays, and the response says which day the figure belongs to.
    Reporting the requested date instead would misdate the record.
    """
    url = f"{API_ROOT}/rate/{base}/{quote}?date={on.isoformat()}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
        payload = json.loads(resp.read().decode())
    rate = payload.get("rate")
    if rate is None:
        raise RateUnavailable(f"no rate for {base}/{quote} on {on}")
    served = payload.get("date") or on.isoformat()
    return Decimal(str(rate)), datetime.strptime(served, "%Y-%m-%d").date()


def cached_rate(db: Session, base: str, quote: str, on: date):
    """The cached rate for exactly this date, or None."""
    row = db.execute(text("""
        SELECT rate, rate_date, provider FROM erdpuls_threshold.fx_rate
        WHERE base = :b AND quote = :q AND rate_date = :d AND provider = :p
    """), {"b": base, "q": quote, "d": on, "p": PROVIDER}).mappings().first()
    return row


def latest_cached_rate(db: Session, base: str, quote: str):
    """The most recent cached rate for this pair, whatever its date."""
    return db.execute(text("""
        SELECT rate, rate_date, provider FROM erdpuls_threshold.fx_rate
        WHERE base = :b AND quote = :q AND provider = :p
        ORDER BY rate_date DESC LIMIT 1
    """), {"b": base, "q": quote, "p": PROVIDER}).mappings().first()


def store_rate(db: Session, base: str, quote: str, rate: Decimal,
               rate_date: date, provider: str = PROVIDER):
    db.execute(text("""
        INSERT INTO erdpuls_threshold.fx_rate (base, quote, rate, rate_date, provider)
        VALUES (:b, :q, :r, :d, :p)
        ON CONFLICT (base, quote, rate_date, provider) DO NOTHING
    """), {"b": base, "q": quote, "r": rate, "d": rate_date, "p": provider})
    db.commit()


def get_rate(db: Session, base: str, quote: str, on: date = None, fetcher=None):
    """Rate for base->quote, cache first, then live, then last known.

    Returns (rate, rate_date, provider, is_stale). `is_stale` is True
    when the figure came from an earlier day than asked for, so callers
    can say so rather than presenting it as today's.
    """
    if base == quote:
        return Decimal("1"), on or date.today(), PROVIDER, False

    on = on or date.today()
    fetcher = fetcher or _http_fetch

    hit = cached_rate(db, base, quote, on)
    if hit:
        return Decimal(str(hit["rate"])), hit["rate_date"], hit["provider"], False

    try:
        rate, served_date = fetcher(base, quote, on)
        store_rate(db, base, quote, rate, served_date)
        # The API answers with the last published day, which at a weekend
        # is earlier than the day asked for. That is not staleness — it
        # is the rate that exists — so it is not flagged as such.
        return rate, served_date, PROVIDER, False
    except Exception as exc:
        logger.warning("fx: live rate %s/%s unavailable (%s); falling back to cache",
                       base, quote, exc)

    fallback = latest_cached_rate(db, base, quote)
    if fallback:
        return (Decimal(str(fallback["rate"])), fallback["rate_date"],
                fallback["provider"], True)

    raise RateUnavailable(
        f"No rate for {base}/{quote}: the rate service is unreachable and "
        "nothing has been cached for this pair yet.")


def convert(db: Session, amount: Decimal, from_currency: str, to_currency: str,
            on: date = None, fetcher=None):
    """Convert an amount, returning the figure and the rate behind it.

    Returns (converted, rate, rate_date, provider, is_stale). Conversion
    goes through EUR when neither side is EUR, because EUR is the
    benchmark and a pivot keeps one rate per currency rather than one
    per pair.
    """
    amount = Decimal(str(amount))
    if from_currency == to_currency:
        return amount, Decimal("1"), on or date.today(), PROVIDER, False

    if from_currency == BENCHMARK or to_currency == BENCHMARK:
        rate, rate_date, provider, stale = get_rate(
            db, from_currency, to_currency, on, fetcher)
        converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return converted, rate, rate_date, provider, stale

    # Neither side is the benchmark: go through it.
    to_eur, d1, p1, s1 = get_rate(db, from_currency, BENCHMARK, on, fetcher)
    from_eur, d2, p2, s2 = get_rate(db, BENCHMARK, to_currency, on, fetcher)
    rate = to_eur * from_eur
    converted = (amount * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return converted, rate, min(d1, d2), p1, (s1 or s2)
