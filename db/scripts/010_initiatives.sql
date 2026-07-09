-- ============================================================================
-- 010_initiatives.sql — network directory of place-based Erdpuls initiatives
-- ============================================================================
-- Backs the network landing (`/`, templates/network.html) with a table instead
-- of hardcoded HTML / a config module (open thread #3), and provides the store
-- for the dashboard "register an initiative" flow (open thread #4).
--
-- IDEMPOTENT: safe to run more than once (CREATE ... IF NOT EXISTS,
-- INSERT ... ON CONFLICT DO NOTHING, guarded GRANT). Run against the
-- erdpuls_threshold schema on the live PG16 database `ubec_erdpuls`.
--
--   psql -d ubec_erdpuls -v ON_ERROR_STOP=1 -f db/scripts/010_initiatives.sql
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS erdpuls_threshold;
SET search_path TO erdpuls_threshold;
-- Install uuid-ossp INTO erdpuls_threshold (search_path is already set), matching
-- db/schema_complete.sql. Ordering matters: creating the extension before the
-- SET would land uuid_generate_v4() in public, which the erdpuls_threshold-only
-- search_path then can't resolve. No-op when the extension already exists.
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE IF NOT EXISTS erdpuls_threshold.initiatives (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    slug        VARCHAR(80)  NOT NULL UNIQUE,
    name        VARCHAR(255) NOT NULL,
    location    VARCHAR(255),
    status      VARCHAR(20)  NOT NULL DEFAULT 'coming_soon',
    flagship    BOOLEAN      NOT NULL DEFAULT FALSE,
    has_page    BOOLEAN      NOT NULL DEFAULT FALSE,
    route       VARCHAR(255),           -- internal path override (e.g. Müllrose -> /muellrose)
    url         VARCHAR(255),           -- external URL (used when has_page = FALSE)
    blurb_en    TEXT NOT NULL,
    blurb_de    TEXT,
    blurb_pl    TEXT,
    blurb_uk    TEXT,
    sort_order  INTEGER     NOT NULL DEFAULT 100,
    created_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP   DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT initiatives_status_check CHECK (status IN ('active','forming','coming_soon')),
    CONSTRAINT initiatives_slug_format  CHECK (slug ~ '^[a-z0-9-]+$'),
    CONSTRAINT initiatives_name_length  CHECK (char_length(name) >= 2 AND char_length(name) <= 255)
);

CREATE INDEX IF NOT EXISTS idx_initiatives_status ON erdpuls_threshold.initiatives(status);
CREATE INDEX IF NOT EXISTS idx_initiatives_sort   ON erdpuls_threshold.initiatives(sort_order, name);

-- Seed the flagship reference implementation (kept intact at /muellrose).
INSERT INTO erdpuls_threshold.initiatives
    (slug, name, location, status, flagship, has_page, route,
     blurb_en, blurb_de, blurb_pl, blurb_uk, sort_order)
VALUES
    ('muellrose', 'Erdpuls Müllrose', 'Müllrose, Brandenburg · Naturpark Schlaubetal',
     'active', TRUE, TRUE, '/muellrose',
     'Center for Sustainability Literacy, Citizen Science & Reciprocal Economics.',
     'Zentrum für Nachhaltigkeitsbildung, Citizen Science und reziproke Ökonomie.',
     'Centrum edukacji na rzecz zrównoważonego rozwoju, nauki obywatelskiej i ekonomii wzajemności.',
     'Центр екологічної грамотності, громадянської науки та економіки взаємності.',
     10)
ON CONFLICT (slug) DO NOTHING;

-- Grant to the application role, only if it exists (idempotent, env-safe).
-- USAGE on the schema is already present on the live DB (the app reads other
-- tables); included here so the migration is self-sufficient on a fresh DB.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'ubec_erdpuls_app') THEN
        GRANT USAGE ON SCHEMA erdpuls_threshold TO ubec_erdpuls_app;
        GRANT SELECT, INSERT, UPDATE, DELETE
            ON erdpuls_threshold.initiatives TO ubec_erdpuls_app;
    END IF;
END
$$;
