-- Migration: adapt schema to elective-credit logic
-- 1) rename courses.term -> suggested_term (if old column exists)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'courses' AND column_name = 'term'
    ) THEN
        ALTER TABLE courses RENAME COLUMN term TO suggested_term;
    END IF;
END $$;

-- 2) create elective_rules table
CREATE TABLE IF NOT EXISTS elective_rules (
    id BIGSERIAL PRIMARY KEY,
    program_code TEXT NOT NULL,
    specialization TEXT NOT NULL,
    group_type TEXT NOT NULL,
    min_credits_required NUMERIC(4,1) NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_elective_rules_program_specialization
ON elective_rules(program_code, specialization);
