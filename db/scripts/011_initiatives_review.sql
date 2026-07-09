-- ============================================================================
-- 011_initiatives_review.sql — propose → review → publish workflow
-- ============================================================================
-- Adds a moderation gate to the initiatives directory: proposals are submitted
-- publicly (/initiatives/start) as UNPUBLISHED, and only appear on `/` after an
-- admin approves them (/admin/initiatives). "Reject" is a delete.
--
-- IDEMPOTENT: ADD COLUMN IF NOT EXISTS + a flagship-scoped UPDATE that is safe
-- to re-run. Table-level grants already cover new columns, so no re-GRANT.
--
--   psql -d ubec_erdpuls -v ON_ERROR_STOP=1 -f db/scripts/011_initiatives_review.sql
-- ============================================================================

SET search_path TO erdpuls_threshold;

ALTER TABLE erdpuls_threshold.initiatives
    ADD COLUMN IF NOT EXISTS is_published    BOOLEAN NOT NULL DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS submitter_name  VARCHAR(255),
    ADD COLUMN IF NOT EXISTS submitter_email VARCHAR(255);

-- Publish rows that predate this column so they don't vanish from `/`.
-- Scoped to the flagship (the only pre-review live row: the Müllrose seed).
-- Safe to re-run; does NOT touch later public proposals (they aren't flagship).
UPDATE erdpuls_threshold.initiatives
    SET is_published = TRUE
    WHERE flagship = TRUE AND is_published = FALSE;

-- Pending proposals are the review queue; index the common filter.
CREATE INDEX IF NOT EXISTS idx_initiatives_published
    ON erdpuls_threshold.initiatives(is_published, sort_order, name);
