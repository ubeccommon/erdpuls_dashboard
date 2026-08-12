-- 014_solidarity_offering_link.sql
-- Solidarity Financing 2026 (working title) — Michel Garand
-- Lets an Erdpuls offering be financed through the solidarity module:
-- one offering, at most one session; a session may also stand alone.
--
-- What this link does NOT do, deliberately:
--   * It does not copy money. Offering costs are EUR; the session budget
--     is UAH. No conversion happens here or anywhere else in the module:
--     the facilitator enters the UAH budget, and the offering's EUR
--     figure travels only as a stated-rate reference note.
--   * It does not join contributors to pledges. The threshold model
--     records who contributed; the bidding round is anonymous by design.
--     The two remain separate ledgers that never reconcile per person.
--   * It carries no child data. The link references an offering, nothing
--     about who attends it.
--
-- ON DELETE SET NULL: deleting an offering must not delete a financing
-- record. The session survives, unlinked, with its budget and settlement
-- intact — the account of what happened outlives the listing.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/014_solidarity_offering_link.sql
-- Rollback: ALTER TABLE solidarity.camp_session DROP COLUMN offering_id;

BEGIN;

ALTER TABLE solidarity.camp_session
    ADD COLUMN IF NOT EXISTS offering_id UUID
        REFERENCES erdpuls_threshold.offerings(id) ON DELETE SET NULL;

CREATE UNIQUE INDEX IF NOT EXISTS camp_session_offering_id_key
    ON solidarity.camp_session (offering_id) WHERE offering_id IS NOT NULL;

COMMENT ON COLUMN solidarity.camp_session.offering_id IS
    'Optional Erdpuls offering financed by this session. No money or identity crosses this link.';

COMMIT;
