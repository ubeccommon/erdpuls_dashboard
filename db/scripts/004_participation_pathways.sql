-- ============================================
-- Migration: Participation Pathways Architecture
-- Enables three engagement modes:
--   1. Participate Only (register without contributing)
--   2. Contribute Only (support without participating)
--   3. Contribute & Participate (both linked together)
-- ============================================

-- Ensure required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================
-- UPDATE CONTRIBUTIONS TABLE
-- Add participation intent flag
-- ============================================

-- Add wants_to_participate column to contributions
ALTER TABLE erdpuls_threshold.contributions
    ADD COLUMN IF NOT EXISTS wants_to_participate BOOLEAN DEFAULT FALSE;

-- Add engagement_type to clarify the pathway chosen
-- 'support_only' = Contribute without participating
-- 'support_and_participate' = Contribute and participate
ALTER TABLE erdpuls_threshold.contributions
    ADD COLUMN IF NOT EXISTS engagement_type VARCHAR(50) DEFAULT 'support_only';

-- Add constraint for engagement types
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'contributions_engagement_type_check'
    ) THEN
        ALTER TABLE erdpuls_threshold.contributions
            ADD CONSTRAINT contributions_engagement_type_check 
            CHECK (engagement_type IN ('support_only', 'support_and_participate'));
    END IF;
END $$;

-- Update existing contributions to have engagement_type
UPDATE erdpuls_threshold.contributions 
SET engagement_type = 'support_only',
    wants_to_participate = FALSE 
WHERE engagement_type IS NULL OR wants_to_participate IS NULL;

-- Update table comment
COMMENT ON TABLE erdpuls_threshold.contributions IS 
'Contributions to offerings with engagement pathway tracking.
ENGAGEMENT TYPES:
- support_only: Contribute financially without participating
- support_and_participate: Contribute AND register for participation
Identity stored SEPARATELY in contribution_contacts for operational needs.
PUBLIC visibility: aggregates only (total amount, contributor count).
ORGANIZER visibility: individual contributions + linked contact info.';

COMMENT ON COLUMN erdpuls_threshold.contributions.wants_to_participate IS 
'Whether the contributor also wants to participate in the offering.
If TRUE, a registration record should be created linking to this contribution.';

COMMENT ON COLUMN erdpuls_threshold.contributions.engagement_type IS 
'The participation pathway chosen:
- support_only: Financial support without attendance
- support_and_participate: Both contribute and attend';

-- ============================================
-- UPDATE REGISTRATIONS TABLE
-- Add link to contribution (for "Contribute & Participate" pathway)
-- ============================================

-- Add linked_contribution_id to registrations
ALTER TABLE erdpuls_threshold.registrations
    ADD COLUMN IF NOT EXISTS linked_contribution_id UUID REFERENCES erdpuls_threshold.contributions(id) ON DELETE SET NULL;

-- Add registration_type to clarify the pathway
-- 'participate_only' = Register without contributing
-- 'linked_to_contribution' = Registration created from contribution
ALTER TABLE erdpuls_threshold.registrations
    ADD COLUMN IF NOT EXISTS registration_type VARCHAR(50) DEFAULT 'participate_only';

-- Add constraint for registration types
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'registrations_registration_type_check'
    ) THEN
        ALTER TABLE erdpuls_threshold.registrations
            ADD CONSTRAINT registrations_registration_type_check 
            CHECK (registration_type IN ('participate_only', 'linked_to_contribution'));
    END IF;
END $$;

-- Update existing registrations
UPDATE erdpuls_threshold.registrations 
SET registration_type = 'participate_only' 
WHERE registration_type IS NULL;

-- Index for linked contributions lookup
CREATE INDEX IF NOT EXISTS idx_registrations_linked_contribution 
    ON erdpuls_threshold.registrations(linked_contribution_id);

-- Update table comment
COMMENT ON TABLE erdpuls_threshold.registrations IS 
'Registration of intention to participate.
REGISTRATION TYPES:
- participate_only: Register without contributing
- linked_to_contribution: Registration created from "Contribute & Participate" flow
When linked_contribution_id is set, this registration was auto-created from a contribution.';

COMMENT ON COLUMN erdpuls_threshold.registrations.linked_contribution_id IS 
'If set, this registration was created automatically when a contribution was made 
with wants_to_participate=TRUE. Links participation to contribution for operational tracking.';

COMMENT ON COLUMN erdpuls_threshold.registrations.registration_type IS 
'The participation pathway chosen:
- participate_only: Just register without financial contribution
- linked_to_contribution: Registration from "Contribute & Participate" flow';

-- ============================================
-- CREATE VIEW FOR UNIFIED ENGAGEMENT TRACKING
-- Helps organizers see all engagement in one place
-- ============================================

CREATE OR REPLACE VIEW erdpuls_threshold.engagement_overview AS
SELECT 
    o.id AS offering_id,
    o.title AS offering_title,
    'participate_only' AS engagement_type,
    r.id AS record_id,
    r.email,
    r.name,
    NULL::DECIMAL AS amount_eur,
    NULL::VARCHAR AS contribution_type,
    r.registered_at AS engaged_at,
    r.status
FROM erdpuls_threshold.registrations r
JOIN erdpuls_threshold.offerings o ON r.offering_id = o.id
WHERE r.registration_type = 'participate_only'

UNION ALL

SELECT 
    o.id AS offering_id,
    o.title AS offering_title,
    c.engagement_type,
    c.id AS record_id,
    cc.email,
    cc.name,
    c.amount_eur,
    c.contribution_type,
    c.contributed_at AS engaged_at,
    c.status
FROM erdpuls_threshold.contributions c
JOIN erdpuls_threshold.offerings o ON c.offering_id = o.id
LEFT JOIN erdpuls_threshold.contribution_contacts cc ON c.id = cc.contribution_id
ORDER BY engaged_at DESC;

COMMENT ON VIEW erdpuls_threshold.engagement_overview IS 
'Unified view of all engagement types for organizer dashboard.
Shows participation-only registrations and all contribution types together.';

-- ============================================
-- VERIFICATION QUERIES
-- ============================================

-- Show updated table structures
SELECT 
    'contributions' as table_name,
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'erdpuls_threshold' 
AND table_name = 'contributions'
AND column_name IN ('wants_to_participate', 'engagement_type')

UNION ALL

SELECT 
    'registrations' as table_name,
    column_name, 
    data_type, 
    column_default
FROM information_schema.columns 
WHERE table_schema = 'erdpuls_threshold' 
AND table_name = 'registrations'
AND column_name IN ('linked_contribution_id', 'registration_type');
