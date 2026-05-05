from sqlalchemy import Column, Boolean, BigInteger, Integer, ForeignKey, DateTime, Text, Numeric, UniqueConstraint, Index, PrimaryKeyConstraint, JSON, String
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=True)
    specialization = Column(Text, nullable=True)
    cohort = Column(Text, nullable=True, index=True)  # student only: khoá tuyển (vd "K20", "2020")
    role = Column(Text, nullable=False, server_default="student")  # "student" | "advisor" | "admin"
    managed_specialization = Column(Text, nullable=True)  # advisor only: chuyên ngành SV được phụ trách
    teacher_code = Column(Text, unique=True, nullable=True)  # advisor only: mã GV (VD: GV0001)
    # student only: thuộc lớp nào. ON DELETE SET NULL → khi xoá lớp, SV về NULL tạm thời (admin re-assign)
    class_group_id = Column(BigInteger, ForeignKey("class_groups.id", ondelete="SET NULL"), nullable=True, index=True)
    is_first_login = Column(Boolean, nullable=False, server_default="true")
    default_password = Column(Text, nullable=True)  # plain-text default pw; cleared when user changes password
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, unique=True, index=True, nullable=False)
    course_name = Column(Text, nullable=False)
    credits = Column(Numeric(4, 1), nullable=True)
    required_specialization = Column(Text, nullable=True)  # NULL = shared; non-null = only required for this specialization
    count_toward_credits = Column(Boolean, nullable=False, server_default="true")  # False for GDTC, military practical, etc.
    description = Column(Text, nullable=True)
    typical_semester = Column(Integer, nullable=True)  # HK theo CTĐT (1-9); overrides CURRICULUM_ORDER in plan view


class ElectiveRule(Base):
    __tablename__ = "elective_rules"

    id = Column(BigInteger, primary_key=True, index=True)
    program_code = Column(Text, nullable=False)
    specialization = Column(Text, nullable=False)
    group_type = Column(Text, nullable=False)
    min_credits_required = Column(Numeric(4, 1), nullable=False)


class UserGrade(Base):
    __tablename__ = "user_grades"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="RESTRICT"), nullable=False)
    score10 = Column(Numeric(4, 2), nullable=True)
    score4 = Column(Numeric(3, 2), nullable=True)
    letter = Column(Text, nullable=True)
    passed = Column(Boolean, nullable=False, default=False)
    term = Column(Text, nullable=True)
    uploaded_at = Column(DateTime, nullable=False, server_default=func.now())
    # Note: cột `source` đã DROP ở refactor 2026-05-05. EduGuide là tool cá nhân,
    # tất cả điểm đều do SV tự upload. Admin không import điểm chính thức nữa
    # (đã có SIS riêng của trường).


class CourseElectiveGroup(Base):
    """Maps a course to an elective group within a program/specialization."""
    __tablename__ = "course_elective_groups"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    program_code = Column(Text, nullable=False)
    specialization = Column(Text, nullable=False)
    group_type = Column(Text, nullable=False)


class CourseSpecialization(Base):
    """Quan hệ M2M: 1 môn có thể yêu cầu cho nhiều chuyên ngành.

    Course.required_specialization (legacy) vẫn được dùng và khi 1 môn chỉ thuộc
    đúng 1 CN thì giữ ở field đó. Khi thuộc nhiều CN: required_specialization=NULL
    và mỗi CN một row trong bảng này.
    """
    __tablename__ = "course_specializations"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    specialization = Column(Text, nullable=False, index=True)
    __table_args__ = (
        UniqueConstraint("course_code", "specialization", name="uq_course_spec_pair"),
    )


class Skill(Base):
    """Kỹ năng / nghề nghiệp gắn với môn học.

    Categories: programming / web / mobile / data / ai / network / security
                / db / business / softskill / other
    """
    __tablename__ = "skills"

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(Text, unique=True, nullable=False, index=True)  # vd: PYTHON, WEB_DEV, NLP
    name = Column(Text, nullable=False)                            # vd: "Python", "Phát triển Web"
    category = Column(Text, nullable=False)                        # bucket
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class CourseSkill(Base):
    """M2M giữa môn học và kỹ năng.

    Mỗi (course, skill) có weight 0.1-1.0 (default 1.0) để đánh dấu kỹ năng nào
    môn này dạy mạnh, kỹ năng nào chỉ phụ.
    """
    __tablename__ = "course_skills"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    skill_code = Column(Text, ForeignKey("skills.code", ondelete="CASCADE"), nullable=False, index=True)
    weight = Column(Numeric(3, 2), nullable=False, server_default="1.00")
    __table_args__ = (
        UniqueConstraint("course_code", "skill_code", name="uq_course_skill_pair"),
    )


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(Text, nullable=False)
    target_gpa = Column(Numeric(3, 2), nullable=True)
    max_credits_per_term = Column(Numeric(4, 1), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)


