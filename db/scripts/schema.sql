-- Erdpuls Collective Threshold Model Database Schema
-- Database: ubec_erdpuls
-- Schema: erdpuls_threshold

-- Create schema
CREATE SCHEMA IF NOT EXISTS erdpuls_threshold;

-- Set search path for this session
SET search_path TO erdpuls_threshold;

-- Enable UUID extension (if not already enabled in database)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- OFFERINGS TABLE
-- Each offering (workshop, course, event) with its threshold
-- ============================================
CREATE TABLE erdpuls_threshold.offerings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    title VARCHAR(255) NOT NULL,
    title_de VARCHAR(255),
    title_pl VARCHAR(255),
    description TEXT NOT NULL,
    description_de TEXT,
    description_pl TEXT,
    
    -- Threshold and financial breakdown
    threshold_amount DECIMAL(10,2) NOT NULL,
    facilitator_cost DECIMAL(10,2) DEFAULT 0,
    materials_cost DECIMAL(10,2) DEFAULT 0,
    meals_cost DECIMAL(10,2) DEFAULT 0,
    space_cost DECIMAL(10,2) DEFAULT 0,
    sustainability_contribution DECIMAL(10,2) DEFAULT 0,
    
    -- Dates
    event_date TIMESTAMP,
    registration_deadline TIMESTAMP NOT NULL,
    contribution_deadline TIMESTAMP NOT NULL,
    
    -- Status
    status VARCHAR(50) DEFAULT 'open' CHECK (status IN ('draft', 'open', 'threshold_met', 'confirmed', 'completed', 'cancelled')),
    
    -- Capacity
    min_participants INTEGER DEFAULT 1,
    max_participants INTEGER,
    
    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(255)
);

-- ============================================
-- REGISTRATIONS TABLE
-- People expressing intention to participate
-- (Separate from contributions - no financial info here)
-- ============================================
CREATE TABLE erdpuls_threshold.registrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offering_id UUID NOT NULL REFERENCES erdpuls_threshold.offerings(id) ON DELETE CASCADE,
    
    -- Contact info (for confirmation emails only)
    email VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    
    -- Optional: how they heard about it
    referral_source VARCHAR(255),
    
    -- Status
    status VARCHAR(50) DEFAULT 'registered' CHECK (status IN ('registered', 'confirmed', 'cancelled', 'attended')),
    
    -- Metadata
    registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure one registration per email per offering
    UNIQUE(offering_id, email)
);

-- ============================================
-- CONTRIBUTIONS TABLE
-- ANONYMOUS contributions to offerings
-- CRITICAL: No contributor identification stored!
-- ============================================
CREATE TABLE erdpuls_threshold.contributions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    offering_id UUID NOT NULL REFERENCES erdpuls_threshold.offerings(id) ON DELETE CASCADE,
    
    -- Amount and type
    amount_eur DECIMAL(10,2) NOT NULL,
    contribution_type VARCHAR(50) DEFAULT 'euro' CHECK (contribution_type IN ('euro', 'token', 'hours')),
    
    -- For token contributions: original token amount
    token_amount DECIMAL(15,2),
    
    -- For hours contributions: description of work
    hours_description TEXT,
    hours_equivalent_eur DECIMAL(10,2),
    
    -- Timestamp only - NO contributor identification
    contributed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    
    -- NOTE: We deliberately do NOT store:
    -- - contributor_id
    -- - email
    -- - IP address
    -- - any identifying information
);

