-- Migration 2026-05-05: drop columns không được code đọc/ghi
--
-- Bối cảnh: audit toàn bộ backend (main.py + core/* + scripts/*) phát hiện 9 cột
-- 0 references trong code thực thi:
--   • chat_group_members.joined_at  — chưa hiển thị thời điểm join ở bất kỳ UI nào
--   • risk_cases.* (8 cột)          — model RiskCase được thiết kế cho workflow
--                                     đầy đủ nhưng MVP chỉ implement track state.
--                                     Khi cần triển khai full workflow, restore
--                                     lại các cột này qua migration sau.
--
-- Tác động: schema khớp với code → ER diagram trong báo cáo phân tích thiết kế
-- không còn "noise" (cột tồn tại nhưng vô nghĩa với hệ thống).
--
-- Idempotent: dùng IF EXISTS để chạy lại an toàn.

-- chat_group_members
ALTER TABLE chat_group_members DROP COLUMN IF EXISTS joined_at;

-- risk_cases — drop 8 cột thiết kế cho workflow đầy đủ chưa implement
ALTER TABLE risk_cases DROP COLUMN IF EXISTS opened_at;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS closed_at;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS opened_risk_score;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS current_risk_score;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS opened_reason;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS opened_factors;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS close_reason;
ALTER TABLE risk_cases DROP COLUMN IF EXISTS next_check_at;