class StudyPlanItem(Base):
    __tablename__ = "study_plan_items"

    id = Column(BigInteger, primary_key=True, index=True)
    plan_id = Column(BigInteger, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="RESTRICT"), nullable=False)
    term_label = Column(Text, nullable=True)


class CoursePrerequisite(Base):
    """Records that course_code requires prerequisite_code to be completed first."""
    __tablename__ = "course_prerequisites"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    prerequisite_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False)


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id = Column(Text, primary_key=True)  # UUID string, generated client-side
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    thread_id = Column(Text, ForeignKey("chat_threads.id", ondelete="CASCADE"), nullable=True, index=True)
    role = Column(Text, nullable=False)
    intent = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class SystemConfig(Base):
    """Key-value store for application-level configuration."""
    __tablename__ = "system_config"

    key = Column(Text, primary_key=True)
    value = Column(Text, nullable=True)


class SemesterOffering(Base):
    """Records which courses are offered in a given semester."""
    __tablename__ = "semester_offerings"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    semester_label = Column(Text, nullable=False, index=True)
    is_open = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("course_code", "semester_label", name="uq_offering_course_semester"),
    )


class AuthToken(Base):
    """Persistent auth tokens with TTL. Replaces in-memory TOKENS dict."""
    __tablename__ = "auth_tokens"

    id = Column(BigInteger, primary_key=True, index=True)
    token_hash = Column(Text, unique=True, nullable=False, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    expires_at = Column(DateTime, nullable=False)


class CourseRegistration(Base):
    """Tracks which courses a student actually registered for each semester."""
    __tablename__ = "course_registrations"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="RESTRICT"), nullable=False)
    semester_label = Column(Text, nullable=False)
    registered_at = Column(DateTime, nullable=False, server_default=func.now())
    was_recommended = Column(Boolean, nullable=False, server_default="false")
    recommendation_score_at_time = Column(Numeric(6, 2), nullable=True)
    outcome = Column(Text, nullable=True)  # NULL=pending, "passed", "failed", "dropped"


class ScheduleEntry(Base):
    """Personal class schedule entry for a student."""
    __tablename__ = "schedule_entries"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code = Column(Text, nullable=True)
    course_name = Column(Text, nullable=False)
    day_of_week = Column(Text, nullable=False)   # "2","3","4","5","6","7" (Mon=2 … Sat=7)
    start_time = Column(Text, nullable=False)    # "HH:MM" 24h
    end_time = Column(Text, nullable=False)      # "HH:MM" 24h
    start_date = Column(Text, nullable=True)     # "YYYY-MM-DD", optional
    end_date = Column(Text, nullable=True)       # "YYYY-MM-DD", optional
    room = Column(Text, nullable=True)
    color = Column(Text, nullable=False, server_default="#3b82f6")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class LoginAttempt(Base):
    """DB-persisted failed login attempts for rate limiting. Survives restarts and works across workers."""
    __tablename__ = "login_attempts"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(Text, nullable=False, index=True)
    attempted_at = Column(DateTime, nullable=False, server_default=func.now())


