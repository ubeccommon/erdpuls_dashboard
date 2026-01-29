-- ============================================
-- Erdpuls Collective Threshold Model
-- Rollback: Remove description/title length constraints
--
-- © 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 
-- https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
-- ============================================

-- Remove description constraints
ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_description_length;

ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_description_de_length;

ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_description_pl_length;

-- Remove title constraints
ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_title_length;

ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_title_de_length;

ALTER TABLE erdpuls_threshold.offerings
DROP CONSTRAINT IF EXISTS chk_title_pl_length;
