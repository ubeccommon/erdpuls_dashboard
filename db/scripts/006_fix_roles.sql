-- Quick fix: Drop old constraint, update roles, add new constraint

-- 1. Drop the old constraint
ALTER TABLE erdpuls_threshold.users DROP CONSTRAINT IF EXISTS users_role_check;

-- 2. Update 'user' to 'member'
UPDATE erdpuls_threshold.users SET role = 'member' WHERE role = 'user';

-- 3. Add new constraint with all valid roles
ALTER TABLE erdpuls_threshold.users 
ADD CONSTRAINT users_role_check 
CHECK (role IN ('member', 'creator', 'facilitator', 'moderator', 'admin'));

-- 4. Verify
SELECT role, COUNT(*) FROM erdpuls_threshold.users GROUP BY role;
