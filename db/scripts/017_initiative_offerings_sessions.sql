-- 017_initiative_offerings_sessions.sql
-- Erdpuls — an offering belongs to a place-based initiative, and a
-- solidarity session inherits that place through it.
--
-- Chain: initiative (a place) -> offering (what is on offer, priced)
--        -> session (how it is financed).
--
-- Both columns are nullable, for different reasons:
--   * offerings.initiative_id — offerings already exist without one, and
--     network-level offerings that belong to no single place are
--     legitimate. An offering with no initiative simply cannot be
--     financed through a solidarity session, since a session must know
--     where it happens.
--   * camp_session.initiative_id — stored directly rather than read
--     through the offering, so a session keeps its place when its
--     offering is deleted. A settlement account must outlive the listing
--     AND still say where the cycle happened.
--
-- ON DELETE RESTRICT on the session side: an initiative that has
-- financing records cannot be deleted out from under them.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/017_initiative_offerings_sessions.sql
-- Rollback:
--   ALTER TABLE solidarity.camp_session DROP COLUMN initiative_id;
--   ALTER TABLE erdpuls_threshold.offerings DROP COLUMN initiative_id;

BEGIN;

ALTER TABLE erdpuls_threshold.offerings
    ADD COLUMN IF NOT EXISTS initiative_id UUID
        REFERENCES erdpuls_threshold.initiatives(id) ON DELETE SET NULL;

ALTER TABLE solidarity.camp_session
    ADD COLUMN IF NOT EXISTS initiative_id UUID
        REFERENCES erdpuls_threshold.initiatives(id) ON DELETE RESTRICT;

-- Backfill any existing session from its offering, where one exists.
UPDATE solidarity.camp_session cs
   SET initiative_id = o.initiative_id
  FROM erdpuls_threshold.offerings o
 WHERE o.id = cs.offering_id
   AND cs.initiative_id IS NULL
   AND o.initiative_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_offerings_initiative
    ON erdpuls_threshold.offerings (initiative_id);
CREATE INDEX IF NOT EXISTS idx_camp_session_initiative
    ON solidarity.camp_session (initiative_id);

COMMENT ON COLUMN erdpuls_threshold.offerings.initiative_id IS
    'Place-based initiative this offering belongs to. Null means network-level; such an offering cannot be financed through a solidarity session.';
COMMENT ON COLUMN solidarity.camp_session.initiative_id IS
    'Where this financing cycle happens. Held directly so the record survives deletion of its offering.';

COMMIT;
