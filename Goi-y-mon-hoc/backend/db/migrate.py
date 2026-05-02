"""
One-time migration script — safe to run multiple times (uses IF NOT EXISTS).
Run: python -m backend.db.migrate
"""
from sqlalchemy import text
from backend.db.db import engine, Base
from backend.db import models  # noqa: F401 — ensures all models are registered

MIGRATIONS = [
    # ── users: new profile columns ───────────────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS career_goal TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS career_skills JSONB",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS difficulty_preference TEXT",
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS max_credits_per_term NUMERIC(4,1)",

    # ── users: role column (admin vs student) ────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT 'student'",

    # ── grade integrity: khoá bảng điểm + nguồn xác thực ─────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS grades_locked BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE user_grades ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'self'",
    "CREATE INDEX IF NOT EXISTS ix_user_grades_source ON user_grades(source)",

    # ── user_quiz_results: kết quả Holland-lite (auto-create qua create_all) ─
    # Bảng được tạo bởi Base.metadata.create_all — không cần ALTER

    # ── chat: thread support ─────────────────────────────────────────────────
    "ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS thread_id TEXT REFERENCES chat_threads(id) ON DELETE CASCADE",

    # ── users: google oauth ──────────────────────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT UNIQUE",

    # ── users: managed_specialization for advisors ───────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS managed_specialization TEXT",

    # ── users: cohort (khoá tuyển) — dùng để advisor filter sinh viên ────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS cohort TEXT",
    "CREATE INDEX IF NOT EXISTS ix_users_cohort ON users(cohort)",

    # Backfill cohort cho student đã có (cohort NULL) — derive từ pattern MSSV.
    # Idempotent: chỉ update row có cohort NULL match pattern.
    """
    UPDATE users SET cohort = SUBSTRING(username FROM 3 FOR 2)
    WHERE role='student' AND cohort IS NULL AND username ~ '^sv[0-9]{5}$'
    """,
    """
    UPDATE users SET cohort = SUBSTRING(username FROM 3 FOR 2)
    WHERE role='student' AND cohort IS NULL AND username ~ '^SV[0-9]{6}$'
    """,
    """
    UPDATE users SET cohort = SUBSTRING(username FROM 1 FOR 2)
    WHERE role='student' AND cohort IS NULL AND username ~ '^[0-9]{10}$'
    """,

    # ── users: email + first-login setup flow ────────────────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS email TEXT",
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_email'
        ) THEN
            ALTER TABLE users ADD CONSTRAINT uq_users_email UNIQUE (email);
        END IF;
    END $$
    """,
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_first_login BOOLEAN NOT NULL DEFAULT TRUE",
    # Sync is_first_login với trạng thái thực: idempotent cả 2 chiều.
    # Logic: email IS NOT NULL ↔ đã onboard (FALSE). email IS NULL ↔ cần setup (TRUE).
    #   - SV mới admin tạo (email=NULL) → TRUE
    #   - SV onboarded → FALSE
    #   - SV recovered (email cleared) → TRUE (ép setup lại)
    # Chỉ áp dụng role='student' để không phá state advisor/admin.
    """
    UPDATE users SET is_first_login = FALSE
    WHERE is_first_login = TRUE AND email IS NOT NULL
    """,
    """
    UPDATE users SET is_first_login = TRUE
    WHERE role = 'student' AND email IS NULL AND is_first_login = FALSE
    """,

    # ── password_reset_tokens ────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        token_hash TEXT NOT NULL UNIQUE,
        expires_at TIMESTAMPTZ NOT NULL,
        used_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_prt_user ON password_reset_tokens(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_prt_expires ON password_reset_tokens(expires_at)",

    # ── courses: description ─────────────────────────────────────────────────
    "ALTER TABLE courses ADD COLUMN IF NOT EXISTS description TEXT",

    # ── UNIQUE constraints: prevent duplicate records ─────────────────────────
    # user_grades: một sinh viên chỉ có một bản ghi tốt nhất mỗi môn
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_user_grades_user_course'
        ) THEN
            ALTER TABLE user_grades ADD CONSTRAINT uq_user_grades_user_course
                UNIQUE (user_id, course_code);
        END IF;
    END $$
    """,
    # course_prerequisites: không trùng lặp quan hệ tiên quyết
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_course_prereq'
        ) THEN
            ALTER TABLE course_prerequisites ADD CONSTRAINT uq_course_prereq
                UNIQUE (course_code, prerequisite_code);
        END IF;
    END $$
    """,
    # study_plan_items: một môn xuất hiện một lần trong mỗi kế hoạch
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_study_plan_item'
        ) THEN
            ALTER TABLE study_plan_items ADD CONSTRAINT uq_study_plan_item
                UNIQUE (plan_id, course_code);
        END IF;
    END $$
    """,
    # semester_offerings: không trùng lặp môn mở trong cùng học kỳ
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_semester_offering'
        ) THEN
            ALTER TABLE semester_offerings ADD CONSTRAINT uq_semester_offering
                UNIQUE (course_code, semester_label);
        END IF;
    END $$
    """,

    # ── user_skill_progress: tiến độ học kỹ năng nghề nghiệp ────────────────
    """
    CREATE TABLE IF NOT EXISTS user_skill_progress (
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        skill_id TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'not_started',
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, skill_id)
    )
    """,

    # ── user_messages: tin nhắn cá nhân từ admin → sinh viên ─────────────────
    """
    CREATE TABLE IF NOT EXISTS user_messages (
        id BIGSERIAL PRIMARY KEY,
        sender_id BIGINT REFERENCES users(id) ON DELETE SET NULL,
        sender_username TEXT,
        recipient_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        type TEXT NOT NULL DEFAULT 'info',
        is_read BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_user_messages_recipient ON user_messages(recipient_id)",

    # ── graduation threshold: CTDT 7480201 = 153 TC (bao gồm TT + ĐATN) ─────
    """
    INSERT INTO system_config (key, value)
    VALUES ('graduation_credit_threshold', '153')
    ON CONFLICT (key) DO UPDATE SET value = '153'
    """,

    # ── non-counting courses: GDTC, QPAN, Tiếng Anh tăng cường ─────────────
    # These courses do not count toward the official TC tích lũy (confirmed from
    # real transcripts). Safe to run multiple times.
    # Step 1: Ensure QPAN certificate courses exist (they appear in real transcripts
    # but may not be imported from the CTDT file since they are taught separately).
    """
    INSERT INTO courses (course_code, course_name, credits, count_toward_credits)
    VALUES
        ('7300103', 'Đường lối quốc phòng và an ninh của Đảng CSVN', 2, FALSE),
        ('7300104', 'Công tác quốc phòng và an ninh', 2, FALSE),
        ('7300202', 'Quân sự chung', 3, FALSE),
        ('7300203', 'Kỹ thuật bắn súng tiểu liên AK và chiến thuật', 4, FALSE),
        ('7010610', 'Tiếng Anh tăng cường 1', 3, FALSE)
    ON CONFLICT (course_code) DO UPDATE SET count_toward_credits = FALSE
    """,
    # Step 2: Ensure all other known non-counting courses are flagged correctly.
    """
    UPDATE courses
    SET count_toward_credits = FALSE
    WHERE course_code IN (
        '7010701', '7010702', '7010703',
        '7300101', '7300102', '7300201',
        '7300103', '7300104', '7300202', '7300203',
        '7010610'
    )
    """,

    # ── schedule_entries: lịch học cá nhân ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS schedule_entries (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        course_code TEXT,
        course_name TEXT NOT NULL,
        day_of_week TEXT NOT NULL,
        start_time TEXT NOT NULL,
        end_time TEXT NOT NULL,
        start_date TEXT,
        end_date TEXT,
        room TEXT,
        color TEXT NOT NULL DEFAULT '#3b82f6',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,

    # ── advisor_assignments: phân công cố vấn ───────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS advisor_assignments (
        id BIGSERIAL PRIMARY KEY,
        advisor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        student_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        assigned_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_advisor_assignment UNIQUE (advisor_id, student_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_advisor_assignments_advisor ON advisor_assignments(advisor_id)",
    "CREATE INDEX IF NOT EXISTS ix_advisor_assignments_student ON advisor_assignments(student_id)",

    # ── advisor_notes: ghi chú tư vấn ───────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS advisor_notes (
        id BIGSERIAL PRIMARY KEY,
        advisor_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        student_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_advisor_notes_advisor ON advisor_notes(advisor_id)",
    "CREATE INDEX IF NOT EXISTS ix_advisor_notes_student ON advisor_notes(student_id)",

    # ── direct_messages: tin nhắn 1-1 (SV ↔ cố vấn) ─────────────────────────
    """
    CREATE TABLE IF NOT EXISTS direct_messages (
        id BIGSERIAL PRIMARY KEY,
        sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        receiver_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        read_at TIMESTAMPTZ
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_direct_messages_sender ON direct_messages(sender_id)",
    "CREATE INDEX IF NOT EXISTS ix_direct_messages_receiver ON direct_messages(receiver_id)",
    "CREATE INDEX IF NOT EXISTS ix_direct_messages_created ON direct_messages(created_at)",

    # ── chat_groups: nhóm chat ────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS chat_groups (
        id BIGSERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        created_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        muted_by JSONB NOT NULL DEFAULT '[]'
    )
    """,

    # ── chat_group_members: thành viên nhóm ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS chat_group_members (
        group_id BIGINT NOT NULL REFERENCES chat_groups(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        joined_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (group_id, user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_chat_group_members_user ON chat_group_members(user_id)",

    # ── group_messages: tin nhắn nhóm ─────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS group_messages (
        id BIGSERIAL PRIMARY KEY,
        group_id BIGINT NOT NULL REFERENCES chat_groups(id) ON DELETE CASCADE,
        sender_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_group_messages_group ON group_messages(group_id)",
    "CREATE INDEX IF NOT EXISTS ix_group_messages_created ON group_messages(created_at)",

    # ── user_connections: lời mời kết nối ────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS user_connections (
        id BIGSERIAL PRIMARY KEY,
        from_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        to_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_user_connection UNIQUE (from_id, to_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_user_connections_from ON user_connections(from_id)",
    "CREATE INDEX IF NOT EXISTS ix_user_connections_to ON user_connections(to_id)",

    # ── users: default_password (plain-text, cleared on first password change) ─
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS default_password TEXT",

    # ── users: is_head_of_department — trưởng bộ môn cho advisor ───────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_head_of_department BOOLEAN NOT NULL DEFAULT FALSE",

    # ── planned_electives: môn tự chọn SV đã plan trong lộ trình ─────────────
    """
    CREATE TABLE IF NOT EXISTS planned_electives (
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        term_label TEXT NOT NULL,
        slot_id TEXT NOT NULL,
        course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (user_id, term_label, slot_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_planned_electives_user ON planned_electives(user_id)",

    # ── users: teacher_code — mã GV cho advisor (VD: GV0001) ────────────────────
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS teacher_code VARCHAR(20)",
    """
    DO $$ BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_constraint WHERE conname = 'uq_users_teacher_code'
        ) THEN
            ALTER TABLE users ADD CONSTRAINT uq_users_teacher_code UNIQUE (teacher_code);
        END IF;
    END $$
    """,

    # ── Rename student usernames to SV{cohort}{seq:04d} format ──────────────────
    # Old format: 2400000001 (10-digit numeric, first 2 = cohort)
    # New format: SV240001   (SV prefix + cohort + 4-digit sequence)
    # Grades / assignments use user_id FK — unaffected by username rename.
    # Already-SV usernames are skipped automatically.
    """
    DO $$
    DECLARE
        rec        RECORD;
        prev_cohort TEXT    := '';
        counter     INT     := 0;
        new_uname   TEXT;
        cohort      TEXT;
    BEGIN
        FOR rec IN
            SELECT id, username,
                   LEFT(username, 2) AS cohort_key
            FROM   users
            WHERE  role = 'student'
              AND  username ~ '^[0-9]{10}$'
            ORDER  BY LEFT(username, 2), id
        LOOP
            cohort := rec.cohort_key;

            -- On cohort change, start counter after highest existing SV-seq for this cohort
            IF cohort <> prev_cohort THEN
                SELECT COALESCE(
                    MAX(CAST(SUBSTRING(u2.username FROM 5) AS INT)), 0
                )
                INTO counter
                FROM users u2
                WHERE u2.role = 'student'
                  AND u2.username ~ ('^SV' || cohort || '[0-9]{4}$');
                prev_cohort := cohort;
            END IF;

            counter    := counter + 1;
            new_uname  := 'SV' || cohort || LPAD(counter::TEXT, 4, '0');

            -- Guard against accidental collision
            WHILE EXISTS (SELECT 1 FROM users WHERE username = new_uname) LOOP
                counter   := counter + 1;
                new_uname := 'SV' || cohort || LPAD(counter::TEXT, 4, '0');
            END LOOP;

            UPDATE users SET username = new_uname WHERE id = rec.id;
        END LOOP;
    END $$
    """,

    # ── system_notifications: target_type, target_value, severity ───────────────
    "ALTER TABLE system_notifications ADD COLUMN IF NOT EXISTS severity VARCHAR(10) NOT NULL DEFAULT 'info'",
    "ALTER TABLE system_notifications ADD COLUMN IF NOT EXISTS target_type VARCHAR(30) DEFAULT 'all'",
    "ALTER TABLE system_notifications ADD COLUMN IF NOT EXISTS target_value TEXT",

    # ── notification_reads: đánh dấu đã đọc ──────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS notification_reads (
        id BIGSERIAL PRIMARY KEY,
        notification_id BIGINT NOT NULL REFERENCES system_notifications(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        read_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_notification_read UNIQUE (notification_id, user_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_notification_reads_user ON notification_reads(user_id)",
    "CREATE INDEX IF NOT EXISTS ix_notification_reads_notif ON notification_reads(notification_id)",

    # VIỆC 7: backfill dữ liệu cũ
    "UPDATE system_notifications SET target_type = 'all' WHERE target_type IS NULL",
    "UPDATE system_notifications SET severity = COALESCE(type, 'info') WHERE severity = 'info' AND type IS NOT NULL",

    # ── courses: typical_semester for plan view drag-drop ────────────────────────
    "ALTER TABLE courses ADD COLUMN IF NOT EXISTS typical_semester INTEGER",

    # ── Fix required_specialization: Vietnamese display names → spec codes ────────
    # Old values were stored as full Vietnamese names by the docx importer.
    # All three tables (courses, course_elective_groups, elective_rules) are fixed.
    "UPDATE courses SET required_specialization = '7480201_07' WHERE required_specialization = 'Khoa học máy tính'",
    "UPDATE courses SET required_specialization = '7480201_06' WHERE required_specialization = 'Mạng máy tính'",
    "UPDATE courses SET required_specialization = '7480201_05' WHERE required_specialization = 'Công nghệ phần mềm'",
    "UPDATE courses SET required_specialization = '7480201_09' WHERE required_specialization = 'Hệ thống thông tin'",
    "UPDATE courses SET required_specialization = '7480201_04' WHERE required_specialization = 'Tin học kinh tế'",
    "UPDATE courses SET required_specialization = '7480201_08' WHERE required_specialization IN ('Công nghệ thông tin Địa học', 'Công nghệ thông tin đa học', 'Công nghệ thông tin địa học')",
    "UPDATE course_elective_groups SET specialization = '7480201_07' WHERE specialization = 'Khoa học máy tính'",
    "UPDATE course_elective_groups SET specialization = '7480201_06' WHERE specialization = 'Mạng máy tính'",
    "UPDATE course_elective_groups SET specialization = '7480201_05' WHERE specialization = 'Công nghệ phần mềm'",
    "UPDATE course_elective_groups SET specialization = '7480201_09' WHERE specialization = 'Hệ thống thông tin'",
    "UPDATE course_elective_groups SET specialization = '7480201_04' WHERE specialization = 'Tin học kinh tế'",
    "UPDATE course_elective_groups SET specialization = '7480201_08' WHERE specialization IN ('Công nghệ thông tin Địa học', 'Công nghệ thông tin đa học', 'Công nghệ thông tin địa học')",
    "UPDATE elective_rules SET specialization = '7480201_07' WHERE specialization = 'Khoa học máy tính'",
    "UPDATE elective_rules SET specialization = '7480201_06' WHERE specialization = 'Mạng máy tính'",
    "UPDATE elective_rules SET specialization = '7480201_05' WHERE specialization = 'Công nghệ phần mềm'",
    "UPDATE elective_rules SET specialization = '7480201_09' WHERE specialization = 'Hệ thống thông tin'",
    "UPDATE elective_rules SET specialization = '7480201_04' WHERE specialization = 'Tin học kinh tế'",
    "UPDATE elective_rules SET specialization = '7480201_08' WHERE specialization IN ('Công nghệ thông tin Địa học', 'Công nghệ thông tin đa học', 'Công nghệ thông tin địa học')",

    # ── users.specialization: Vietnamese names → spec codes ─────────────────────
    "UPDATE users SET specialization = '7480201_07' WHERE role = 'student' AND specialization = 'Khoa học máy tính'",
    "UPDATE users SET specialization = '7480201_06' WHERE role = 'student' AND specialization = 'Mạng máy tính'",
    "UPDATE users SET specialization = '7480201_05' WHERE role = 'student' AND specialization = 'Công nghệ phần mềm'",
    "UPDATE users SET specialization = '7480201_09' WHERE role = 'student' AND specialization = 'Hệ thống thông tin'",
    "UPDATE users SET specialization = '7480201_04' WHERE role = 'student' AND specialization = 'Tin học kinh tế'",
    "UPDATE users SET specialization = '7480201_08' WHERE role = 'student' AND specialization IN ('Công nghệ thông tin Địa học', 'Công nghệ thông tin đa học', 'Công nghệ thông tin địa học')",

    # ── advisor_notes.course_code: gắn note vào 1 môn học cụ thể (F4) ───────────
    "ALTER TABLE advisor_notes ADD COLUMN IF NOT EXISTS course_code VARCHAR(20)",
    "CREATE INDEX IF NOT EXISTS ix_advisor_notes_course_code ON advisor_notes(course_code)",

    # ── study_plans.updated_at: hỗ trợ hiển thị "lần sửa cuối" cho advisor ──────
    "ALTER TABLE study_plans ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NULL",

    # ── advisor_assignments: enforce 1 SV = 1 advisor ──────────────────────────
    # Bước 1: xóa duplicate, giữ lại assignment có advisor cùng managed_specialization
    # với SV (specialty match), fallback assignment mới nhất.
    """
    DO $$
    DECLARE r RECORD;
    BEGIN
        -- Phase A: với SV có nhiều assignment, giữ assignment có spec match
        FOR r IN
            SELECT student_id
            FROM advisor_assignments
            GROUP BY student_id
            HAVING COUNT(*) > 1
        LOOP
            -- Ưu tiên 1: spec match
            DELETE FROM advisor_assignments aa
            WHERE aa.student_id = r.student_id
            AND aa.id NOT IN (
                SELECT aa2.id FROM advisor_assignments aa2
                JOIN users sv ON sv.id = aa2.student_id
                JOIN users gv ON gv.id = aa2.advisor_id
                WHERE aa2.student_id = r.student_id
                AND (
                    -- Convert SV's spec name to code or vice versa
                    sv.specialization = gv.managed_specialization
                    OR (sv.specialization = 'Khoa học máy tính' AND gv.managed_specialization = '7480201_07')
                    OR (sv.specialization = 'Mạng máy tính' AND gv.managed_specialization = '7480201_06')
                    OR (sv.specialization = 'Công nghệ phần mềm' AND gv.managed_specialization = '7480201_05')
                    OR (sv.specialization = 'Hệ thống thông tin' AND gv.managed_specialization = '7480201_09')
                    OR (sv.specialization = 'Tin học kinh tế' AND gv.managed_specialization = '7480201_04')
                    OR (sv.specialization LIKE 'Công nghệ thông tin %' AND gv.managed_specialization = '7480201_08')
                )
                ORDER BY aa2.assigned_at DESC
                LIMIT 1
            );
        END LOOP;

        -- Phase B: SV còn lại nhiều assignment (không match spec), giữ assignment mới nhất
        FOR r IN
            SELECT student_id
            FROM advisor_assignments
            GROUP BY student_id
            HAVING COUNT(*) > 1
        LOOP
            DELETE FROM advisor_assignments aa
            WHERE aa.student_id = r.student_id
            AND aa.id NOT IN (
                SELECT id FROM advisor_assignments aa2
                WHERE aa2.student_id = r.student_id
                ORDER BY assigned_at DESC, id DESC
                LIMIT 1
            );
        END LOOP;
    END $$;
    """,
    # Bước 2: thêm UNIQUE constraint trên student_id (sau khi đã clean dups)
    """
    DO $$
    BEGIN
        -- Drop old composite unique if it exists
        IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_advisor_assignment') THEN
            ALTER TABLE advisor_assignments DROP CONSTRAINT uq_advisor_assignment;
        END IF;
        -- Add new unique on student_id only (idempotent)
        IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'uq_advisor_assignment_student') THEN
            ALTER TABLE advisor_assignments ADD CONSTRAINT uq_advisor_assignment_student UNIQUE (student_id);
        END IF;
    END $$;
    """,

    # ── course_ratings: đánh giá môn học của sinh viên ──────────────────────────
    """
    CREATE TABLE IF NOT EXISTS course_ratings (
        id BIGSERIAL PRIMARY KEY,
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        review TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        CONSTRAINT uq_course_rating UNIQUE (user_id, course_code)
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_course_ratings_course ON course_ratings(course_code)",
    "CREATE INDEX IF NOT EXISTS ix_course_ratings_user ON course_ratings(user_id)",

    # ── career paths ───────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS career_paths (
        id BIGSERIAL PRIMARY KEY,
        code VARCHAR(32) UNIQUE NOT NULL,
        name TEXT NOT NULL,
        short_description TEXT,
        long_description TEXT,
        icon VARCHAR(64),
        color VARCHAR(32),
        domain_profile JSON,
        created_at TIMESTAMP NOT NULL DEFAULT NOW()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_career_paths_code ON career_paths(code)",

    """
    CREATE TABLE IF NOT EXISTS career_skills (
        id BIGSERIAL PRIMARY KEY,
        path_id BIGINT NOT NULL REFERENCES career_paths(id) ON DELETE CASCADE,
        skill_name TEXT NOT NULL,
        skill_type VARCHAR(32) NOT NULL,
        level VARCHAR(16),
        priority INTEGER NOT NULL DEFAULT 2,
        source_type VARCHAR(32),
        source_name TEXT,
        source_url TEXT,
        description TEXT,
        estimated_hours INTEGER
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_career_skills_path ON career_skills(path_id)",

    """
    CREATE TABLE IF NOT EXISTS career_course_mapping (
        path_id BIGINT NOT NULL REFERENCES career_paths(id) ON DELETE CASCADE,
        course_code TEXT NOT NULL REFERENCES courses(course_code) ON DELETE CASCADE,
        relevance NUMERIC(3,2) NOT NULL DEFAULT 1.0,
        PRIMARY KEY (path_id, course_code)
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS user_career_choice (
        user_id BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        primary_path_id BIGINT REFERENCES career_paths(id) ON DELETE SET NULL,
        secondary_path_id BIGINT REFERENCES career_paths(id) ON DELETE SET NULL,
        chosen_at TIMESTAMP NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMP NULL
    )
    """,

    """
    CREATE TABLE IF NOT EXISTS user_career_skill_progress (
        user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        skill_id BIGINT NOT NULL REFERENCES career_skills(id) ON DELETE CASCADE,
        status VARCHAR(16) NOT NULL DEFAULT 'planned',
        completed_at TIMESTAMP NULL,
        note TEXT,
        PRIMARY KEY (user_id, skill_id)
    )
    """,

    # Seed: generate sample ratings from students who already passed courses
    # Uses DO block so it's safe to run multiple times (ON CONFLICT DO NOTHING)
    """
    DO $$
    DECLARE
        rec RECORD;
        r_val INTEGER;
    BEGIN
        FOR rec IN
            SELECT DISTINCT ug.user_id, ug.course_code
            FROM user_grades ug
            JOIN users u ON u.id = ug.user_id AND u.role = 'student'
            WHERE ug.passed = TRUE
            ORDER BY ug.user_id, ug.course_code
            LIMIT 300
        LOOP
            -- Deterministic but varied rating based on user_id + course hash
            r_val := 3 + ((rec.user_id * 7 + LENGTH(rec.course_code) * 13) % 3);
            -- r_val is 3, 4, or 5 (weighted toward positive — students rate after passing)
            INSERT INTO course_ratings (user_id, course_code, rating)
            VALUES (rec.user_id, rec.course_code, r_val)
            ON CONFLICT (user_id, course_code) DO NOTHING;
        END LOOP;
    END $$
    """,

    # ── Backfill teacher_code for existing advisors (cách 2: giữ username cũ) ───
    # Sinh mã GV0001, GV0002... theo thứ tự created_at cho advisor chưa có mã.
    # Nếu username đã có format GVxxxx thì reuse, không sinh mới.
    """
    DO $$
    DECLARE
        rec RECORD;
        counter INT := 0;
        new_code VARCHAR(20);
    BEGIN
        FOR rec IN
            SELECT id, username
            FROM users
            WHERE role = 'advisor' AND teacher_code IS NULL
            ORDER BY id
        LOOP
            -- Reuse username nếu đúng format GVxxxx
            IF rec.username ~ '^GV[0-9]{4}$' THEN
                new_code := rec.username;
            ELSE
                -- Sinh mã mới, tăng dần cho đến khi không trùng
                LOOP
                    counter := counter + 1;
                    new_code := 'GV' || LPAD(counter::TEXT, 4, '0');
                    EXIT WHEN NOT EXISTS (
                        SELECT 1 FROM users WHERE teacher_code = new_code
                    );
                END LOOP;
            END IF;
            UPDATE users SET teacher_code = new_code WHERE id = rec.id;
        END LOOP;
    END $$
    """,

    # ════════════════════════════════════════════════════════════════════════
    # V2 — Lộ trình tích hợp (2026-04-30)
    # Mở rộng career_skills + user_career_skill_progress để hỗ trợ:
    #   - Nhóm skill (Lập trình cơ bản / Backend Frameworks / DevOps...)
    #   - Đánh dấu skill có/không có trong CTĐT (school_covered + school_courses[])
    #   - Lên lịch học mục ngoài trường vào học kỳ cụ thể (scheduled_term)
    #   - Track lần AI sinh blueprint cuối cho 1 nghề (last_blueprint_at)
    # ════════════════════════════════════════════════════════════════════════
    "ALTER TABLE career_skills ADD COLUMN IF NOT EXISTS skill_group TEXT NOT NULL DEFAULT 'Khác'",
    "ALTER TABLE career_skills ADD COLUMN IF NOT EXISTS school_courses JSON",
    "ALTER TABLE career_skills ADD COLUMN IF NOT EXISTS school_covered BOOLEAN NOT NULL DEFAULT FALSE",
    "CREATE INDEX IF NOT EXISTS ix_career_skills_group ON career_skills(path_id, skill_group)",

    "ALTER TABLE user_career_skill_progress ADD COLUMN IF NOT EXISTS scheduled_term VARCHAR(20)",
    "CREATE INDEX IF NOT EXISTS ix_ucsp_scheduled_term ON user_career_skill_progress(user_id, scheduled_term)",

    "ALTER TABLE career_paths ADD COLUMN IF NOT EXISTS last_blueprint_at TIMESTAMPTZ",
    "ALTER TABLE career_paths ADD COLUMN IF NOT EXISTS blueprint_model TEXT",
]


def _populate_typical_semester():
    """Populate courses.typical_semester from CURRICULUM_ORDER + static CTDT plan data."""
    from backend.core.academic_engine import CURRICULUM_ORDER
    from backend.db import models as _m
    from backend.db.db import SessionLocal
    db = SessionLocal()
    try:
        # Group codes by semester from CURRICULUM_ORDER
        sem_map: dict[int, list[str]] = {}
        for code, sem in CURRICULUM_ORDER.items():
            sem_map.setdefault(sem, []).append(code)

        # Pool A semesters (from static _CTDT_POOL_A)
        POOL_A_SEMS = {
            '7010108': 3, '7080121': 3, '7080226': 3,
            '7080219': 4, '7080636': 4, '7010607': 4,
            '7010608': 5, '7080622': 5,
        }
        # Pool B semesters (HK7) — unique codes across all specs
        POOL_B_HK7 = [
            '7080107','7080124','7080516','7080518','7080520',
            '7080511','7080716','7080724','7080730','7080731','7080732',
            '7080109','7080115','7080123','7080234',
            '7080202','7080205','7080209','7080214','7080217','7080634',
            '7080605','7080615','7080627','7080628','7080635',
            '7050362','7080302','7080321','7080323','7080324','7080402','7080405',
        ]
        # Pool C semesters (HK8) — only codes NOT already covered by pool B or common
        POOL_C_HK8 = [
            '7080316','7080319','7080505','7080507',
            '7000002','7000004','7080118','7080308',
            '7080103','7080105','7080117','7080120','7080502','7080610','7080618',
            '7080215','7080220','7080230','7080232','7080310','7080609',
            '7080631','7080637',
            '7080301','7080307','7080325','7080406','7080407','7080408','7080541',
        ]

        updated = 0
        # CURRICULUM_ORDER courses
        for sem, codes in sem_map.items():
            n = db.query(_m.Course).filter(
                _m.Course.course_code.in_(codes),
                _m.Course.typical_semester == None,
            ).update({"typical_semester": sem}, synchronize_session=False)
            updated += n

        # Pool A
        for code, sem in POOL_A_SEMS.items():
            db.query(_m.Course).filter(
                _m.Course.course_code == code,
                _m.Course.typical_semester == None,
            ).update({"typical_semester": sem}, synchronize_session=False)

        # Pool B (HK7)
        db.query(_m.Course).filter(
            _m.Course.course_code.in_(POOL_B_HK7),
            _m.Course.typical_semester == None,
        ).update({"typical_semester": 7}, synchronize_session=False)

        # Pool C (HK8) — only where not already set
        db.query(_m.Course).filter(
            _m.Course.course_code.in_(POOL_C_HK8),
            _m.Course.typical_semester == None,
        ).update({"typical_semester": 8}, synchronize_session=False)

        db.commit()
        print(f"[migrate] typical_semester populated for courses")
    except Exception as e:
        db.rollback()
        print(f"[migrate] typical_semester population failed: {e}")
    finally:
        db.close()


def run():
    # Create any brand-new tables that don't exist yet
    Base.metadata.create_all(bind=engine)
    print("[migrate] create_all done (new tables, if any)")

    # Run each statement in its own transaction so one failure doesn't abort the rest
    for stmt in MIGRATIONS:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            print(f"[migrate] OK  : {stmt[:80]}")
        except Exception as exc:
            print(f"[migrate] SKIP: {stmt[:80]}\n         reason: {exc}")

    _populate_typical_semester()
    print("[migrate] finished.")


if __name__ == "__main__":
    run()
