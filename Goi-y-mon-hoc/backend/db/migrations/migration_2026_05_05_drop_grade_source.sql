-- Migration 2026-05-05 v3: drop admin grades import concept
--
-- Bối cảnh: refactor EduGuide thành "tool cá nhân hỗ trợ học vụ" — không thay
-- thế cổng SIS chính thức của trường.
--   • Bỏ admin import điểm (endpoint /admin/grades/import đã xoá)
--   • Bỏ phân biệt source (admin/self) — tất cả điểm là SV tự khai
--   • Bỏ grades_locked — không còn admin lock SV
--   • Bỏ official_earned_credits — không còn nguồn "official", credits tính
--     live từ user_grades.passed=True
--
-- Idempotent: dùng IF EXISTS để chạy lại an toàn.

-- user_grades: drop source field (chỉ còn 1 source duy nhất là SV tự khai)
ALTER TABLE user_grades DROP COLUMN IF EXISTS source;

-- users: drop grades_locked, official_earned_credits
ALTER TABLE users DROP COLUMN IF EXISTS grades_locked;
ALTER TABLE users DROP COLUMN IF EXISTS official_earned_credits;
