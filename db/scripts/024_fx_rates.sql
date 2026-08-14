-- 024_fx_rates.sql
-- Erdpuls — exchange rates, cached, and frozen onto each contribution.
--
-- EUR is the benchmark. Rates come from Frankfurter (api.frankfurter.dev),
-- which blends daily reference rates from 84 central banks and covers
-- EUR, PLN and UAH among 201 currencies. No API key; no quota.
--
-- Two tables' worth of thinking, in one:
--
-- 1. fx_rate caches one row per (base, quote, rate_date, provider). A
--    past date is fetched once and never again: a rate that was true on
--    a day stays true for that day, and re-fetching could only introduce
--    drift. This is also what makes the ledger reproducible offline.
--
-- 2. The contribution columns FREEZE the rate at the moment of giving.
--    A gift of 50 EUR to a hryvnia offering records the amount given,
--    its currency, the rate used, the date that rate belongs to, and who
--    published it. The converted figure is stored too, not recomputed:
--    if it were recomputed, yesterday's settled total would move today,
--    which is precisely what the status enum exists to prevent.
--
-- amount_converted is expressed in the OFFERING's currency, so totals
-- can be summed without asking the rate table anything at read time.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/024_fx_rates.sql
-- Rollback:
--   ALTER TABLE erdpuls_threshold.contributions
--     DROP COLUMN amount_converted, DROP COLUMN fx_rate,
--     DROP COLUMN fx_rate_date, DROP COLUMN fx_provider;
--   DROP TABLE erdpuls_threshold.fx_rate;

BEGIN;

CREATE TABLE IF NOT EXISTS erdpuls_threshold.fx_rate (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    base       VARCHAR(3) NOT NULL,
    quote      VARCHAR(3) NOT NULL,
    rate       NUMERIC(20,10) NOT NULL CHECK (rate > 0),
    rate_date  DATE NOT NULL,
    provider   VARCHAR(40) NOT NULL DEFAULT 'frankfurter',
    fetched_at TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_fx_rate UNIQUE (base, quote, rate_date, provider)
);

CREATE INDEX IF NOT EXISTS idx_fx_rate_lookup
    ON erdpuls_threshold.fx_rate (base, quote, rate_date DESC);

COMMENT ON TABLE erdpuls_threshold.fx_rate IS
    'Cached daily exchange rates. A past date is fetched once; rates for a given day never change.';

-- The rate as it stood when the contribution was made.
ALTER TABLE erdpuls_threshold.contributions
    ADD COLUMN IF NOT EXISTS amount_converted NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS fx_rate          NUMERIC(20,10),
    ADD COLUMN IF NOT EXISTS fx_rate_date     DATE,
    ADD COLUMN IF NOT EXISTS fx_provider      VARCHAR(40);

-- Contributions already in the offering's own currency need no rate:
-- the converted figure is the figure.
UPDATE erdpuls_threshold.contributions c
   SET amount_converted = c.amount_eur
  FROM erdpuls_threshold.offerings o
 WHERE o.id = c.offering_id
   AND c.amount_converted IS NULL
   AND c.currency = o.currency;

COMMENT ON COLUMN erdpuls_threshold.contributions.amount_converted IS
    'The gift expressed in the offering''s currency, frozen at the rate below. Never recomputed.';
COMMENT ON COLUMN erdpuls_threshold.contributions.fx_rate IS
    'Rate used at the moment of giving. NULL when the gift was already in the offering''s currency.';

COMMIT;
