-- ============================================
-- Migration: Add ContributionContact table and update Contributions
-- Implements "Community-Anonymous, Operationally-Known" model
-- ============================================

-- Ensure uuid extension exists (try both methods)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- If above fails, gen_random_uuid() from pgcrypto works too
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Add new columns to contributions table
ALTER TABLE erdpuls_threshold.contributions
    ADD COLUMN IF NOT EXISTS hours_category VARCHAR(100),
    ADD COLUMN IF NOT EXISTS hours_amount DECIMAL(5,2),
    ADD COLUMN IF NOT EXISTS status VARCHAR(50) DEFAULT 'pending';

-- Add status constraint
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'contributions_status_check'
    ) THEN
        ALTER TABLE erdpuls_threshold.contributions
            ADD CONSTRAINT contributions_status_check 
            CHECK (status IN ('pending', 'confirmed', 'scheduled', 'completed', 'cancelled'));
    END IF;
END $$;

-- Update comment on contributions table
COMMENT ON TABLE erdpuls_threshold.contributions IS 
'Contributions to offerings. Identity stored SEPARATELY in contribution_contacts for operational needs. 
PUBLIC visibility: aggregates only (total amount, contributor count).
ORGANIZER visibility: individual contributions + linked contact info for coordination.';

-- ============================================
-- CONTRIBUTION CONTACTS TABLE
-- Separate identity from contribution for conceptual anonymity
-- Only visible to organizers for operational purposes
-- ============================================
CREATE TABLE IF NOT EXISTS erdpuls_threshold.contribution_contacts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    contribution_id UUID NOT NULL REFERENCES erdpuls_threshold.contributions(id) ON DELETE CASCADE,
    
    -- Contact information (for operational purposes only)
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Notes from contributor
    notes TEXT,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_contribution_contacts_contribution_id 
    ON erdpuls_threshold.contribution_contacts(contribution_id);

CREATE INDEX IF NOT EXISTS idx_contribution_contacts_email 
    ON erdpuls_threshold.contribution_contacts(email);

-- Comment explaining the separation
COMMENT ON TABLE erdpuls_threshold.contribution_contacts IS 
'Contact information linked to contributions for operational purposes.
SEPARATED from contributions to maintain conceptual anonymity.
Access restricted to organizers - never displayed publicly.
Enables: payment follow-up, hours coordination, tax receipts.';

-- ============================================
-- Update existing contributions to have status
-- ============================================
UPDATE erdpuls_threshold.contributions 
SET status = 'pending' 
WHERE status IS NULL;