class AdminLog(Base):
    """Audit trail for every significant admin action."""
    __tablename__ = "admin_logs"

    id = Column(BigInteger, primary_key=True, index=True)
    admin_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    admin_username = Column(Text, nullable=True)          # snapshot in case user deleted later
    action = Column(Text, nullable=False, index=True)     # e.g. CREATE_COURSE, DELETE_USER, SEND_NOTIF
    target_type = Column(Text, nullable=True)             # "course" | "user" | "prerequisite" | "notification"
    target_id = Column(Text, nullable=True)               # course_code / user_id / notif_id
    detail = Column(Text, nullable=True)                  # JSON blob — before/after values
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class SystemNotification(Base):
    """Broadcast notifications from admin to users, with flexible target groups."""
    __tablename__ = "system_notifications"

    id = Column(BigInteger, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    body = Column(Text, nullable=False)
    type = Column(Text, nullable=False, server_default="info")  # legacy, keep for compat
    severity = Column(Text, nullable=False, server_default="info")  # "info"|"warning"|"urgent"
    target_type = Column(Text, nullable=True, server_default="all")  # see VALID_TARGET_TYPES
    target_value = Column(Text, nullable=True)                       # CSV of cohorts/codes/etc.
    admin_id = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    admin_username = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class NotificationRead(Base):
    """Tracks which users have read which notifications."""
    __tablename__ = "notification_reads"

    id = Column(BigInteger, primary_key=True, index=True)
    notification_id = Column(BigInteger, ForeignKey("system_notifications.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    read_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("notification_id", "user_id", name="uq_notification_read"),
    )


class UserSkillProgress(Base):
    __tablename__ = "user_skill_progress"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    skill_id = Column(Text, nullable=False)   # "track_id.skill_id", e.g. "backend.docker"
    status = Column(Text, nullable=False, server_default="not_started")  # not_started | in_progress | completed
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (PrimaryKeyConstraint("user_id", "skill_id"),)


class AdvisorAssignment(Base):
    """Phân công cố vấn phụ trách sinh viên.

    Quy tắc nghiệp vụ: MỖI SV CHỈ CÓ 1 CỐ VẤN. 1 cố vấn có thể phụ trách nhiều SV.
    UNIQUE(student_id) đảm bảo điều này ở DB level.
    """
    __tablename__ = "advisor_assignments"

    id = Column(BigInteger, primary_key=True, index=True)
    advisor_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    assigned_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("student_id", name="uq_advisor_assignment_student"),)


class AdvisorNote(Base):
    """Ghi chú tư vấn của cố vấn về sinh viên được phụ trách."""
    __tablename__ = "advisor_notes"

    id = Column(BigInteger, primary_key=True, index=True)
    advisor_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    course_code = Column(String(20), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())


# ── Realtime chat tables ─────────────────────────────────────────────────────

class DirectMessage(Base):
    """Tin nhắn 1-1 giữa hai người dùng (SV ↔ cố vấn)."""
    __tablename__ = "direct_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    receiver_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # Plan A — file attachment (gửi ảnh + tài liệu)
    attachment_filename = Column(Text, nullable=True)
    attachment_path = Column(Text, nullable=True)        # relative under /uploads/messages/
    attachment_type = Column(Text, nullable=True)        # MIME
    attachment_size = Column(BigInteger, nullable=True)  # bytes
    # Category tag để filter/sort
    category = Column(Text, nullable=True)               # course/gpa/roadmap/graduation/scholarship/internship/other
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)
    read_at = Column(DateTime, nullable=True)


class ChatGroup(Base):
    """Nhóm chat (cố vấn tạo cho lớp/nhóm SV)."""
    __tablename__ = "chat_groups"

    id = Column(BigInteger, primary_key=True, index=True)
    name = Column(Text, nullable=False)
    created_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    muted_by = Column(JSON, nullable=False, server_default="[]")  # list user_id đã tắt thông báo


class ChatGroupMember(Base):
    """Thành viên của một nhóm chat."""
    __tablename__ = "chat_group_members"

    group_id = Column(BigInteger, ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    __table_args__ = (PrimaryKeyConstraint("group_id", "user_id"),)


class GroupMessage(Base):
    """Tin nhắn trong nhóm chat."""
    __tablename__ = "group_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    group_id = Column(BigInteger, ForeignKey("chat_groups.id", ondelete="CASCADE"), nullable=False, index=True)
    sender_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)


class UserConnection(Base):
    """Lời mời kết nối / kết bạn giữa hai người dùng."""
    __tablename__ = "user_connections"

    id = Column(BigInteger, primary_key=True, index=True)
    from_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    to_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(Text, nullable=False, server_default="pending")  # pending | accepted | rejected
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("from_id", "to_id", name="uq_user_connection"),)


class PlannedElective(Base):
    """Môn tự chọn mà SV đã plan vào một slot cụ thể trong lộ trình."""
    __tablename__ = "planned_electives"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    term_label = Column(Text, nullable=False)   # VD: "HK1 2025-2026"
    slot_id = Column(Text, nullable=False)      # VD: "B_1", "C_2"
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False)
    updated_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (PrimaryKeyConstraint("user_id", "term_label", "slot_id"),)


# PasswordResetToken model REMOVED 2026-05-05 (Phase 6) — không còn forgot
# password flow. SV quên pw → admin reset thủ công qua /admin/users/{id}/reset-password.


