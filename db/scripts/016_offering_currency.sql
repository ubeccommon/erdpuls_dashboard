-- 016_offering_currency.sql
-- Erdpuls — an offering declares its own currency.
--
-- The application was built EUR-only: the contribution column is named
-- amount_eur, token rates are tokens_per_eur, hours rates are
-- eur_per_hour, and templates print a hard euro sign. This migration
-- does NOT rename those; renaming a live column used across the API and
-- admin screens is a separate, riskier change. Instead:
--
--   * offerings.currency says what an offering's own figures mean —
--     its cost lines, its threshold, and the contributions made to it.
--   * contributions.amount_eur therefore holds an amount in the
--     OFFERING's currency. The column name is now a historical
--     misnomer, which is recorded here rather than left to be
--     discovered: see the column comment below.
--   * Nothing is converted. A PLN offering's figures are never added
--     to a EUR offering's; totals are grouped by currency, never summed
--     across them.
--
-- Token and hours contributions stay EUR-only, because their rates
-- (tokens_per_eur, eur_per_hour) are denominated in euro. Offering them
-- on a UAH offering would silently apply a euro rate to hryvnia. The
-- application blocks that rather than guessing; per-currency rates are a
-- later decision, and one for the participants and an accountant.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/016_offering_currency.sql
-- Rollback:
--   ALTER TABLE erdpuls_threshold.offerings DROP COLUMN currency;

BEGIN;

ALTER TABLE erdpuls_threshold.offerings
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'EUR';

ALTER TABLE erdpuls_threshold.offerings
    DROP CONSTRAINT IF EXISTS chk_offering_currency;

ALTER TABLE erdpuls_threshold.offerings
    ADD CONSTRAINT chk_offering_currency
        CHECK (currency IN ('EUR', 'PLN', 'UAH'));

COMMENT ON COLUMN erdpuls_threshold.offerings.currency IS
    'Currency of this offering''s costs, threshold and contributions. Figures are never converted between currencies.';

COMMENT ON COLUMN erdpuls_threshold.contributions.amount_eur IS
    'Amount in the OFFERING''s currency (see offerings.currency), not necessarily euro. Name kept for API compatibility.';

COMMIT;
