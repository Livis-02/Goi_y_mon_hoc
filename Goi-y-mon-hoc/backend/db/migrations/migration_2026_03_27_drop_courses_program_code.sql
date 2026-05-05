-- Migration: remove courses.program_code (deprecated)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'courses' AND column_name = 'program_code'
    ) THEN
        ALTER TABLE courses DROP COLUMN program_code;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_courses_program_specialization;
CREATE INDEX IF NOT EXISTS idx_courses_specialization ON courses(specialization);
