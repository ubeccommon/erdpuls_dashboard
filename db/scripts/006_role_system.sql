-- ============================================
-- Erdpuls Role System Migration
-- Migration: 006_role_system.sql
-- ============================================
-- 
-- This migration updates the user role system from simple 'user'/'admin'
-- to a comprehensive role hierarchy:
--
--   member (10)     - Default for new users, can participate & contribute
--   creator (20)    - Can create offerings (require approval)
--   facilitator (30)- Trusted creator, offerings published directly
--   moderator (50)  - Can approve offerings, manage community
--   admin (100)     - Full system access
--
-- ============================================

-- Step 1: Update existing 'user' roles to 'member'
UPDATE erdpuls_threshold.users 
SET role = 'member' 
WHERE role = 'user';

-- Step 2: Create a roles reference table (optional but useful for joins/validation)
CREATE TABLE IF NOT EXISTS erdpuls_threshold.roles (
    name VARCHAR(50) PRIMARY KEY,
    level INTEGER NOT NULL,
    description TEXT,
    description_de TEXT,
    description_pl TEXT,
    can_create_offering BOOLEAN DEFAULT FALSE,
    can_publish_direct BOOLEAN DEFAULT FALSE,
    can_approve_offerings BOOLEAN DEFAULT FALSE,
    can_manage_users BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Step 3: Insert role definitions
INSERT INTO erdpuls_threshold.roles (name, level, description, description_de, description_pl, can_create_offering, can_publish_direct, can_approve_offerings, can_manage_users)
VALUES 
    ('member', 10, 'Can participate in and contribute to offerings', 'Kann an Angeboten teilnehmen und beitragen', 'Może uczestniczyć i wspierać oferty', FALSE, FALSE, FALSE, FALSE),
    ('creator', 20, 'Can create offerings (require approval)', 'Kann Angebote erstellen (erfordert Genehmigung)', 'Może tworzyć oferty (wymagają zatwierdzenia)', TRUE, FALSE, FALSE, FALSE),
    ('facilitator', 30, 'Trusted creator - offerings published directly', 'Vertrauenswürdiger Ersteller - Angebote werden direkt veröffentlicht', 'Zaufany twórca - oferty publikowane bezpośrednio', TRUE, TRUE, FALSE, FALSE),
    ('moderator', 50, 'Can approve offerings and manage community', 'Kann Angebote genehmigen und Community verwalten', 'Może zatwierdzać oferty i zarządzać społecznością', TRUE, TRUE, TRUE, FALSE),
    ('admin', 100, 'Full system access', 'Voller Systemzugriff', 'Pełny dostęp do systemu', TRUE, TRUE, TRUE, TRUE)
ON CONFLICT (name) DO UPDATE SET
    level = EXCLUDED.level,
    description = EXCLUDED.description,
    description_de = EXCLUDED.description_de,
    description_pl = EXCLUDED.description_pl,
    can_create_offering = EXCLUDED.can_create_offering,
    can_publish_direct = EXCLUDED.can_publish_direct,
    can_approve_offerings = EXCLUDED.can_approve_offerings,
    can_manage_users = EXCLUDED.can_manage_users;

-- Step 4: Add check constraint to users table (optional - for data integrity)
-- Note: This will fail if there are any roles not in the list
-- ALTER TABLE erdpuls_threshold.users 
-- ADD CONSTRAINT check_valid_role 
-- CHECK (role IN ('member', 'creator', 'facilitator', 'moderator', 'admin'));

-- Step 5: Create index for faster role lookups
CREATE INDEX IF NOT EXISTS idx_users_role ON erdpuls_threshold.users(role);

-- ============================================
-- Verification queries (run manually to check)
-- ============================================
-- 
-- Check role distribution:
-- SELECT role, COUNT(*) FROM erdpuls_threshold.users GROUP BY role;
--
-- Check roles table:
-- SELECT * FROM erdpuls_threshold.roles ORDER BY level;
--
-- ============================================
