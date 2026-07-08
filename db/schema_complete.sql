-- ============================================================================
-- Erdpuls Collective Threshold Model — erdpuls_threshold schema (complete init)
-- ============================================================================
-- Reconstructed from the authoritative schema documentation
-- (erdpuls_schema_documentation_20260129_054507.md — 9 tables, 93 columns, 6 FKs,
-- 22 indexes, 1 trigger, custom functions) combined with the repo's db/scripts for
-- exact CHECK expressions, function bodies, and seed data.
--
-- Why this file exists: the repo's schema.sql + committed migrations do NOT
-- reproduce the documented DB. Three pieces are created by NO script and are
-- reconstructed here from the doc:
--   1. the entire `users` table (+ constraints/indexes)
--   2. offerings.creator_id (+ FK -> users) and organizer_name/email/phone
--   3. hours_rates.description_de / description_pl
--
-- Canonical fresh-install schema. Run ONCE against an empty erdpuls_threshold schema.
-- Verified against PostgreSQL 16: 9 tables / 93 columns / 6 FKs / 22 indexes / 1 trigger.
-- ============================================================================

CREATE SCHEMA IF NOT EXISTS erdpuls_threshold;
SET search_path TO erdpuls_threshold;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid() for contribution_contacts

-- ============================================================================
-- roles  (RBAC reference table)  [from 006_role_system.sql]
-- ============================================================================
CREATE TABLE erdpuls_threshold.roles (
    name                  VARCHAR(50) PRIMARY KEY,
    level                 INTEGER NOT NULL,
    description           TEXT,
    description_de        TEXT,
    description_pl        TEXT,
    can_create_offering   BOOLEAN DEFAULT FALSE,
    can_publish_direct    BOOLEAN DEFAULT FALSE,
    can_approve_offerings BOOLEAN DEFAULT FALSE,
    can_manage_users      BOOLEAN DEFAULT FALSE,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO erdpuls_threshold.roles
    (name, level, description, description_de, description_pl,
     can_create_offering, can_publish_direct, can_approve_offerings, can_manage_users)
VALUES
    ('member',      10,  'Can participate in and contribute to offerings',  'Kann an Angeboten teilnehmen und beitragen',                        'Może uczestniczyć i wspierać oferty',                      FALSE, FALSE, FALSE, FALSE),
    ('creator',     20,  'Can create offerings (require approval)',         'Kann Angebote erstellen (erfordert Genehmigung)',                   'Może tworzyć oferty (wymagają zatwierdzenia)',             TRUE,  FALSE, FALSE, FALSE),
    ('facilitator', 30,  'Trusted creator - offerings published directly',  'Vertrauenswürdiger Ersteller - Angebote werden direkt veröffentlicht','Zaufany twórca - oferty publikowane bezpośrednio',        TRUE,  TRUE,  FALSE, FALSE),
    ('moderator',   50,  'Can approve offerings and manage community',      'Kann Angebote genehmigen und Community verwalten',                  'Może zatwierdzać oferty i zarządzać społecznością',        TRUE,  TRUE,  TRUE,  FALSE),
    ('admin',       100, 'Full system access',                              'Voller Systemzugriff',                                              'Pełny dostęp do systemu',                                  TRUE,  TRUE,  TRUE,  TRUE);

-- ============================================================================
-- users  (RECONSTRUCTED from doc — created by no repo script)
-- ============================================================================
-- NOTE: the doc records the column default as 'user', but users_role_check
-- (added by 006_fix_roles.sql) only permits member/creator/facilitator/
-- moderator/admin — i.e. the documented default is itself invalid. The role
-- system's stated intent is that 'member' is the default for new users, so the
-- default is reconciled to 'member' here. Flagged for confirmation.
CREATE TABLE erdpuls_threshold.users (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email          VARCHAR(255) NOT NULL,
    password_hash  VARCHAR(255) NOT NULL,
    name           VARCHAR(255),
    role           VARCHAR(50) DEFAULT 'member',
    is_active      BOOLEAN DEFAULT TRUE,
    email_verified BOOLEAN DEFAULT FALSE,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login     TIMESTAMP,
    CONSTRAINT users_email_key UNIQUE (email),
    CONSTRAINT users_role_check CHECK (role IN ('member', 'creator', 'facilitator', 'moderator', 'admin'))
);
CREATE INDEX idx_users_email ON erdpuls_threshold.users(email);
CREATE INDEX idx_users_role  ON erdpuls_threshold.users(role);

-- ============================================================================
-- offerings  [schema.sql base + delivery_language + description-length checks +
--             meals->catering rename + RECONSTRUCTED creator_id / organizer_*]
-- ============================================================================
CREATE TABLE erdpuls_threshold.offerings (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title                       VARCHAR(255) NOT NULL,
    title_de                    VARCHAR(255),
    title_pl                    VARCHAR(255),
    description                 TEXT NOT NULL,
    description_de              TEXT,
    description_pl              TEXT,
    threshold_amount            DECIMAL(10,2) NOT NULL,
    facilitator_cost            DECIMAL(10,2) DEFAULT 0,
    materials_cost              DECIMAL(10,2) DEFAULT 0,
    catering_cost               DECIMAL(10,2) DEFAULT 0,
    space_cost                  DECIMAL(10,2) DEFAULT 0,
    sustainability_contribution DECIMAL(10,2) DEFAULT 0,
    event_date                  TIMESTAMP,
    registration_deadline       TIMESTAMP NOT NULL,
    contribution_deadline       TIMESTAMP NOT NULL,
    status                      VARCHAR(50) DEFAULT 'open',
    min_participants            INTEGER DEFAULT 1,
    max_participants            INTEGER,
    created_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by                  VARCHAR(255),
    creator_id                  UUID REFERENCES erdpuls_threshold.users(id) ON DELETE SET NULL,
    organizer_name              VARCHAR(255),
    organizer_email             VARCHAR(255),
    organizer_phone             VARCHAR(50),
    delivery_language           VARCHAR(50)[] DEFAULT ARRAY['de']::VARCHAR(50)[],
    CONSTRAINT offerings_status_check CHECK (status IN ('draft','open','threshold_met','confirmed','completed','cancelled')),
    CONSTRAINT offerings_delivery_language_check CHECK (delivery_language <@ ARRAY['en','de','pl']::VARCHAR(50)[]),
    CONSTRAINT chk_title_length       CHECK (char_length(title) >= 3 AND char_length(title) <= 255),
    CONSTRAINT chk_title_de_length    CHECK (title_de IS NULL OR (char_length(title_de) >= 3 AND char_length(title_de) <= 255)),
    CONSTRAINT chk_title_pl_length    CHECK (title_pl IS NULL OR (char_length(title_pl) >= 3 AND char_length(title_pl) <= 255)),
    CONSTRAINT chk_description_length    CHECK (char_length(description) >= 50 AND char_length(description) <= 5000),
    CONSTRAINT chk_description_de_length CHECK (description_de IS NULL OR (char_length(description_de) >= 50 AND char_length(description_de) <= 5000)),
    CONSTRAINT chk_description_pl_length CHECK (description_pl IS NULL OR (char_length(description_pl) >= 50 AND char_length(description_pl) <= 5000))
);
CREATE INDEX idx_offerings_status ON erdpuls_threshold.offerings(status);
CREATE INDEX idx_offerings_dates  ON erdpuls_threshold.offerings(registration_deadline, contribution_deadline);

-- ============================================================================
-- contributions  [schema.sql base + 003 (hours_category/hours_amount/status) +
--                 004 (wants_to_participate/engagement_type)]
-- ============================================================================
CREATE TABLE erdpuls_threshold.contributions (
    id                   UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offering_id          UUID NOT NULL REFERENCES erdpuls_threshold.offerings(id) ON DELETE CASCADE,
    amount_eur           DECIMAL(10,2) NOT NULL,
    contribution_type    VARCHAR(50) DEFAULT 'euro',
    token_amount         DECIMAL(15,2),
    hours_description    TEXT,
    hours_equivalent_eur DECIMAL(10,2),
    contributed_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    hours_category       VARCHAR(100),
    hours_amount         DECIMAL(5,2),
    status               VARCHAR(50) DEFAULT 'pending',
    wants_to_participate BOOLEAN DEFAULT FALSE,
    engagement_type      VARCHAR(50) DEFAULT 'support_only',
    CONSTRAINT contributions_contribution_type_check CHECK (contribution_type IN ('euro','token','hours')),
    CONSTRAINT contributions_status_check            CHECK (status IN ('pending','confirmed','scheduled','completed','cancelled')),
    CONSTRAINT contributions_engagement_type_check   CHECK (engagement_type IN ('support_only','support_and_participate'))
);
CREATE INDEX idx_contributions_offering ON erdpuls_threshold.contributions(offering_id);
CREATE INDEX idx_contributions_date     ON erdpuls_threshold.contributions(contributed_at);

-- ============================================================================
-- contribution_contacts  [003 — gen_random_uuid() default per doc]
-- ============================================================================
CREATE TABLE erdpuls_threshold.contribution_contacts (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contribution_id UUID NOT NULL REFERENCES erdpuls_threshold.contributions(id) ON DELETE CASCADE,
    name            VARCHAR(255),
    email           VARCHAR(255),
    phone           VARCHAR(50),
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_contribution_contacts_contribution_id ON erdpuls_threshold.contribution_contacts(contribution_id);
CREATE INDEX idx_contribution_contacts_email           ON erdpuls_threshold.contribution_contacts(email);

-- ============================================================================
-- registrations  [schema.sql base + 004 (linked_contribution_id/registration_type)]
-- ============================================================================
CREATE TABLE erdpuls_threshold.registrations (
    id                     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offering_id            UUID NOT NULL REFERENCES erdpuls_threshold.offerings(id) ON DELETE CASCADE,
    email                  VARCHAR(255) NOT NULL,
    name                   VARCHAR(255),
    referral_source        VARCHAR(255),
    status                 VARCHAR(50) DEFAULT 'registered',
    registered_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    linked_contribution_id UUID REFERENCES erdpuls_threshold.contributions(id) ON DELETE SET NULL,
    registration_type      VARCHAR(50) DEFAULT 'participate_only',
    CONSTRAINT registrations_status_check            CHECK (status IN ('registered','confirmed','cancelled','attended')),
    CONSTRAINT registrations_registration_type_check CHECK (registration_type IN ('participate_only','linked_to_contribution')),
    CONSTRAINT registrations_offering_id_email_key   UNIQUE (offering_id, email)
);
CREATE INDEX idx_registrations_offering             ON erdpuls_threshold.registrations(offering_id);
CREATE INDEX idx_registrations_linked_contribution  ON erdpuls_threshold.registrations(linked_contribution_id);

-- ============================================================================
-- regeneration_fund  [schema.sql]
-- ============================================================================
CREATE TABLE erdpuls_threshold.regeneration_fund (
    id               UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    amount           DECIMAL(10,2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    offering_id      UUID REFERENCES erdpuls_threshold.offerings(id) ON DELETE SET NULL,
    description      TEXT,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT regeneration_fund_transaction_type_check CHECK (transaction_type IN ('surplus_in','shortfall_cover','seed_offering','adjustment'))
);

-- ============================================================================
-- token_rates  [schema.sql + default seed]
-- ============================================================================
CREATE TABLE erdpuls_threshold.token_rates (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tokens_per_eur DECIMAL(15,4) NOT NULL DEFAULT 70.0,
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
INSERT INTO erdpuls_threshold.token_rates (tokens_per_eur, effective_from)
VALUES (70.0, CURRENT_TIMESTAMP);

-- ============================================================================
-- hours_rates  [schema.sql + RECONSTRUCTED description_de/description_pl]
-- ============================================================================
CREATE TABLE erdpuls_threshold.hours_rates (
    id             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category       VARCHAR(100) NOT NULL,
    eur_per_hour   DECIMAL(10,2) NOT NULL,
    description    TEXT,
    created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    description_de TEXT,
    description_pl TEXT,
    CONSTRAINT hours_rates_category_key UNIQUE (category)
);
INSERT INTO erdpuls_threshold.hours_rates (category, eur_per_hour, description) VALUES
    ('garden_labor',      11.00, 'Weeding, planting, harvesting, composting, watering'),
    ('skilled_labor',     20.00, 'Carpentry, electrical, sensor installation, equipment repair'),
    ('knowledge_sharing', 27.50, 'Leading a session, mentoring, traditional knowledge transmission'),
    ('translation',       22.50, 'DE/EN/PL translation, documentation, content creation'),
    ('technical_support', 30.00, 'Data processing, sensor calibration, web development'),
    ('administrative',    12.50, 'Communication, scheduling, outreach, event support');

-- ============================================================================
-- Functions + trigger  [schema.sql]
-- ============================================================================
CREATE OR REPLACE FUNCTION erdpuls_threshold.check_offering_threshold()
RETURNS TRIGGER AS $$
DECLARE
    total DECIMAL(10,2);
    threshold DECIMAL(10,2);
    current_status VARCHAR(50);
BEGIN
    SELECT COALESCE(SUM(amount_eur), 0) INTO total
    FROM erdpuls_threshold.contributions
    WHERE offering_id = NEW.offering_id;

    SELECT threshold_amount, status INTO threshold, current_status
    FROM erdpuls_threshold.offerings
    WHERE id = NEW.offering_id;

    IF total >= threshold AND current_status = 'open' THEN
        UPDATE erdpuls_threshold.offerings
        SET status = 'threshold_met', updated_at = CURRENT_TIMESTAMP
        WHERE id = NEW.offering_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_threshold
AFTER INSERT ON erdpuls_threshold.contributions
FOR EACH ROW
EXECUTE FUNCTION erdpuls_threshold.check_offering_threshold();

CREATE OR REPLACE FUNCTION erdpuls_threshold.process_offering_surplus(offering_uuid UUID)
RETURNS DECIMAL AS $$
DECLARE
    total DECIMAL(10,2);
    threshold DECIMAL(10,2);
    surplus DECIMAL(10,2);
BEGIN
    SELECT COALESCE(SUM(amount_eur), 0) INTO total
    FROM erdpuls_threshold.contributions
    WHERE offering_id = offering_uuid;

    SELECT threshold_amount INTO threshold
    FROM erdpuls_threshold.offerings
    WHERE id = offering_uuid;

    surplus := total - threshold;

    IF surplus > 0 THEN
        INSERT INTO erdpuls_threshold.regeneration_fund (amount, transaction_type, offering_id, description)
        VALUES (surplus, 'surplus_in', offering_uuid, 'Surplus from offering threshold exceeded');
    END IF;

    RETURN surplus;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- Views  [offering_progress + regeneration_fund_balance (schema.sql);
--         engagement_overview (004)]
-- ============================================================================
CREATE VIEW erdpuls_threshold.offering_progress AS
SELECT
    o.id, o.title, o.threshold_amount, o.status,
    o.registration_deadline, o.contribution_deadline, o.event_date,
    COALESCE(SUM(c.amount_eur), 0) AS total_contributed,
    ROUND(COALESCE(SUM(c.amount_eur), 0) / o.threshold_amount * 100, 1) AS percent_funded,
    COUNT(DISTINCT r.id) AS registrations_count,
    o.max_participants,
    CASE WHEN COALESCE(SUM(c.amount_eur), 0) >= o.threshold_amount THEN true ELSE false END AS threshold_reached
FROM erdpuls_threshold.offerings o
LEFT JOIN erdpuls_threshold.contributions c ON o.id = c.offering_id
LEFT JOIN erdpuls_threshold.registrations r ON o.id = r.offering_id AND r.status != 'cancelled'
GROUP BY o.id;

CREATE VIEW erdpuls_threshold.regeneration_fund_balance AS
SELECT
    COALESCE(SUM(
        CASE
            WHEN transaction_type = 'surplus_in' THEN amount
            WHEN transaction_type IN ('shortfall_cover', 'seed_offering') THEN -amount
            WHEN transaction_type = 'adjustment' THEN amount
            ELSE 0
        END), 0) AS current_balance,
    COUNT(*) AS total_transactions
FROM erdpuls_threshold.regeneration_fund;

CREATE OR REPLACE VIEW erdpuls_threshold.engagement_overview AS
SELECT
    o.id AS offering_id, o.title AS offering_title,
    'participate_only' AS engagement_type,
    r.id AS record_id, r.email, r.name,
    NULL::DECIMAL AS amount_eur, NULL::VARCHAR AS contribution_type,
    r.registered_at AS engaged_at, r.status
FROM erdpuls_threshold.registrations r
JOIN erdpuls_threshold.offerings o ON r.offering_id = o.id
WHERE r.registration_type = 'participate_only'
UNION ALL
SELECT
    o.id AS offering_id, o.title AS offering_title,
    c.engagement_type, c.id AS record_id, cc.email, cc.name,
    c.amount_eur, c.contribution_type, c.contributed_at AS engaged_at, c.status
FROM erdpuls_threshold.contributions c
JOIN erdpuls_threshold.offerings o ON c.offering_id = o.id
LEFT JOIN erdpuls_threshold.contribution_contacts cc ON c.id = cc.contribution_id
ORDER BY engaged_at DESC;

-- ============================================================================
-- Grants to the application role (environment-specific — uncomment & set role)
-- ============================================================================
-- GRANT USAGE ON SCHEMA erdpuls_threshold TO <app_role>;
-- GRANT ALL PRIVILEGES ON ALL TABLES    IN SCHEMA erdpuls_threshold TO <app_role>;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA erdpuls_threshold TO <app_role>;
-- ALTER DEFAULT PRIVILEGES IN SCHEMA erdpuls_threshold GRANT ALL ON TABLES TO <app_role>;
