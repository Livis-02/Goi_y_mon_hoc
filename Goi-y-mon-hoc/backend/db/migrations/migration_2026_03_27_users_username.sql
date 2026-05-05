-- Migration: users.email -> users.username (if needed)
DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'email'
    )
    AND NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'users' AND column_name = 'username'
    ) THEN
        ALTER TABLE users RENAME COLUMN email TO username;
    END IF;
END $$;
