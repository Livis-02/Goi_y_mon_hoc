from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_validator
from typing import Optional, List


class RegisterIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    career_goal: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        text = str(value or "").strip()
        if len(text) < 3:
            raise ValueError("Username must be at least 3 characters")
        return text

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if len(value) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(ch.isupper() for ch in value):
            raise ValueError("Password must include at least 1 uppercase letter")
        if not any(ch.islower() for ch in value):
            raise ValueError("Password must include at least 1 lowercase letter")
        if not any(ch.isdigit() for ch in value):
            raise ValueError("Password must include at least 1 digit")
        return value


class AdminRegisterIn(BaseModel):
    password: str
    full_name: Optional[str] = None
    admin_secret: str


class LoginIn(BaseModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_username(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Username is required")
        return text


class UserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    specialization: Optional[str] = None
    cohort: Optional[str] = None
    managed_specialization: Optional[str] = None
    is_head_of_department: bool = False
    teacher_code: Optional[str] = None
    is_first_login: bool = False
    email: Optional[str] = None
    grades_locked: bool = False  # SV: True = bảng điểm đã admin import, không tự upload đè được

    model_config = ConfigDict(from_attributes=True)


class CourseOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credits: Optional[float] = None
    count_toward_credits: bool = True
    description: Optional[str] = None
    required_specialization: Optional[str] = None
    typical_semester: Optional[int] = None
    specializations: list[str] = []  # Tất cả CN môn này yêu cầu (rỗng = dùng chung)

    model_config = ConfigDict(from_attributes=True)


class CourseAdminIn(BaseModel):
    course_code: str
    course_name: str
    credits: Optional[float] = None
    required_specialization: Optional[str] = None
    count_toward_credits: bool = True
    description: Optional[str] = None
    typical_semester: Optional[int] = None
    # Khi truyền: rỗng = dùng chung; 1 phần tử = single CN; nhiều = M2M
    # Nếu None, không sửa specializations (chỉ dùng required_specialization)
    specializations: Optional[list[str]] = None

    @field_validator("course_code", "course_name")
    @classmethod
    def strip_required(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Field is required")
        return text

    @field_validator("credits")
    @classmethod
    def validate_credits(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if value < 0:
            raise ValueError("Credits must be >= 0")
        return value

    @field_validator("required_specialization")
    @classmethod
    def strip_spec(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = str(value).strip()
        return v or None

    @field_validator("description")
    @classmethod
    def strip_description(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        v = str(value).strip()
        return v or None


class ElectiveGroupRef(BaseModel):
    program_code: str
    specialization: str
    group_type: str


# ── Skills ────────────────────────────────────────────────────────────────────
class SkillIn(BaseModel):
    code: str
    name: str
    category: str
    description: Optional[str] = None

    @field_validator("code")
    @classmethod
    def code_upper(cls, v: str) -> str:
        s = str(v or "").strip().upper()
        if not s:
            raise ValueError("Code is required")
        return s

    @field_validator("name", "category")
    @classmethod
    def strip_req(cls, v: str) -> str:
        s = str(v or "").strip()
        if not s:
            raise ValueError("Field is required")
        return s


class SkillOut(BaseModel):
    id: int
    code: str
    name: str
    category: str
    description: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class CourseSkillIn(BaseModel):
    """Set toàn bộ skill cho 1 môn (replace) — list (skill_code, weight)."""
    skills: list[dict]  # [{skill_code: str, weight: float}]


class CourseSkillOut(BaseModel):
    skill_code: str
    skill_name: str
    category: str
    weight: float


class CourseWithGroupOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credits: Optional[float] = None
    required_specialization: Optional[str] = None
    count_toward_credits: bool = True
    elective_groups: List[ElectiveGroupRef] = []


class CourseBootstrapOut(BaseModel):
    inserted: int
    skipped: int
    total_rows: int


class MessageOut(BaseModel):
    message: str


class ElectiveRuleOut(BaseModel):
    id: int
    program_code: str
    specialization: str
    group_type: str
    min_credits_required: float

    model_config = ConfigDict(from_attributes=True)


class UserGradeOut(BaseModel):
    id: int
    user_id: int
    course_code: str
    course_name: Optional[str] = None
    credits: Optional[float] = None
    score10: Optional[float] = None
    score4: Optional[float] = None
    letter: Optional[str] = None
    passed: bool
    term: Optional[str] = None
    source: Optional[str] = "self"  # 'self' | 'admin' — phân biệt nguồn dữ liệu

    model_config = ConfigDict(from_attributes=True)


class GradeUploadIssue(BaseModel):
    course_code_in_file: Optional[str] = None
    course_name_in_file: Optional[str] = None
    reason: str


class GradeUploadOut(BaseModel):
    inserted: int
    updated: int = 0
    skipped_unknown: int
    issues: List[GradeUploadIssue]
    gpa4_before: float | None = None
    gpa4_after: float | None = None
    credits_before: int = 0
    credits_after: int = 0
    official_tich_luy: float | None = None
    detected_specialization: Optional[str] = None
    spec_auto_set: bool = False
    advisor_assigned: Optional[dict] = None   # {"id": ..., "full_name": ...}
    advisor_warning: Optional[str] = None


class CurriculumImportOut(BaseModel):
    file_path: str
    program_code: str
    total_rows: int
    parsed_courses: int
    inserted_courses: int
    updated_courses: int
    deleted_courses: int
    protected_courses: int
    inserted_rules: int
    updated_rules: int
    assumptions: List[str]


class CtdtPreviewCourse(BaseModel):
    code: str
    name: str
    credits: Optional[float] = None
    elective_group: Optional[str] = None
    specialization: Optional[str] = None


class CtdtPreviewOut(BaseModel):
    valid_count: int = 0
    elective_count: int = 0
    valid_courses: List[CtdtPreviewCourse] = []
    warnings: List[str] = []


class ProgressElectiveGroupOut(BaseModel):
    specialization: Optional[str] = None
    group_type: str
    min_credits_required: float
    earned_credits: float
    remaining_credits: float
    completed: bool


class ProgressCourseItemOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    is_elective: bool = False
    elective_group_type: Optional[str] = None
    required_specialization: Optional[str] = None


class PrereqIssueOut(BaseModel):
    course_code: str
    course_name: str
    missing_prereq_codes: List[str]


class ProgressOut(BaseModel):
    total_courses: int
    completed_courses: int
    remaining_courses: int
    total_credits: float
    earned_credits: float
    official_earned_credits: Optional[float] = None
    completion_percent: float
    avg_score10: Optional[float] = None
    avg_score4: Optional[float] = None
    elective_groups: List[ProgressElectiveGroupOut]
    remaining_course_items: List[ProgressCourseItemOut]
    estimated_terms_remaining: Optional[float] = None
    avg_credits_per_term: Optional[float] = None
    terms_studied: Optional[int] = None
    estimated_graduation: Optional[str] = None
    estimated_graduation_detail: Optional[str] = None
    required_score10_for_target: Optional[float] = None
    target_gpa: Optional[float] = None
    graduation_threshold: float = 153.0
    graduation_ready: bool = False
    internship_eligible: bool = False
    internship_done: bool = False
    thesis_eligible: bool = False
    thesis_done: bool = False
    prereq_issues: List[PrereqIssueOut] = []
    failed_courses: List[dict] = []
    specialization: Optional[str] = None


class CoursePrerequisiteIn(BaseModel):
    course_code: str
    prerequisite_code: str

    @field_validator("course_code", "prerequisite_code")
    @classmethod
    def strip_required(cls, value: str) -> str:
        return str(value or "").strip()


class CoursePrerequisiteOut(BaseModel):
    id: int
    course_code: str
    prerequisite_code: str

    model_config = ConfigDict(from_attributes=True)


class RecommendationItemOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    recommendation_score: float
    fit_probability: float
    reason_codes: List[str]
    reasons: List[str]
    study_direction: str
    category: str = "required"              # required | elective | internship | thesis
    elective_group: Optional[str] = None
    available_this_term: bool = True        # False if not offered in current semester
    ai_ranked: bool = False                 # True if this item was selected/ranked by LLM
    # ── Intelligent scoring metadata ──────────────────────────────────────────
    pass_rate: Optional[float] = None       # Tỷ lệ qua môn toàn trường (0..1)
    avg_score10_course: Optional[float] = None  # Điểm TB toàn trường thang 10
    unlock_count: int = 0                   # Số môn bị mở khóa transitive
    prereq_avg_score: Optional[float] = None    # Điểm TB các môn tiên quyết của SV
    description: Optional[str] = None      # Mô tả môn học
    ml_probability: Optional[float] = None # Xác suất ML dự đoán sinh viên nên học (0..1)
    predicted_score: Optional[float] = None  # Điểm dự đoán sinh viên sẽ đạt (thang 10)
    # Function #6: confidence interval + pass probability cho grade prediction
    predicted_score_std: Optional[float] = None         # Độ lệch chuẩn (uncertainty)
    pass_probability: Optional[float] = None             # P(score >= 5) — 0..1
    prediction_confidence: Optional[str] = None          # "high" | "medium" | "low"


class PlanSuggestionItemOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    prereqs_met: bool = True
    available_this_term: Optional[bool] = None


class RecommendationOut(BaseModel):
    generated_at: datetime
    total_candidates: int
    avg_score10_baseline: Optional[float] = None
    avg_score4_baseline: Optional[float] = None
    suggested_track: str
    suggested_track_key: Optional[str] = None
    track_reasoning: Optional[str] = None
    recommendations: List[RecommendationItemOut]
    ai_ranked: bool = False
    graduation_ready: bool = False
    internship_eligible: bool = False
    thesis_eligible: bool = False
    current_plan_semester: int = 0
    next_plan_semester: int = 1
    plan_direct_suggestions: List[PlanSuggestionItemOut] = []
    specialization: Optional[str] = None
    spec_tracks: dict = {}

class ChatIn(BaseModel):
    message: str
    limit: int = 5
    prefer_llm: bool = True
    thread_id: Optional[str] = None

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Message is required")
        return text


class ChatOut(BaseModel):
    intent: str
    answer: str
    suggestions: List[str]

class ChatHistoryItemOut(BaseModel):
    id: int
    role: str
    intent: Optional[str] = None
    message: str
    created_at: datetime
    thread_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChatThreadOut(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SpecializationIn(BaseModel):
    specialization: str

    @field_validator("specialization")
    @classmethod
    def validate_specialization(cls, value: str) -> str:
        text = str(value or "").strip()
        if not text:
            raise ValueError("Specialization is required")
        return text


class StudyGoalIn(BaseModel):
    target_gpa: Optional[float] = None

    @field_validator("target_gpa")
    @classmethod
    def validate_target_gpa(cls, value: Optional[float]) -> Optional[float]:
        if value is None:
            return value
        if not (0.0 <= value <= 4.0):
            raise ValueError("Target GPA must be between 0.0 and 4.0")
        return value


class StudyGoalOut(BaseModel):
    target_gpa: Optional[float] = None


# ── Grade Preview ──────────────────────────────────────────────────────────────

class GradePreviewItem(BaseModel):
    course_code: str
    course_name_in_file: Optional[str] = None
    course_name_in_db: Optional[str] = None
    credits: Optional[float] = None
    score10: Optional[float] = None
    score4: Optional[float] = None
    letter: Optional[str] = None
    passed: bool
    term: Optional[str] = None
    matched: bool


class GradePreviewOut(BaseModel):
    matched: List[GradePreviewItem]
    unmatched: List[GradeUploadIssue]
    tich_luy: Optional[float] = None
    total_rows_in_file: int
    student_code: Optional[str] = None
    # Extra fields populated when called by admin bulk-import
    account_created: Optional[bool] = None      # True = new account; False = existing
    old_specialization: Optional[str] = None    # current spec in DB (if student exists)
    new_specialization: Optional[str] = None    # detected spec from this file
    specialization_changed: Optional[bool] = None


# ── User Profile ───────────────────────────────────────────────────────────────

class UserProfileIn(BaseModel):
    max_credits_per_term: Optional[float] = None
    career_goal: Optional[str] = None
    target_gpa: Optional[float] = None
    difficulty_preference: Optional[str] = None  # "easy" | "balanced" | "challenging"

    @field_validator("difficulty_preference")
    @classmethod
    def validate_difficulty(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("easy", "balanced", "challenging"):
            raise ValueError("difficulty_preference must be 'easy', 'balanced', or 'challenging'")
        return v

    @field_validator("career_goal")
    @classmethod
    def validate_career_goal(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            v = str(v).strip()
            return v or None
        return None

    @field_validator("max_credits_per_term")
    @classmethod
    def validate_max_credits(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (6.0 <= v <= 30.0):
            raise ValueError("max_credits_per_term must be between 6 and 30")
        return v

    @field_validator("target_gpa")
    @classmethod
    def validate_target_gpa(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and not (0.0 <= v <= 4.0):
            raise ValueError("target_gpa must be between 0.0 and 4.0")
        return v


class UserProfileOut(BaseModel):
    max_credits_per_term: Optional[float] = None
    career_goal: Optional[str] = None
    target_gpa: Optional[float] = None
    difficulty_preference: Optional[str] = None


# ── Semester Offerings ─────────────────────────────────────────────────────────

class SemesterOfferingIn(BaseModel):
    course_code: str
    semester_label: str
    is_open: bool = True

    @field_validator("course_code", "semester_label")
    @classmethod
    def strip_required(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("Field is required")
        return v


class SemesterOfferingOut(BaseModel):
    id: int
    course_code: str
    course_name: Optional[str] = None
    semester_label: str
    is_open: bool

    model_config = ConfigDict(from_attributes=True)


class BulkOfferingIn(BaseModel):
    semester_label: str
    course_codes: List[str]
    is_open: bool = True


class ActiveSemesterIn(BaseModel):
    semester_label: str


class ActiveSemesterOut(BaseModel):
    semester_label: Optional[str] = None
    available_course_codes: List[str] = []


# ── Roadmap ────────────────────────────────────────────────────────────────────

class RoadmapCourseItem(BaseModel):
    course_code: str
    course_name: str
    credits: float
    category: str
    available_this_term: Optional[bool] = None
    elective_group: Optional[str] = None


class SemesterPlanOut(BaseModel):
    semester_number: int
    semester_label: str
    total_credits: float
    courses: List[RoadmapCourseItem]
    is_spec_placeholder: bool = False  # Deprecated: always False — placeholder HK7-9 không còn sinh ra
    is_assigned_by_school: bool = False  # True for HK1-HK2 (năm 1): school assigns, SV cannot drag-drop


class CompletedSemesterCourseOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    score10: Optional[float] = None
    passed: bool


class CompletedSemesterOut(BaseModel):
    semester_label: str
    total_credits: float
    gpa4: Optional[float] = None
    gpa10: Optional[float] = None
    courses: List[CompletedSemesterCourseOut]


class RoadmapOverdueCourseOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    plan_semester: int
    prereqs_met: bool = True


class RoadmapOut(BaseModel):
    completed_semesters: List[CompletedSemesterOut] = []
    semesters: List[SemesterPlanOut]
    total_remaining_credits: float
    estimated_terms: int
    max_credits_per_term: float
    track_elective_suggestions: dict = {}
    spec_tracks: dict = {}
    prereq_map: dict = {}
    internship_code: Optional[str] = None
    thesis_code: Optional[str] = None
    current_plan_semester: int = 0
    next_plan_semester: int = 1
    plan_direct_suggestions: List[PlanSuggestionItemOut] = []
    overdue_courses: List[RoadmapOverdueCourseOut] = []
    specialization: Optional[str] = None
    actual_user_spec: Optional[str] = None  # CN thực của user (None nếu chưa chốt)
    explore_spec: Optional[str] = None  # CN đang explore (chỉ set khi khác actual)
    spec_pending: bool = False  # True when SV chưa chọn CN → frontend hiện CTA "Khám phá 6 CN"


# ── Analytics ─────────────────────────────────────────────────────────────────

class GpaByTermItem(BaseModel):
    term: str
    gpa4: float
    gpa10: float
    credits_earned: float


class SubjectGroupItem(BaseModel):
    group_name: str
    avg_score10: float
    course_count: int


class WeakCourseItem(BaseModel):
    course_code: str
    course_name: str
    score10: Optional[float] = None
    credits: float
    passed: bool


class AnalyticsOut(BaseModel):
    gpa_by_term: List[GpaByTermItem]
    subject_group_performance: List[SubjectGroupItem]
    weak_courses: List[WeakCourseItem]
    failed_courses: List[WeakCourseItem]
    gpa_trend_direction: str   # "improving" | "declining" | "stable" | "insufficient_data"
    study_pace: str            # "ahead" | "on_track" | "behind" | "unknown"
    recommended_credits_next_term: float
    credits_remaining: Optional[float] = None
    credits_total: Optional[float] = None
    credits_progress_pct: Optional[float] = None
    terms_remaining: Optional[int] = None
    estimated_graduation_term: Optional[str] = None


# ── Course Registration ────────────────────────────────────────────────────────

class RegistrationItemIn(BaseModel):
    course_code: str
    was_recommended: bool = False
    recommendation_score: Optional[float] = None


class CourseRegistrationIn(BaseModel):
    semester_label: str
    courses: List[RegistrationItemIn]

    @field_validator("semester_label")
    @classmethod
    def strip_semester(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("semester_label is required")
        return v


class CourseRegistrationOut(BaseModel):
    id: int
    user_id: int
    course_code: str
    semester_label: str
    was_recommended: bool
    recommendation_score_at_time: Optional[float] = None
    outcome: Optional[str] = None
    registered_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Admin User Management ──────────────────────────────────────────────────────

class AdminUserItem(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    specialization: Optional[str] = None
    career_goal: Optional[str] = None
    official_earned_credits: Optional[float] = None
    grade_count: int = 0
    avg_score4: Optional[float] = None
    default_password: Optional[str] = None
    # Khoá bảng điểm (admin có thể toggle)
    grades_locked: bool = False
    # SV quá hạn: span năm học từ term điểm > 5 năm + TC < threshold tốt nghiệp
    is_overdue: bool = False
    # Advisor assignment (for student rows only)
    advisor_id: Optional[int] = None
    advisor_teacher_code: Optional[str] = None
    advisor_full_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminUserListOut(BaseModel):
    total: int
    users: List[AdminUserItem]


class AdminDefaultPasswordOut(BaseModel):
    has_default: bool
    password: Optional[str] = None


class AdminResetPasswordOut(BaseModel):
    message: str
    password: str


class AdminSetRoleIn(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in {"student", "advisor", "admin"}:
            raise ValueError("role must be 'student', 'advisor', or 'admin'")
        return v


class UpdateFullNameIn(BaseModel):
    full_name: str

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("Tên hiển thị không được để trống")
        return v


class GoogleAuthIn(BaseModel):
    credential: str  # Google ID token from GSI

    @field_validator("credential")
    @classmethod
    def validate_credential(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("Google credential is required")
        return v


class SetupAccountIn(BaseModel):
    email: str
    new_password: str
    confirm_password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email không hợp lệ")
        return v

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải ít nhất 8 ký tự")
        if not any(c.isupper() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ hoa")
        if not any(c.islower() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ thường")
        if not any(c.isdigit() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ số")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return v


class ForgotPasswordIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Email không hợp lệ")
        return v


class ResetPasswordIn(BaseModel):
    token: str
    new_password: str
    confirm_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải ít nhất 8 ký tự")
        if not any(c.isupper() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ hoa")
        if not any(c.islower() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ thường")
        if not any(c.isdigit() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ số")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v: str, info) -> str:
        if "new_password" in info.data and v != info.data["new_password"]:
            raise ValueError("Mật khẩu xác nhận không khớp")
        return v


class ChangePasswordIn(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Mật khẩu phải ít nhất 8 ký tự")
        if not any(c.isupper() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ hoa")
        if not any(c.islower() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ thường")
        if not any(c.isdigit() for c in v):
            raise ValueError("Phải có ít nhất 1 chữ số")
        return v


# ── Admin Audit Log ───────────────────────────────────────────────────────────

class AdminLogOut(BaseModel):
    id: int
    admin_username: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    detail: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Schedule ──────────────────────────────────────────────────────────────────

class ScheduleEntryIn(BaseModel):
    course_code: Optional[str] = None
    course_name: str
    day_of_week: str        # "2"–"7"
    start_time: str         # "HH:MM"
    end_time: str           # "HH:MM"
    start_date: Optional[str] = None   # "YYYY-MM-DD"
    end_date: Optional[str] = None     # "YYYY-MM-DD"
    room: Optional[str] = None
    color: str = "#3b82f6"

    @field_validator("course_name")
    @classmethod
    def check_name(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("course_name is required")
        return v


class ScheduleEntryOut(BaseModel):
    id: int
    course_code: Optional[str] = None
    course_name: str
    day_of_week: str
    start_time: str
    end_time: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    room: Optional[str] = None
    color: str

    model_config = ConfigDict(from_attributes=True)


class ScheduleConflictOut(BaseModel):
    entry_a: ScheduleEntryOut
    entry_b: ScheduleEntryOut
    day_of_week: str


# ── System Notifications ──────────────────────────────────────────────────────

VALID_TARGET_TYPES = {"all", "all_students", "all_advisors", "cohort",
                      "specialization", "students", "advisors", "department"}
VALID_SEVERITIES = {"info", "warning", "urgent"}

class SystemNotificationIn(BaseModel):
    title: str
    body: str
    type: str = "info"   # legacy — kept for old admin frontend


class SystemNotificationOut(BaseModel):
    id: int
    title: str
    body: str
    type: str
    admin_username: Optional[str] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationCreateIn(BaseModel):
    title: str
    content: str
    severity: str = "info"
    target_type: str = "all"
    target_value: Optional[str] = None


class NotificationListItem(BaseModel):
    id: int
    title: str
    body: str
    severity: str
    target_type: Optional[str] = "all"
    target_value: Optional[str] = None
    admin_username: Optional[str] = None
    is_active: bool
    created_at: datetime
    read_count: int = 0
    total_reach: int = 0

    model_config = ConfigDict(from_attributes=True)


class NotificationUserItem(BaseModel):
    id: int
    title: str
    body: str
    severity: str
    created_at: datetime
    is_read: bool

    model_config = ConfigDict(from_attributes=True)


class UnreadCountOut(BaseModel):
    count: int


class EstimateReachOut(BaseModel):
    count: int


# ── User Messages (Admin → Student personal messages) ─────────────────────────

class UserMessageIn(BaseModel):
    title: str
    body: str
    type: str = "info"   # "info" | "warning" | "success" | "danger"


class UserMessageOut(BaseModel):
    id: int
    sender_username: Optional[str] = None
    recipient_id: Optional[int] = None
    title: str
    body: str
    type: str
    is_read: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ── Advisor ───────────────────────────────────────────────────────────────────

class AdvisorNoteIn(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def check_content(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("Nội dung ghi chú không được để trống")
        return v


class AdvisorNoteCreateIn(BaseModel):
    student_id: int
    content: str
    course_code: Optional[str] = None

    @field_validator("content")
    @classmethod
    def check_content(cls, v: str) -> str:
        v = str(v or "").strip()
        if not v:
            raise ValueError("Nội dung ghi chú không được để trống")
        return v


class AdvisorNoteOut(BaseModel):
    id: int
    advisor_id: int
    student_id: int
    content: str
    course_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdvisorAssignmentOut(BaseModel):
    id: int
    advisor_id: int
    student_id: int
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdvisorStudentItem(BaseModel):
    """Tóm tắt thông tin sinh viên trong danh sách của cố vấn."""
    id: int
    username: str
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    cohort: Optional[str] = None
    earned_credits: Optional[float] = None
    avg_score4: Optional[float] = None
    status: str = "normal"          # "high_risk" | "needs_attention" | "normal"
    status_reason: Optional[str] = None
    flags: list[dict] = []          # extra warning badges: [{code,label,severity}]
    has_admin_grades: bool = False  # True nếu phòng đào tạo đã import điểm chính thức
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdvisorStatsOut(BaseModel):
    """Thống kê tổng quan nhóm sinh viên của cố vấn."""
    total_students: int
    high_risk_count: int            # GPA < 2.0 hoặc dự kiến trễ > 2 HK
    needs_attention_count: int      # GPA 2.0–2.5 hoặc trễ 1–2 HK
    normal_count: int
    avg_gpa4: Optional[float] = None
    avg_completion_percent: Optional[float] = None


# ── Admin Advisor management ─────────────────────────────────────────────────

class AdminAdvisorItem(BaseModel):
    id: int
    username: str
    teacher_code: Optional[str] = None
    full_name: Optional[str] = None
    managed_specialization: Optional[str] = None
    is_head_of_department: bool = False
    student_count: int = 0
    default_password: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AdminCreateAdvisorIn(BaseModel):
    teacher_code: str          # Mã GV (VD: KHMT001, GV001) — cũng là username đăng nhập
    full_name: str
    managed_specialization: Optional[str] = None

    @field_validator("teacher_code")
    @classmethod
    def check_teacher_code(cls, v: str) -> str:
        import re as _re
        v = v.strip().upper()
        if not _re.match(r'^(KHMT|MMT|CNPM|HTTT|THKT|CNTTDH|GV)\d{3}$', v):
            raise ValueError(
                "Mã GV không hợp lệ. Format: PREFIX + 3 chữ số (VD: KHMT001, MMT001, GV001)"
            )
        return v

    @field_validator("full_name")
    @classmethod
    def check_full_name(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Họ và tên không được để trống")
        return v


class AdminUpdateAdvisorIn(BaseModel):
    full_name: Optional[str] = None
    managed_specialization: Optional[str] = None
    is_head_of_department: Optional[bool] = None


class TransferHeadIn(BaseModel):
    new_head_advisor_id: int


class AdminCreateAdvisorOut(BaseModel):
    id: int
    username: str
    teacher_code: Optional[str] = None
    full_name: Optional[str] = None
    managed_specialization: Optional[str] = None
    is_head_of_department: bool = False
    role: str
    password_plain: str  # mật khẩu tạm cần đổi khi đăng nhập lần đầu


class AdminAdvisorStudentItem(BaseModel):
    assignment_id: int
    student_id: int
    username: str
    full_name: Optional[str] = None
    assigned_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminAssignStudentIn(BaseModel):
    student_id: int


# ── Admin dashboard & config ──────────────────────────────────────────────────

class AdminDashboardOut(BaseModel):
    total_students: int
    total_advisors: int
    total_courses: int
    at_risk_students: int        # GPA < 2.0 HOẶC dự kiến trễ TN
    active_users_this_week: int  # số SV có upload điểm trong 7 ngày qua
    graduation_threshold: float
    students_no_grades: int = 0        # SV chưa có bảng điểm
    students_first_login: int = 0      # SV chưa đăng nhập lần đầu
    cohort_distribution: dict = {}     # {"10": 5, "11": 8, ...}
    spec_distribution: dict = {}       # {"KHMT": 12, "CNPM": 9, ...}


class AdminDashboardStatsOut(BaseModel):
    """Extended dashboard stats — 8 stat cards + Chart.js arrays + structured warnings."""
    # ── 8 stat cards
    total_students: int = 0
    total_advisors: int = 0
    total_courses: int = 0
    at_risk_students: int = 0         # avg GPA < 2.0
    thesis_eligible: int = 0          # official_earned_credits >= threshold - 10 (đủ ĐK làm ĐATN)
    students_no_grades: int = 0
    students_no_advisor: int = 0      # students without any advisor assignment
    not_thesis_eligible: int = 0      # chưa đủ ĐK làm ĐATN
    # ── Extra context (footer bar)
    students_first_login: int = 0
    active_users_this_week: int = 0
    graduation_threshold: float = 153.0
    notifications_total: int = 0
    notifications_avg_read_rate: float = 0.0
    # ── Chart.js arrays (pre-sorted)
    cohort_labels: list = []
    cohort_values: list = []
    spec_labels: list = []
    spec_values: list = []
    # ── Structured warnings
    warnings: list = []


class GraduationThresholdIn(BaseModel):
    threshold: float

    @field_validator("threshold")
    @classmethod
    def check_threshold(cls, v: float) -> float:
        if v < 60 or v > 300:
            raise ValueError("Ngưỡng tín chỉ tốt nghiệp phải nằm trong khoảng 60–300")
        return round(v, 1)


class GraduationThresholdOut(BaseModel):
    threshold: float
    source: str   # "db" | "default"


class AcademicThresholdsIn(BaseModel):
    """Ngưỡng học vụ — chỉnh được từ tab Nhật ký."""
    internship_min_credits: float       # TC tối thiểu để đi thực tập DN
    thesis_min_credits: float           # TC tối thiểu để làm ĐATN
    thesis_min_gpa4: float              # GPA hệ 4 tối thiểu để làm ĐATN

    @field_validator("internship_min_credits", "thesis_min_credits")
    @classmethod
    def check_credits(cls, v: float) -> float:
        if v < 30 or v > 250:
            raise ValueError("Ngưỡng TC phải trong khoảng 30–250")
        return round(v, 1)

    @field_validator("thesis_min_gpa4")
    @classmethod
    def check_gpa(cls, v: float) -> float:
        if v < 0 or v > 4:
            raise ValueError("GPA hệ 4 phải trong khoảng 0–4")
        return round(v, 2)


class AcademicThresholdsOut(BaseModel):
    internship_min_credits: float
    thesis_min_credits: float
    thesis_min_gpa4: float
    source: str   # "db" | "default" | "mixed"


# ── Admin bulk import ──────────────────────────────────────────────────────────

class UserImportError(BaseModel):
    row: int
    username: Optional[str] = None
    reason: str


class AdminUsersImportOut(BaseModel):
    created_count: int
    skipped_count: int
    errors: List[UserImportError] = []
    generated_passwords: dict = {}   # username → plain-text password (chỉ khi auto-gen)


class AdvisorImportError(BaseModel):
    row: int
    teacher_code: Optional[str] = None
    reason: str


class AdminAdvisorsImportOut(BaseModel):
    created_count: int
    skipped_count: int
    errors: List[AdvisorImportError] = []
    generated_passwords: dict = {}   # teacher_code → plain-text password


class AdminAdvisorBulkAssignIn(BaseModel):
    student_usernames: List[str]


class AdminAdvisorBulkAssignOut(BaseModel):
    assigned_count: int
    skipped_count: int
    errors: List[str] = []


class AdminCreateUserIn(BaseModel):
    username: str
    full_name: Optional[str] = None
    role: Optional[str] = "student"


class AdminUpdateUserIn(BaseModel):
    """Partial update — chỉ field được gửi mới update. None = không đụng tới."""
    full_name: Optional[str] = None
    cohort: Optional[str] = None
    specialization: Optional[str] = None  # gửi "" để clear (chưa CN)
    email: Optional[str] = None


class AdminCreateUserOut(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    role: str
    password_plain: Optional[str] = None  # chỉ trả về khi hệ thống tự sinh


class GradesImportError(BaseModel):
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    reason: str


class AdminGradesImportOut(BaseModel):
    student_code: str
    account_created: bool
    password_plain: Optional[str] = None
    grades_imported: int
    advisor_assigned: Optional[dict] = None   # {"id": ..., "full_name": ...}
    advisor_warning: Optional[str] = None
    specialization_changed: bool = False
    new_specialization: Optional[str] = None


# ── Advisor: department management (head reassigns advisors) ─────────────────

class DeptStudentItem(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    specialization: Optional[str] = None
    earned_credits: Optional[float] = None
    avg_score4: Optional[float] = None
    current_advisor_id: Optional[int] = None
    current_advisor_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class DeptAdvisorItem(BaseModel):
    id: int
    username: str
    full_name: Optional[str] = None
    is_head_of_department: bool = False
    student_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ReassignAdvisorIn(BaseModel):
    new_advisor_id: int


# ── Admin bulk-import assignments ─────────────────────────────────────────────

class NewTeacherInfo(BaseModel):
    """Thông tin GV mới cần tạo khi import phân công."""
    teacher_code: str
    full_name: str
    managed_specialization: Optional[str] = None
    is_head_of_department: bool = False

    @field_validator("teacher_code")
    @classmethod
    def check_tc(cls, v: str) -> str:
        import re as _re
        v = v.strip().upper()
        if not _re.match(r'^(KHMT|MMT|CNPM|HTTT|THKT|CNTTDH|GV)\d{3}$', v):
            raise ValueError(f"Mã GV không hợp lệ: {v}. Format: PREFIX + 3 chữ số (VD: KHMT001, GV001)")
        return v

    @field_validator("full_name")
    @classmethod
    def check_fn(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Họ tên không được để trống")
        return v


class AssignmentImportError(BaseModel):
    row: int
    student_code: Optional[str] = None
    teacher_code: Optional[str] = None
    reason: str


class MissingTeacherInfo(BaseModel):
    teacher_code: str
    student_count: int
    affected_students: List[str]


class CreatedTeacherInfo(BaseModel):
    teacher_code: str
    full_name: str
    password_plain: str


class AssignmentBulkImportOut(BaseModel):
    total: int
    created: int      # assignment mới
    updated: int      # assignment đổi cố vấn
    skipped: int
    missing_teachers: List[MissingTeacherInfo] = []
    created_teachers: List[CreatedTeacherInfo] = []
    errors: List[AssignmentImportError] = []


# ════════════════════════════════════════════════════════════════════════════
# V2 — Lộ trình tích hợp (career blueprint)
# ════════════════════════════════════════════════════════════════════════════

class CareerPathOut(BaseModel):
    """Một nghề mục tiêu trong picker."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    short_description: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None
    has_blueprint: bool = False
    last_blueprint_at: Optional[datetime] = None


class BlueprintSkillOut(BaseModel):
    """Một mục skill/resource trong blueprint."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    skill_group: str
    skill_name: str
    skill_type: str
    level: Optional[str] = None
    priority: int
    school_covered: bool
    school_courses: Optional[List[str]] = None
    source_type: Optional[str] = None
    source_name: Optional[str] = None
    source_url: Optional[str] = None
    description: Optional[str] = None
    estimated_hours: Optional[int] = None
    # Trạng thái tiến độ của SV với mục này (gắn từ user_career_skill_progress)
    status: str = "planned"           # planned | in_progress | completed | skipped
    scheduled_term: Optional[str] = None


class BlueprintGroupOut(BaseModel):
    """1 nhóm skill (Lập trình cơ bản, Backend Frameworks...)."""
    group_name: str
    total: int
    completed: int
    in_progress: int
    skills: List[BlueprintSkillOut] = []


class BlueprintMeOut(BaseModel):
    """Toàn bộ blueprint cho nghề SV đã chọn."""
    path: CareerPathOut
    fit_percent: int                  # 0-100 — tỉ lệ skill đã đạt
    total_skills: int
    completed_skills: int
    in_progress_skills: int
    estimated_external_hours: int     # tổng giờ học ngoài còn lại
    groups: List[BlueprintGroupOut] = []


class BlueprintRegenerateIn(BaseModel):
    """Trigger AI sinh lại blueprint cho 1 nghề (admin/owner only)."""
    path_id: int
    force: bool = False               # True = sinh lại dù đã có blueprint


class BlueprintSkillStatusIn(BaseModel):
    status: str                       # planned | in_progress | completed | skipped
    note: Optional[str] = None


class BlueprintSkillScheduleIn(BaseModel):
    scheduled_term: Optional[str] = None   # "HK3/2024-2025" hoặc null để bỏ lịch


class CareerChoiceIn(BaseModel):
    primary_path_id: int
    secondary_path_id: Optional[int] = None


class IntegratedTermItem(BaseModel):
    """1 dòng trong lộ trình tích hợp — môn trường HOẶC mục ngoài."""
    kind: str                          # "school" | "external"
    title: str
    subtitle: Optional[str] = None
    status: str                        # passed/current/locked/upcoming (school) | planned/doing/done/skipped (external)
    # School-only
    course_code: Optional[str] = None
    credits: Optional[float] = None
    grade_letter: Optional[str] = None
    score10: Optional[float] = None
    # External-only
    skill_id: Optional[int] = None
    skill_group: Optional[str] = None
    estimated_hours: Optional[int] = None
    source_url: Optional[str] = None
    source_type: Optional[str] = None


class IntegratedTermOut(BaseModel):
    term_label: str                    # "HK1/2024-2025"
    semester_index: int                # 1..9
    school_credits: float
    external_hours: int
    school_items: List[IntegratedTermItem] = []
    external_items: List[IntegratedTermItem] = []


class IntegratedRoadmapOut(BaseModel):
    path: Optional[CareerPathOut] = None    # null nếu SV chưa chọn nghề
    fit_percent: int = 0
    terms: List[IntegratedTermOut] = []
    dry_run: bool = False
