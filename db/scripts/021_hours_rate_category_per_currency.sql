-- 021_hours_rate_category_per_currency.sql
-- Erdpuls — a category may hold one rate per currency.
--
-- Migration 020 gave rates a currency, but left hours_rates.category
-- globally unique. That meant "garden_labor" could be priced in euro OR
-- in hryvnia, never both — which defeats the point: the same kind of
-- work is done in both places, and is worth what it is worth in each.
--
-- The uniqueness that is actually wanted is one rate per category PER
-- CURRENCY, so this replaces the constraint rather than dropping it.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/021_hours_rate_category_per_currency.sql
-- Rollback:
--   ALTER TABLE erdpuls_threshold.hours_rates DROP CONSTRAINT uq_hours_rate_category_currency;
--   ALTER TABLE erdpuls_threshold.hours_rates ADD CONSTRAINT hours_rates_category_key UNIQUE (category);
--   (the rollback fails if two currencies hold the same category — delete one first)

BEGIN;

DELETE FROM erdpuls_threshold.hours_rates a
      USING erdpuls_threshold.hours_rates b
      WHERE a.ctid < b.ctid
        AND a.category = b.category
        AND a.currency = b.currency;

ALTER TABLE erdpuls_threshold.hours_rates
    DROP CONSTRAINT IF EXISTS hours_rates_category_key;

ALTER TABLE erdpuls_threshold.hours_rates
    DROP CONSTRAINT IF EXISTS uq_hours_rate_category_currency;

ALTER TABLE erdpuls_threshold.hours_rates
    ADD CONSTRAINT uq_hours_rate_category_currency UNIQUE (category, currency);

COMMIT;
