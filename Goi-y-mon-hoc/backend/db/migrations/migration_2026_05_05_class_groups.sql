-- Migration 2026-05-05 v2: ClassGroup model + email_edu + soft-delete reviews
--
-- Bối cảnh: refactor mô hình quản lý SV/GV theo Lớp (đại học VN truyền thống).
--   • Mỗi Lớp có 1 GVCN (NOT NULL) — không cho phép lớp "mồ côi"
--   • Mỗi SV thuộc 1 Lớp → tự derive specialization + advisor từ class_group
--   • Bỏ concept "Trưởng bộ môn" (is_head_of_department) — không dùng nữa
--   • Thêm email_edu cho cơ chế quên mật khẩu (mock SMTP)
--   • Thêm soft-delete cho course_ratings để admin moderation không mất audit
--
-- Idempotent: dùng IF EXISTS / IF NOT EXISTS để chạy lại an toàn.

-- ── ClassGroup table ──────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS class_groups (
    id BIGSERIAL PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    cohort VARCHAR(10) NOT NULL,
    specialization VARCHAR(20) NOT NULL,
    advisor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_class_groups_advisor_id ON class_groups(advisor_id);
CREATE INDEX IF NOT EXISTS idx_class_groups_specialization ON class_groups(specialization);
CREATE INDEX IF NOT EXISTS idx_class_groups_cohort ON class_groups(cohort);

-- ── users: thêm class_group_id + email_edu, drop is_head_of_department ────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_edu VARCHAR(255);
ALTER TABLE users ADD COLUMN IF NOT EXISTS class_group_id BIGINT
    REFERENCES class_groups(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_users_class_group_id ON users(class_group_id);
CREATE INDEX IF NOT EXISTS idx_users_email_edu ON users(email_edu);

ALTER TABLE users DROP COLUMN IF EXISTS is_head_of_department;

-- ── course_ratings: soft delete fields ────────────────────────────────────────
ALTER TABLE course_ratings ADD COLUMN IF NOT EXISTS hidden BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE course_ratings ADD COLUMN IF NOT EXISTS hidden_by BIGINT
    REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE course_ratings ADD COLUMN IF NOT EXISTS hidden_at TIMESTAMP;
CREATE INDEX IF NOT EXISTS idx_course_ratings_hidden ON course_ratings(hidden) WHERE hidden = FALSE;
