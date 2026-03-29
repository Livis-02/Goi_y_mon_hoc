from sqlalchemy import Column, Boolean, BigInteger, ForeignKey, DateTime, Text, Numeric
from sqlalchemy.sql import func
from .db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(BigInteger, primary_key=True, index=True)
    username = Column(Text, unique=True, nullable=False)
    password_hash = Column(Text, nullable=False)
    full_name = Column(Text, nullable=True)
    specialization = Column(Text, nullable=True)
    official_earned_credits = Column(Numeric(5, 1), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Course(Base):
    __tablename__ = "courses"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, unique=True, index=True, nullable=False)
    course_name = Column(Text, nullable=False)
    credits = Column(Numeric(4, 1), nullable=True)
    required_specialization = Column(Text, nullable=True)  # NULL = shared; non-null = only required for this specialization
    count_toward_credits = Column(Boolean, nullable=False, server_default="true")  # False for GDTC, military practical, etc.


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


class CourseElectiveGroup(Base):
    """Maps a course to an elective group within a program/specialization."""
    __tablename__ = "course_elective_groups"

    id = Column(BigInteger, primary_key=True, index=True)
    course_code = Column(Text, ForeignKey("courses.course_code", ondelete="CASCADE"), nullable=False, index=True)
    program_code = Column(Text, nullable=False)
    specialization = Column(Text, nullable=False)
    group_type = Column(Text, nullable=False)


class StudyPlan(Base):
    __tablename__ = "study_plans"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(Text, nullable=False)
    target_gpa = Column(Numeric(3, 2), nullable=True)
    max_credits_per_term = Column(Numeric(4, 1), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


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


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(Text, nullable=False)
    intent = Column(Text, nullable=True)
    message = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
