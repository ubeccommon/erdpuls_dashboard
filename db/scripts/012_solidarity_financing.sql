-- 012_solidarity_financing.sql
-- Solidarity Financing 2026 (working title) — Michel Garand
-- Native Erdpuls module: prototype tables in their own `solidarity` schema
-- inside the existing ubec_erdpuls database. Ported from the standalone
-- schema.sql v0.1 (2026-08-10); design invariants unchanged:
--   1. No child data: no table, column, or comment refers to any child.
--   2. Every amount carries a status (ENUM) — untagged is unrepresentable.
--   3. Pledge anonymity by separation: pledges reference tokens; the
--      token -> household mapping is its own table, populatable or left
--      empty with the mapping on paper. Report views never join it.
--   4. Currency UAH, NUMERIC(12,2); EUR only as a stated-rate note.
--   5. Records and computes; moves no money.
-- Auth is Erdpuls's own (erdpuls_threshold.users + roles); this schema
-- holds no user table.
-- Apply:  psql -U erdpuls -d ubec_erdpuls -f db/scripts/012_solidarity_financing.sql
-- Rollback: DROP SCHEMA solidarity CASCADE;

BEGIN;

CREATE SCHEMA IF NOT EXISTS solidarity;

CREATE TYPE solidarity.figure_status AS ENUM ('estimate', 'budget', 'pledge', 'settled');
CREATE TYPE solidarity.round_state   AS ENUM ('open', 'closed', 'stopped');

CREATE TABLE solidarity.camp_session (
    id         SERIAL PRIMARY KEY,
    label      TEXT NOT NULL UNIQUE,
    days       INTEGER CHECK (days > 0),
    adopted_on DATE,
    note       TEXT NOT NULL DEFAULT ''
);

CREATE TABLE solidarity.budget_line (
    id             SERIAL PRIMARY KEY,
    session_id     INTEGER NOT NULL REFERENCES solidarity.camp_session(id) ON DELETE CASCADE,
    line_item      TEXT NOT NULL,
    amount_uah     NUMERIC(12,2) NOT NULL CHECK (amount_uah >= 0),
    status         solidarity.figure_status NOT NULL,
    is_transfer_in BOOLEAN NOT NULL DEFAULT FALSE,
    note           TEXT NOT NULL DEFAULT ''
);

CREATE TABLE solidarity.household (
    id           SERIAL PRIMARY KEY,
    display_name TEXT NOT NULL,
    note         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE solidarity.bidding_round (
    id         SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES solidarity.camp_session(id) ON DELETE CASCADE,
    round_no   INTEGER NOT NULL CHECK (round_no >= 1),
    held_on    DATE,
    state      solidarity.round_state NOT NULL DEFAULT 'open',
    note       TEXT NOT NULL DEFAULT '',
    UNIQUE (session_id, round_no)
);

CREATE TABLE solidarity.round_token (
    id         SERIAL PRIMARY KEY,
    session_id INTEGER NOT NULL REFERENCES solidarity.camp_session(id) ON DELETE CASCADE,
    token      TEXT NOT NULL,
    UNIQUE (session_id, token)
);

CREATE TABLE solidarity.token_mapping (
    token_id     INTEGER PRIMARY KEY REFERENCES solidarity.round_token(id) ON DELETE CASCADE,
    household_id INTEGER NOT NULL REFERENCES solidarity.household(id) ON DELETE CASCADE
);

CREATE TABLE solidarity.pledge (
    id         SERIAL PRIMARY KEY,
    round_id   INTEGER NOT NULL REFERENCES solidarity.bidding_round(id) ON DELETE CASCADE,
    token_id   INTEGER NOT NULL REFERENCES solidarity.round_token(id),
    amount_uah NUMERIC(12,2) NOT NULL CHECK (amount_uah >= 0),
    status     solidarity.figure_status NOT NULL DEFAULT 'pledge',
    note       TEXT NOT NULL DEFAULT '',
    UNIQUE (round_id, token_id)
);

CREATE TABLE solidarity.supporter (
    id           SERIAL PRIMARY KEY,
    token        TEXT NOT NULL UNIQUE,
    display_name TEXT,
    note         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE solidarity.contribution (
    id           SERIAL PRIMARY KEY,
    supporter_id INTEGER NOT NULL REFERENCES solidarity.supporter(id) ON DELETE CASCADE,
    period       TEXT NOT NULL CHECK (period ~ '^\d{4}-\d{2}$'),
    amount_uah   NUMERIC(12,2) NOT NULL CHECK (amount_uah >= 0),
    status       solidarity.figure_status NOT NULL,
    note         TEXT NOT NULL DEFAULT ''
);

CREATE TABLE solidarity.settlement (
    id                     SERIAL PRIMARY KEY,
    session_id             INTEGER NOT NULL UNIQUE REFERENCES solidarity.camp_session(id) ON DELETE CASCADE,
    drawn_up_on            DATE NOT NULL DEFAULT CURRENT_DATE,
    received_uah           NUMERIC(12,2) NOT NULL CHECK (received_uah >= 0),
    outstanding_uah        NUMERIC(12,2) NOT NULL CHECK (outstanding_uah >= 0),
    spent_uah              NUMERIC(12,2) NOT NULL CHECK (spent_uah >= 0),
    to_infrastructure_uah  NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (to_infrastructure_uah >= 0),
    carried_by_hosts_uah   NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (carried_by_hosts_uah >= 0),
    status                 solidarity.figure_status NOT NULL DEFAULT 'settled',
    note                   TEXT NOT NULL DEFAULT ''
);

CREATE VIEW solidarity.v_session_budget AS
SELECT s.id AS session_id, s.label,
       COALESCE(SUM(b.amount_uah) FILTER (WHERE NOT b.is_transfer_in), 0) AS cost_uah,
       COALESCE(SUM(b.amount_uah) FILTER (WHERE b.is_transfer_in), 0)     AS cover_uah,
       COALESCE(SUM(b.amount_uah) FILTER (WHERE NOT b.is_transfer_in), 0)
     - COALESCE(SUM(b.amount_uah) FILTER (WHERE b.is_transfer_in), 0)     AS remainder_uah
FROM solidarity.camp_session s
LEFT JOIN solidarity.budget_line b ON b.session_id = s.id
GROUP BY s.id, s.label;

CREATE VIEW solidarity.v_round_totals AS
SELECT r.id AS round_id, r.session_id, r.round_no, r.state,
       COUNT(p.id)                    AS pledge_count,
       COALESCE(SUM(p.amount_uah), 0) AS total_pledged_uah,
       vb.remainder_uah,
       vb.remainder_uah - COALESCE(SUM(p.amount_uah), 0) AS gap_uah
FROM solidarity.bidding_round r
JOIN solidarity.v_session_budget vb ON vb.session_id = r.session_id
LEFT JOIN solidarity.pledge p ON p.round_id = r.id
GROUP BY r.id, r.session_id, r.round_no, r.state, vb.remainder_uah;

CREATE VIEW solidarity.v_period_summary AS
SELECT period,
       COUNT(*) AS contributions,
       COALESCE(SUM(amount_uah) FILTER (WHERE status = 'pledge'), 0)  AS pledged_uah,
       COALESCE(SUM(amount_uah) FILTER (WHERE status = 'settled'), 0) AS settled_uah
FROM solidarity.contribution
GROUP BY period;

COMMIT;
