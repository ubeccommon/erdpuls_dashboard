-- 019_session_budget_shared.sql
-- Solidarity Financing — the open budget can be shown to the families
-- taking part, when the facilitator decides to show it.
--
-- Step one of the bidding-round procedure is "lay the budget open": a
-- family cannot pledge against figures it has not seen. On paper that is
-- a sheet on the table. This column is its equivalent on screen.
--
-- Default FALSE, deliberately. Nothing about a session becomes visible
-- to anyone outside the facilitators until someone decides it should.
-- The project's working default is that nothing publishes or circulates
-- before the hosts have read it and agreed, and a default of TRUE would
-- quietly override that for every session ever created.
--
-- What sharing does NOT do: it does not make the session public. The
-- view is for signed-in people registered for the linked offering, or
-- members of the initiative. It shows sums and budget lines only — never
-- a token, never a per-family pledge — and carries no pledge form. The
-- round is still held in a room; this is the sheet on the table, not
-- the box the slips go into.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/019_session_budget_shared.sql
-- Rollback: ALTER TABLE solidarity.camp_session DROP COLUMN budget_shared;

BEGIN;

ALTER TABLE solidarity.camp_session
    ADD COLUMN IF NOT EXISTS budget_shared BOOLEAN NOT NULL DEFAULT FALSE;

COMMENT ON COLUMN solidarity.camp_session.budget_shared IS
    'Whether the open budget is shown to participants of the linked offering. Never public; sums and budget lines only.';

COMMIT;
