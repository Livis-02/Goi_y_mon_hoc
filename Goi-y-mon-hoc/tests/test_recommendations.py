"""Tests cho engine gợi ý môn học — không cần LLM (test rule-based path)."""
from __future__ import annotations

import os
import pytest
from backend.db import models
from backend.core.academic_engine import build_recommendations, build_progress_snapshot


def _seed_curriculum(db):
    """Thêm một số môn học mẫu vào DB test."""
    courses = [
        models.Course(course_code="IT001", course_name="Nhập môn lập trình", credits=4),
        models.Course(course_code="IT002", course_name="Lập trình hướng đối tượng", credits=4),
        models.Course(course_code="IT003", course_name="Cơ sở dữ liệu", credits=3),
        models.Course(course_code="IT004", course_name="Mạng máy tính", credits=3),
        models.Course(course_code="IT005", course_name="Trí tuệ nhân tạo", credits=3),
    ]
    for c in courses:
        existing = db.query(models.Course).filter(models.Course.course_code == c.course_code).first()
        if not existing:
            db.add(c)
    db.commit()


def _seed_user_with_grades(db, username="rec_test_sv"):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        from backend.main import _hash_password
        user = models.User(
            username=username,
            password_hash=_hash_password("Pass@1234"),
            full_name="Test",
            specialization=None,
            career_goal="ai_data",
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    # Đã hoàn thành IT001
    existing = db.query(models.UserGrade).filter(
        models.UserGrade.user_id == user.id,
        models.UserGrade.course_code == "IT001"
    ).first()
    if not existing:
        db.add(models.UserGrade(
            user_id=user.id, course_code="IT001",
            score10=8.0, score4=3.5, letter="B+", passed=True, term="HK1-2023"
        ))
        db.commit()
    return user


def test_recommendations_excludes_completed(db):
    """Môn đã hoàn thành không được xuất hiện trong gợi ý."""
    os.environ.setdefault("GEMINI_API_KEY", "")  # disable LLM
    _seed_curriculum(db)
    user = _seed_user_with_grades(db)
    result = build_recommendations(db, user.id, limit=5)
    codes = [r["course_code"] for r in result["recommendations"]]
    assert "IT001" not in codes, "IT001 đã hoàn thành không được gợi ý lại"


def test_recommendations_returns_list(db):
    """build_recommendations phải trả dict với key 'recommendations' là list."""
    _seed_curriculum(db)
    user = _seed_user_with_grades(db)
    result = build_recommendations(db, user.id, limit=3)
    assert "recommendations" in result
    assert isinstance(result["recommendations"], list)


def test_recommendations_limit_respected(db):
    """Số môn trả về không vượt quá limit."""
    _seed_curriculum(db)
    user = _seed_user_with_grades(db)
    result = build_recommendations(db, user.id, limit=2)
    assert len(result["recommendations"]) <= 2


def test_progress_snapshot(db):
    """build_progress_snapshot trả đúng tín chỉ tích lũy."""
    _seed_curriculum(db)
    user = _seed_user_with_grades(db)
    snap = build_progress_snapshot(db, user.id)
    assert snap["earned_credits"] >= 4.0  # IT001 = 4 TC


def test_recommendation_score_positive(db):
    """Mỗi môn gợi ý phải có recommendation_score > 0."""
    _seed_curriculum(db)
    user = _seed_user_with_grades(db)
    result = build_recommendations(db, user.id, limit=5)
    for item in result["recommendations"]:
        assert item["recommendation_score"] > 0
