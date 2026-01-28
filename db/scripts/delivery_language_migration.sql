-- Migration: Add delivery_language field to offerings table
-- Purpose: Track which language(s) the offering will be conducted in
-- Author: Michel Garand
-- Date: 2026-01-28

-- Add the delivery_language column (array to support multilingual offerings)
ALTER TABLE erdpuls_threshold.offerings 
ADD COLUMN IF NOT EXISTS delivery_language VARCHAR(50)[] DEFAULT ARRAY['de']::VARCHAR(50)[];

-- Add comment for documentation
COMMENT ON COLUMN erdpuls_threshold.offerings.delivery_language IS 
'Languages in which the offering will be conducted. Array of ISO codes: en, de, pl';

-- Optional: Add a check constraint to ensure valid language codes
ALTER TABLE erdpuls_threshold.offerings
ADD CONSTRAINT offerings_delivery_language_check 
CHECK (delivery_language <@ ARRAY['en', 'de', 'pl']::VARCHAR(50)[]);

-- Update existing offerings to have German as default (adjust as needed)
UPDATE erdpuls_threshold.offerings 
SET delivery_language = ARRAY['de']::VARCHAR(50)[]
WHERE delivery_language IS NULL;
