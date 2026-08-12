-- 013_solidarity_session_description.sql
-- Solidarity Financing 2026 (working title) — Michel Garand
-- Adds the session description: what the session offers, in plain words,
-- for the families reading the open budget beside it.
--
-- Why a column and not a note: the budget answers "what does it cost";
-- the description answers "what is it" — the two are read together when
-- the budget is laid open, and a family deciding what it can carry is
-- deciding about the thing described here.
--
-- No child data: the description covers what the session offers — days,
-- activities, meals, what a family should expect. It does not name,
-- count, date, or otherwise identify any child, and no field here
-- invites it.
--
-- Language: English settles first. Ukrainian rendering follows as a
-- separate column when the wording is settled and Vasyl has reviewed;
-- deliberately not stubbed out here.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/013_solidarity_session_description.sql
-- Rollback: ALTER TABLE solidarity.camp_session DROP COLUMN description;

BEGIN;

ALTER TABLE solidarity.camp_session
    ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT '';

COMMENT ON COLUMN solidarity.camp_session.description IS
    'What the session offers, in plain words, read alongside the open budget. No child data.';

COMMIT;
