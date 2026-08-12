-- 015_offering_ukrainian.sql
-- Erdpuls — add Ukrainian to offerings, matching the site's four languages.
-- The interface already speaks EN/DE/PL/UK and initiatives already carry
-- blurb_uk; offerings stopped at PL. This closes that gap.
--
-- Three things are needed, not one: the columns, the length checks that
-- every other language column already carries, and the delivery_language
-- CHECK constraint, which whitelists the allowed codes and would other-
-- wise reject 'uk' at insert time regardless of what the form offers.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/015_offering_ukrainian.sql
-- Rollback:
--   ALTER TABLE erdpuls_threshold.offerings
--     DROP COLUMN title_uk, DROP COLUMN description_uk,
--     DROP CONSTRAINT chk_title_uk_length, DROP CONSTRAINT chk_description_uk_length,
--     DROP CONSTRAINT offerings_delivery_language_check;
--   ALTER TABLE erdpuls_threshold.offerings ADD CONSTRAINT offerings_delivery_language_check
--     CHECK (delivery_language <@ ARRAY['en','de','pl']::varchar(50)[]);

BEGIN;

ALTER TABLE erdpuls_threshold.offerings
    ADD COLUMN IF NOT EXISTS title_uk VARCHAR(255),
    ADD COLUMN IF NOT EXISTS description_uk TEXT;

COMMENT ON COLUMN erdpuls_threshold.offerings.title_uk IS
    'Ukrainian title; falls back to English when empty.';

-- Length checks, matching the existing de/pl columns.
ALTER TABLE erdpuls_threshold.offerings
    DROP CONSTRAINT IF EXISTS chk_title_uk_length,
    DROP CONSTRAINT IF EXISTS chk_description_uk_length;

ALTER TABLE erdpuls_threshold.offerings
    ADD CONSTRAINT chk_title_uk_length
        CHECK (title_uk IS NULL OR (char_length(title_uk) >= 3 AND char_length(title_uk) <= 255)),
    ADD CONSTRAINT chk_description_uk_length
        CHECK (description_uk IS NULL OR (char_length(description_uk) >= 50 AND char_length(description_uk) <= 5000));

-- Allow 'uk' as a delivery language.
ALTER TABLE erdpuls_threshold.offerings
    DROP CONSTRAINT IF EXISTS offerings_delivery_language_check;

ALTER TABLE erdpuls_threshold.offerings
    ADD CONSTRAINT offerings_delivery_language_check
        CHECK (delivery_language <@ ARRAY['en','de','pl','uk']::varchar(50)[]);

COMMIT;
