-- Database schema for CNTT course suggestion system
-- PostgreSQL

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS courses (
    id BIGSERIAL PRIMARY KEY,
    course_code TEXT NOT NULL UNIQUE,
    course_name TEXT NOT NULL,
    credits NUMERIC(4,1)
);

CREATE TABLE IF NOT EXISTS elective_rules (
    id BIGSERIAL PRIMARY KEY,
    program_code TEXT NOT NULL,
    specialization TEXT NOT NULL,
    group_type TEXT NOT NULL,
    min_credits_required NUMERIC(4,1) NOT NULL
);

CREATE TABLE IF NOT EXISTS user_grades (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE RESTRICT,
    score10 NUMERIC(4,2),
    score4 NUMERIC(3,2),
    letter TEXT,
    passed BOOLEAN NOT NULL DEFAULT FALSE,
    term TEXT,
    uploaded_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, course_code, term)
);

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

CREATE TABLE IF NOT EXISTS study_plans (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_name TEXT NOT NULL,
    target_gpa NUMERIC(3,2),
    max_credits_per_term NUMERIC(4,1),
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS study_plan_items (
    id BIGSERIAL PRIMARY KEY,
    plan_id BIGINT NOT NULL REFERENCES study_plans(id) ON DELETE CASCADE,
    course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE RESTRICT,
    term_label TEXT
);

CREATE INDEX IF NOT EXISTS idx_elective_rules_program_specialization
ON elective_rules(program_code, specialization);

CREATE INDEX IF NOT EXISTS idx_user_grades_user
ON user_grades(user_id);

CREATE INDEX IF NOT EXISTS idx_study_plans_user
ON study_plans(user_id);

CREATE TABLE IF NOT EXISTS chat_messages (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    intent TEXT,
    message TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_chat_messages_user_created
ON chat_messages(user_id, created_at DESC);
