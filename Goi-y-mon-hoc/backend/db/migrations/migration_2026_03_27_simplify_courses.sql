-- Migration: simplify courses table to only code/name/credits
ALTER TABLE courses DROP COLUMN IF EXISTS specialization;
ALTER TABLE courses DROP COLUMN IF EXISTS group_type;
ALTER TABLE courses DROP COLUMN IF EXISTS suggested_term;
DROP INDEX IF EXISTS idx_courses_specialization;
DROP INDEX IF EXISTS idx_courses_program_specialization;
