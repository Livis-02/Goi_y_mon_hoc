-- migration_2026_05_02_dedupe_dept_heads.sql
--
-- Bug: tab Cố vấn ở admin hiển thị 2 trưởng bộ môn KHMT.
-- Nguyên nhân: data DB hiện tại có >1 advisor cùng managed_specialization với
-- is_head_of_department=true. Có thể do seed script trước đây hoặc lỗi race
-- trong import.
--
-- Fix:
-- 1. Cho mỗi (managed_specialization), giữ lại 1 head duy nhất (theo id nhỏ nhất
--    = người được tạo trước = lâu năm nhất trong hệ thống).
-- 2. Demote tất cả head khác cùng spec.
-- Idempotent: chạy nhiều lần không sai.

UPDATE users u
SET is_head_of_department = false
WHERE u.role = 'advisor'
  AND u.is_head_of_department = true
  AND u.id NOT IN (
    SELECT MIN(id)
    FROM users
    WHERE role = 'advisor'
      AND is_head_of_department = true
    GROUP BY managed_specialization
  );

-- Sau migration: verify mỗi managed_specialization có TỐI ĐA 1 head:
--   SELECT managed_specialization, COUNT(*)
--   FROM users
--   WHERE role='advisor' AND is_head_of_department=true
--   GROUP BY managed_specialization
--   HAVING COUNT(*) > 1;
-- Query trên phải trả về 0 row.