-- ============================================
-- REGENERATION FUND
-- Community reserve from surplus contributions
-- ============================================
CREATE TABLE erdpuls_threshold.regeneration_fund (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Transaction details
    amount DECIMAL(10,2) NOT NULL,
    transaction_type VARCHAR(50) NOT NULL CHECK (transaction_type IN ('surplus_in', 'shortfall_cover', 'seed_offering', 'adjustment')),
    
    -- Reference to offering (if applicable)
    offering_id UUID REFERENCES erdpuls_threshold.offerings(id) ON DELETE SET NULL,
    
    -- Description
    description TEXT,
    
    -- Timestamp
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- TOKEN EXCHANGE RATES
-- For converting UBECrc to EUR
-- ============================================
CREATE TABLE erdpuls_threshold.token_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tokens_per_eur DECIMAL(15,4) NOT NULL DEFAULT 70.0, -- 7 UBECrc = €0.10
    effective_from TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default token rate
INSERT INTO erdpuls_threshold.token_rates (tokens_per_eur, effective_from) 
VALUES (70.0, CURRENT_TIMESTAMP);

-- ============================================
-- CONTRIBUTION HOURS RATES
-- For valuing different types of contribution work
-- ============================================
CREATE TABLE erdpuls_threshold.hours_rates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    category VARCHAR(100) NOT NULL UNIQUE,
    eur_per_hour DECIMAL(10,2) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default hours rates
INSERT INTO erdpuls_threshold.hours_rates (category, eur_per_hour, description) VALUES
('garden_labor', 11.00, 'Weeding, planting, harvesting, composting, watering'),
('skilled_labor', 20.00, 'Carpentry, electrical, sensor installation, equipment repair'),
('knowledge_sharing', 27.50, 'Leading a session, mentoring, traditional knowledge transmission'),
('translation', 22.50, 'DE/EN/PL translation, documentation, content creation'),
('technical_support', 30.00, 'Data processing, sensor calibration, web development'),
('administrative', 12.50, 'Communication, scheduling, outreach, event support');

-- ============================================
-- VIEWS
-- ============================================

-- View: Offering progress (aggregate only - preserves anonymity)
CREATE VIEW erdpuls_threshold.offering_progress AS
SELECT 
    o.id,
    o.title,
    o.threshold_amount,
    o.status,
    o.registration_deadline,
    o.contribution_deadline,
    o.event_date,
    COALESCE(SUM(c.amount_eur), 0) as total_contributed,
    ROUND(COALESCE(SUM(c.amount_eur), 0) / o.threshold_amount * 100, 1) as percent_funded,
    COUNT(DISTINCT r.id) as registrations_count,
    o.max_participants,
    CASE 
        WHEN COALESCE(SUM(c.amount_eur), 0) >= o.threshold_amount THEN true 
        ELSE false 
    END as threshold_reached
FROM erdpuls_threshold.offerings o
LEFT JOIN erdpuls_threshold.contributions c ON o.id = c.offering_id
LEFT JOIN erdpuls_threshold.registrations r ON o.id = r.offering_id AND r.status != 'cancelled'
GROUP BY o.id;

-- View: Regeneration Fund balance
CREATE VIEW erdpuls_threshold.regeneration_fund_balance AS
SELECT 
    COALESCE(SUM(
        CASE 
            WHEN transaction_type = 'surplus_in' THEN amount
            WHEN transaction_type IN ('shortfall_cover', 'seed_offering') THEN -amount
            WHEN transaction_type = 'adjustment' THEN amount
            ELSE 0
        END
    ), 0) as current_balance,
    COUNT(*) as total_transactions
FROM erdpuls_threshold.regeneration_fund;

-- ============================================
-- INDEXES
-- ============================================
CREATE INDEX idx_offerings_status ON erdpuls_threshold.offerings(status);
CREATE INDEX idx_offerings_dates ON erdpuls_threshold.offerings(registration_deadline, contribution_deadline);
CREATE INDEX idx_registrations_offering ON erdpuls_threshold.registrations(offering_id);
CREATE INDEX idx_contributions_offering ON erdpuls_threshold.contributions(offering_id);
CREATE INDEX idx_contributions_date ON erdpuls_threshold.contributions(contributed_at);

-- ============================================
-- FUNCTIONS
-- ============================================

-- Function to check and update offering status
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

-- Trigger to check threshold after each contribution
CREATE TRIGGER trigger_check_threshold
AFTER INSERT ON erdpuls_threshold.contributions
FOR EACH ROW
EXECUTE FUNCTION erdpuls_threshold.check_offering_threshold();

-- Function to move surplus to regeneration fund
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

-- ============================================
-- GRANT PERMISSIONS (adjust user as needed)
-- ============================================
-- GRANT USAGE ON SCHEMA erdpuls_threshold TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA erdpuls_threshold TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA erdpuls_threshold TO your_app_user;