class CourseRating(Base):
    """Đánh giá môn học từ sinh viên đã hoàn thành môn đó.

    Hai kênh feedback song song:
    - rating + review: hiển thị công khai cho SV khác (giúp chọn TC). Có thể ẩn danh (is_anonymous=True).
    - admin_feedback: chỉ admin/khoa thấy — góp ý chất lượng giảng dạy, GV, hàm lượng kiến thức.

    Soft delete (hidden=True): admin moderation — review bị ẩn không hiển thị public
    nhưng vẫn lưu trong DB cho audit / khả năng restore.
    """
    __tablename__ = "course_ratings"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=False)          # 1-5 sao
    review = Column(Text, nullable=True)              # nhận xét công khai (tùy chọn)
    is_anonymous = Column(Boolean, nullable=False, server_default="false")  # ẩn tên trong public reviews
    admin_feedback = Column(Text, nullable=True)      # góp ý riêng cho admin (không công khai)
    # Soft delete: admin có thể ẩn review spam/sai, vẫn giữ data cho audit
    hidden = Column(Boolean, nullable=False, server_default="false", index=True)
    hidden_by = Column(BigInteger, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    hidden_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now(), index=True)

    __table_args__ = (UniqueConstraint("user_id", "course_code", name="uq_course_rating"),)


