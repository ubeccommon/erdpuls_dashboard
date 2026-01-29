-- ============================================
-- Erdpuls Collective Threshold Model
-- Migration: Add description length constraints
-- 
-- Enforces character limits at the database level:
--   - Minimum: 50 characters
--   - Maximum: 5,000 characters
--
-- © 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 
-- https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
-- ============================================

-- Add CHECK constraint for description (required field)
ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_description_length 
CHECK (
    char_length(description) >= 50 
    AND char_length(description) <= 5000
);

-- Add CHECK constraint for description_de (optional, so allow NULL or valid length)
ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_description_de_length 
CHECK (
    description_de IS NULL 
    OR (char_length(description_de) >= 50 AND char_length(description_de) <= 5000)
);

-- Add CHECK constraint for description_pl (optional, so allow NULL or valid length)
ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_description_pl_length 
CHECK (
    description_pl IS NULL 
    OR (char_length(description_pl) >= 50 AND char_length(description_pl) <= 5000)
);

-- Add CHECK constraints for titles as well (3-255 characters)
ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_title_length 
CHECK (
    char_length(title) >= 3 
    AND char_length(title) <= 255
);

ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_title_de_length 
CHECK (
    title_de IS NULL 
    OR (char_length(title_de) >= 3 AND char_length(title_de) <= 255)
);

ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT chk_title_pl_length 
CHECK (
    title_pl IS NULL 
    OR (char_length(title_pl) >= 3 AND char_length(title_pl) <= 255)
);

-- ============================================
-- Verify constraints were added
-- ============================================
SELECT 
    conname AS constraint_name,
    contype AS constraint_type,
    pg_get_constraintdef(oid) AS definition
FROM pg_constraint 
WHERE conrelid = 'erdpuls_threshold.offerings'::regclass
AND conname LIKE 'chk_%'
ORDER BY conname;
