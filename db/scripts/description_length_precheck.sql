-- ============================================
-- Erdpuls Collective Threshold Model
-- Pre-check: Find existing records that would violate constraints
-- Run this BEFORE the migration to identify issues
--
-- © 2026 Michel Garand | Lizenz: CC BY-NC-SA 4.0 
-- https://creativecommons.org/licenses/by-nc-sa/4.0/deed.de
-- ============================================

-- Check for descriptions that are too short or too long
SELECT 
    id,
    title,
    'description' AS field,
    char_length(description) AS current_length,
    CASE 
        WHEN char_length(description) < 50 THEN 'TOO SHORT (min 50)'
        WHEN char_length(description) > 5000 THEN 'TOO LONG (max 5000)'
    END AS issue
FROM erdpuls_threshold.offerings
WHERE char_length(description) < 50 OR char_length(description) > 5000

UNION ALL

SELECT 
    id,
    title,
    'description_de' AS field,
    char_length(description_de) AS current_length,
    CASE 
        WHEN char_length(description_de) < 50 THEN 'TOO SHORT (min 50)'
        WHEN char_length(description_de) > 5000 THEN 'TOO LONG (max 5000)'
    END AS issue
FROM erdpuls_threshold.offerings
WHERE description_de IS NOT NULL 
AND (char_length(description_de) < 50 OR char_length(description_de) > 5000)

UNION ALL

SELECT 
    id,
    title,
    'description_pl' AS field,
    char_length(description_pl) AS current_length,
    CASE 
        WHEN char_length(description_pl) < 50 THEN 'TOO SHORT (min 50)'
        WHEN char_length(description_pl) > 5000 THEN 'TOO LONG (max 5000)'
    END AS issue
FROM erdpuls_threshold.offerings
WHERE description_pl IS NOT NULL 
AND (char_length(description_pl) < 50 OR char_length(description_pl) > 5000)

UNION ALL

-- Also check titles
SELECT 
    id,
    title,
    'title' AS field,
    char_length(title) AS current_length,
    CASE 
        WHEN char_length(title) < 3 THEN 'TOO SHORT (min 3)'
        WHEN char_length(title) > 255 THEN 'TOO LONG (max 255)'
    END AS issue
FROM erdpuls_threshold.offerings
WHERE char_length(title) < 3 OR char_length(title) > 255

ORDER BY id, field;