class ClassGroup(Base):
    """Lớp sinh hoạt — đơn vị tổ chức học vụ truyền thống của đại học VN.

    Mỗi lớp có duy nhất 1 GVCN (NOT NULL). 1 GV có thể chủ nhiệm nhiều lớp.
    SV thuộc 1 lớp → tự động được gán advisor = class_group.advisor_id và derive
    specialization = class_group.specialization (không cần nhập riêng).

    Format mã lớp: DCCTCT{cohort}_{spec_2digit}{letter}, vd 'DCCTCT66_07C'
      • 66       = khoá tuyển (User.cohort)
      • 07       = mã chuyên ngành 2 chữ (suffix của 7480201_07)
      • C        = thứ tự lớp (A, B, C, ...) trong cùng cohort+spec

    ON DELETE RESTRICT trên advisor_id: không cho xoá GV nếu còn chủ nhiệm lớp,
    admin phải chuyển GVCN trước.
    """
    __tablename__ = "class_groups"

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    cohort = Column(String(10), nullable=False, index=True)
    specialization = Column(String(20), nullable=False, index=True)
    advisor_id = Column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class CareerPath(Base):
    """Định hướng nghề nghiệp (Backend, Frontend, Data Scientist, v.v.)."""
    __tablename__ = "career_paths"

    id = Column(BigInteger, primary_key=True, index=True)
    code = Column(String(32), unique=True, nullable=False, index=True)   # e.g. "backend", "data_science"
    name = Column(Text, nullable=False)                                   # "Lập trình Backend"
    short_description = Column(Text, nullable=True)
    long_description = Column(Text, nullable=True)
    icon = Column(String(64), nullable=True)                              # Material icon name
    color = Column(String(32), nullable=True)                             # tailwind color token
    domain_profile = Column(JSON, nullable=True)                          # {"programming":0.9,"database":0.7,...}
    last_blueprint_at = Column(DateTime, nullable=True)                   # lần AI sinh skill blueprint gần nhất
    blueprint_model = Column(Text, nullable=True)                         # provider/model đã dùng (gemini/groq/claude)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class CareerSkill(Base):
    """Kỹ năng / chứng chỉ / khóa học cần cho 1 định hướng nghề.

    Mỗi row = 1 đơn vị học (skill cốt lõi hoặc resource hỗ trợ).
    AI sinh blueprint sẽ tạo nhiều row cho 1 path_id, gom theo skill_group.
    """
    __tablename__ = "career_skills"

    id = Column(BigInteger, primary_key=True, index=True)
    path_id = Column(BigInteger, ForeignKey("career_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_group = Column(Text, nullable=False, server_default="Khác")     # "Lập trình cơ bản" | "Backend Frameworks" | ...
    skill_name = Column(Text, nullable=False)
    skill_type = Column(String(32), nullable=False)                       # "language" | "framework" | "tool" | "certification" | "course" | "soft"
    level = Column(String(16), nullable=True)                             # "basic" | "intermediate" | "advanced"
    priority = Column(Integer, nullable=False, server_default="2")        # 1=must, 2=should, 3=nice-to-have
    school_covered = Column(Boolean, nullable=False, server_default="false")  # TRUE = có môn CTĐT dạy
    school_courses = Column(JSON, nullable=True)                          # ["7080216","7080512"] — list mã môn CTĐT
    source_type = Column(String(32), nullable=True)                       # "course"|"book"|"project"|"practice"|"cert"|"docs"|"video"
    source_name = Column(Text, nullable=True)                             # "Coursera — Meta Backend"
    source_url = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    estimated_hours = Column(Integer, nullable=True)


class CareerCourseMap(Base):
    """Ánh xạ môn học của trường với định hướng nghề nghiệp."""
    __tablename__ = "career_course_mapping"

    path_id = Column(BigInteger, ForeignKey("career_paths.id", ondelete="CASCADE"), primary_key=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), primary_key=True)
    relevance = Column(Numeric(3, 2), nullable=False, server_default="1.0")  # 0.0-1.0


class CareerPathSkill(Base):
    """Liên kết career path ↔ Skill (system Skill chung) — định nghĩa skill cần đạt
    cho 1 career path. Khác với CareerSkill (skill text + tài liệu tự học).

    Dùng để tính skill ownership/gap dựa trên môn SV đã pass.
    """
    __tablename__ = "career_path_skills"

    id = Column(BigInteger, primary_key=True, index=True)
    path_id = Column(BigInteger, ForeignKey("career_paths.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_code = Column(Text, ForeignKey("skills.code", ondelete="CASCADE"), nullable=False, index=True)
    importance = Column(Numeric(3, 2), nullable=False, server_default="1.00")  # 0.5=phụ, 1.0=core
    __table_args__ = (
        UniqueConstraint("path_id", "skill_code", name="uq_career_path_skill_pair"),
    )


class UserCareerChoice(Base):
    """Lựa chọn định hướng nghề của sinh viên (1 primary + 1 secondary)."""
    __tablename__ = "user_career_choice"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    primary_path_id = Column(BigInteger, ForeignKey("career_paths.id", ondelete="SET NULL"), nullable=True)
    secondary_path_id = Column(BigInteger, ForeignKey("career_paths.id", ondelete="SET NULL"), nullable=True)
    chosen_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)


class UserCareerSkillProgress(Base):
    """Theo dõi skill đã học của SV cho định hướng đã chọn."""
    __tablename__ = "user_career_skill_progress"

    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    skill_id = Column(BigInteger, ForeignKey("career_skills.id", ondelete="CASCADE"), primary_key=True)
    status = Column(String(16), nullable=False, server_default="planned")  # "planned" | "in_progress" | "completed" | "skipped"
    scheduled_term = Column(String(20), nullable=True)                     # "HK3/2024-2025" — kỳ SV plan học mục này
    completed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)


# ════════════════════════════════════════════════════════════════════════════
# LUỒNG 1: GRADUATION RISK MANAGEMENT
# Mục đích: phòng ngừa TN trễ hạn — phát hiện sớm SV rủi ro qua ML, tạo case
# để cố vấn xử lý theo workflow (open → in_progress → resolved/escalated).
# ════════════════════════════════════════════════════════════════════════════

# RiskCase model REMOVED 2026-05-05.
# Mô hình tool nội bộ không cần workflow risk tracking — advisor xem trực tiếp
# progress của SV trong lớp; SV tự biết tình trạng học của mình qua progress page.


# ════════════════════════════════════════════════════════════════════════════
# SKILL EVIDENCE & RESOURCES (Evidence-based skill tree)
# Mục đích: thay thế % skill bằng bằng chứng cụ thể (link verifiable + course pass).
# ════════════════════════════════════════════════════════════════════════════

class SkillEvidence(Base):
    """Bằng chứng cá nhân SV tự thêm cho 1 skill — link GitHub / chứng chỉ / project."""
    __tablename__ = "skill_evidence"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_code = Column(String(64), nullable=False, index=True)
    evidence_type = Column(String(32), nullable=False)
    # "github"      — GitHub repo link
    # "certificate" — Coursera/Udemy/etc certificate
    # "project"     — Demo / portfolio project
    # "other"       — Khác
    url = Column(Text, nullable=True)
    label = Column(Text, nullable=False)         # tên hiển thị
    description = Column(Text, nullable=True)    # mô tả ngắn (tuỳ chọn)
    verified = Column(Boolean, nullable=False, default=False, server_default="false")  # admin/GV verify (tương lai)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_skill_evidence_user_skill", "user_id", "skill_code"),
    )


