-- Migration: add specialization column to users table
-- Date: 2026-03-27

ALTER TABLE users ADD COLUMN IF NOT EXISTS specialization TEXT;
