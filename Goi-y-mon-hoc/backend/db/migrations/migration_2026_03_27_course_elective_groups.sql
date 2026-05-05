-- Add course_elective_groups table to map courses to elective groups
CREATE TABLE IF NOT EXISTS course_elective_groups (
    id BIGSERIAL PRIMARY KEY,
    course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
    program_code TEXT NOT NULL,
    specialization TEXT NOT NULL,
    group_type TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_course_elective_unique
ON course_elective_groups(course_code, program_code, specialization, group_type);

CREATE INDEX IF NOT EXISTS idx_course_elective_group
ON course_elective_groups(program_code, specialization, group_type);
