-- 020_rates_per_currency.sql
-- Erdpuls — token and hours rates gain a currency.
--
-- Token and hours contributions were euro-only because their rates were:
-- tokens_per_eur and eur_per_hour say what a token and an hour are worth
-- IN EURO. Offering those contribution types on a hryvnia offering meant
-- either refusing them, or applying a euro rate to hryvnia without
-- saying so. The first is what the application did; the second is the
-- thing it must never do.
--
-- With a currency on each rate, both types can be offered in any
-- currency for which someone has set a rate. The column names stay as
-- they are: renaming live columns used across the API and admin screens
-- is a separate, riskier change, and the comments below record that the
-- names are now historical.
--
-- NO RATES ARE INVENTED HERE. Existing rows are marked EUR, because that
-- is what they always were. A rate in any other currency has to be
-- entered by a person who knows what a token and an hour are worth
-- there — that is a decision about value, not a data migration.
-- Until such a rate exists, those contribution types show as
-- unavailable in that currency, with the reason stated.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/020_rates_per_currency.sql
-- Rollback:
--   ALTER TABLE erdpuls_threshold.token_rates DROP COLUMN currency;
--   ALTER TABLE erdpuls_threshold.hours_rates DROP COLUMN currency;

BEGIN;

ALTER TABLE erdpuls_threshold.token_rates
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'EUR';
ALTER TABLE erdpuls_threshold.hours_rates
    ADD COLUMN IF NOT EXISTS currency VARCHAR(3) NOT NULL DEFAULT 'EUR';

ALTER TABLE erdpuls_threshold.token_rates
    DROP CONSTRAINT IF EXISTS chk_token_rate_currency;
ALTER TABLE erdpuls_threshold.token_rates
    ADD CONSTRAINT chk_token_rate_currency CHECK (currency IN ('EUR', 'PLN', 'UAH'));

ALTER TABLE erdpuls_threshold.hours_rates
    DROP CONSTRAINT IF EXISTS chk_hours_rate_currency;
ALTER TABLE erdpuls_threshold.hours_rates
    ADD CONSTRAINT chk_hours_rate_currency CHECK (currency IN ('EUR', 'PLN', 'UAH'));

CREATE INDEX IF NOT EXISTS idx_token_rates_currency
    ON erdpuls_threshold.token_rates (currency, effective_from DESC);
CREATE INDEX IF NOT EXISTS idx_hours_rates_currency
    ON erdpuls_threshold.hours_rates (currency, category);

COMMENT ON COLUMN erdpuls_threshold.token_rates.tokens_per_eur IS
    'Tokens per one unit of the row''s currency (see currency). Name kept for API compatibility.';
COMMENT ON COLUMN erdpuls_threshold.hours_rates.eur_per_hour IS
    'Value of one hour in the row''s currency (see currency). Name kept for API compatibility.';

COMMIT;
