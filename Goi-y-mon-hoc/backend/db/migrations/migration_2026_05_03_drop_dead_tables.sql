-- Migration: Drop 3 dead tables (no endpoint references)
-- Date: 2026-05-03
-- Reason: Cleanup before final report — these tables were designed but never wired up
--   - user_messages       : duplicate of system_notifications + direct_messages
--   - user_quiz_results   : Holland RIASEC quiz feature, never had POST endpoint or UI
--   - risk_history        : daily snapshot table, no read endpoint, never used
-- All ORM models, schemas, and helper functions have also been removed in the same change.

DROP TABLE IF EXISTS user_messages CASCADE;
DROP TABLE IF EXISTS user_quiz_results CASCADE;
DROP TABLE IF EXISTS risk_history CASCADE;
