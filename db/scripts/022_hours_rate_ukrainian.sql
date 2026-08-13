-- 022_hours_rate_ukrainian.sql
-- Erdpuls — hours-rate descriptions gain Ukrainian.
--
-- The rate categories carry descriptions in EN, DE and PL. Ukrainian was
-- missing, which is the wrong gap to leave: the first rates anyone will
-- set in a non-euro currency are the Carpathian ones, and the people
-- reading "what counts as skilled work here" read Ukrainian.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/022_hours_rate_ukrainian.sql
-- Rollback: ALTER TABLE erdpuls_threshold.hours_rates DROP COLUMN description_uk;

BEGIN;

ALTER TABLE erdpuls_threshold.hours_rates
    ADD COLUMN IF NOT EXISTS description_uk TEXT;

COMMENT ON COLUMN erdpuls_threshold.hours_rates.description_uk IS
    'Ukrainian description of the category; falls back to English when empty.';

COMMIT;
