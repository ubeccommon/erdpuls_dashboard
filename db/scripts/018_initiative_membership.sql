-- 018_initiative_membership.sql
-- Erdpuls — who belongs to which place-based initiative, and in what role.
--
-- Until now the global role decided everything: any facilitator could open
-- any initiative's solidarity module, and any creator could attach an
-- offering to any initiative. That was tolerable while one camp used the
-- module. With several places it is not: a facilitator in Müllrose has no
-- business inside Verkhovyna's budgets.
--
-- Two role systems now sit side by side, and they answer different
-- questions:
--   * The global role (users.role) answers WHAT a person may do at all —
--     create offerings, moderate, administer.
--   * The membership role answers WHERE they may do it.
-- Both must allow an action. Membership never grants a capability the
-- global role withholds; it only narrows where that capability applies.
--
-- Membership roles, deliberately few:
--   member      — belongs to the initiative; no financing powers.
--   facilitator — may run financing here: budgets, rounds, settlements.
--   steward     — may also manage this initiative's membership.
--
-- Platform admins and moderators are NOT listed as members. Their
-- oversight is global and outlives any one place; requiring them to add
-- themselves everywhere would make the record of who actually belongs to
-- an initiative less true, not more.
--
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/018_initiative_membership.sql
-- Rollback: DROP TABLE erdpuls_threshold.initiative_members;

BEGIN;

CREATE TABLE IF NOT EXISTS erdpuls_threshold.initiative_members (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    initiative_id UUID NOT NULL REFERENCES erdpuls_threshold.initiatives(id) ON DELETE CASCADE,
    user_id       UUID NOT NULL REFERENCES erdpuls_threshold.users(id) ON DELETE CASCADE,
    role          VARCHAR(20) NOT NULL DEFAULT 'member',
    added_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    added_by      UUID REFERENCES erdpuls_threshold.users(id) ON DELETE SET NULL,
    note          TEXT NOT NULL DEFAULT '',
    CONSTRAINT chk_initiative_member_role
        CHECK (role IN ('member', 'facilitator', 'steward')),
    CONSTRAINT uq_initiative_member UNIQUE (initiative_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_initiative_members_user
    ON erdpuls_threshold.initiative_members (user_id);
CREATE INDEX IF NOT EXISTS idx_initiative_members_initiative
    ON erdpuls_threshold.initiative_members (initiative_id);

COMMENT ON TABLE erdpuls_threshold.initiative_members IS
    'Who belongs to which initiative and in what role. Narrows where a global role applies; never widens what it permits.';

COMMIT;
