-- ============================================
-- Erdpuls Collective Threshold Model
-- Migration: Rename meals_cost to catering_cost
--
-- © 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 
-- https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
-- ============================================

-- Rename the column
ALTER TABLE erdpuls_threshold.offerings
RENAME COLUMN meals_cost TO catering_cost;

-- Verify the change
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_schema = 'erdpuls_threshold' 
AND table_name = 'offerings'
AND column_name = 'catering_cost';
