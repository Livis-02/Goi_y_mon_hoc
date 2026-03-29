from datetime import datetime
from pydantic import BaseModel, field_validator
from typing import Optional, List


class RegisterIn(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None

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

    class Config:
        from_attributes = True


class CourseOut(BaseModel):
    id: int
    course_code: str
    course_name: str
    credits: Optional[float] = None
    count_toward_credits: bool = True

    class Config:
        from_attributes = True


class CourseAdminIn(BaseModel):
    course_code: str
    course_name: str
    credits: Optional[float] = None

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

    class Config:
        from_attributes = True


class UserGradeOut(BaseModel):
    id: int
    user_id: int
    course_code: str
    score10: Optional[float] = None
    score4: Optional[float] = None
    letter: Optional[str] = None
    passed: bool
    term: Optional[str] = None

    class Config:
        from_attributes = True


class GradeUploadIssue(BaseModel):
    course_code_in_file: Optional[str] = None
    course_name_in_file: Optional[str] = None
    reason: str


class GradeUploadOut(BaseModel):
    inserted: int
    skipped_unknown: int
    issues: List[GradeUploadIssue]


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
    completion_percent: float
    avg_score10: Optional[float] = None
    avg_score4: Optional[float] = None
    elective_groups: List[ProgressElectiveGroupOut]
    remaining_course_items: List[ProgressCourseItemOut]
    estimated_terms_remaining: Optional[float] = None
    avg_credits_per_term: Optional[float] = None
    terms_studied: Optional[int] = None
    required_score10_for_target: Optional[float] = None
    target_gpa: Optional[float] = None
    graduation_threshold: float = 150.0
    graduation_ready: bool = False
    internship_eligible: bool = False
    internship_done: bool = False
    thesis_eligible: bool = False
    thesis_done: bool = False
    prereq_issues: List[PrereqIssueOut] = []


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

    class Config:
        from_attributes = True


class RecommendationItemOut(BaseModel):
    course_code: str
    course_name: str
    credits: float
    recommendation_score: float
    fit_probability: float
    reason_codes: List[str]
    reasons: List[str]
    study_direction: str
    category: str = "required"          # required | elective | internship | thesis
    elective_group: Optional[str] = None


class RecommendationOut(BaseModel):
    generated_at: datetime
    total_candidates: int
    avg_score10_baseline: Optional[float] = None
    avg_score4_baseline: Optional[float] = None
    suggested_track: str
    recommendations: List[RecommendationItemOut]
    graduation_ready: bool = False
    internship_eligible: bool = False
    thesis_eligible: bool = False

class ChatIn(BaseModel):
    message: str
    limit: int = 5
    prefer_llm: bool = True

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

    class Config:
        from_attributes = True


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
