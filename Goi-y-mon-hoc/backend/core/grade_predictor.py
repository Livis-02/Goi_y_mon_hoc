"""
grade_predictor.py — Per-course grade prediction with confidence interval.

Mục đích:
  Thay thế heuristic predicted_score đơn giản trong academic_engine bằng 1 module
  có cấu trúc rõ ràng, có ML hook (optional), và trả về:
    - expected_score: điểm 10 dự kiến (4.5 - 9.8)
    - std: độ lệch chuẩn (confidence interval)
    - pass_probability: P(score >= 5) — để cảnh báo môn rủi ro trượt
    - confidence: "high" | "medium" | "low" — tùy độ giàu data

Cách tiếp cận:
  - Rule-based regression: blend 3 signal (prereq_avg, track_gpa, course_difficulty)
  - Sigmoid mapping student-course-fit → pass probability
  - ML hook: nếu có grade_model.pkl thì dùng (chưa train), không thì fallback rule
"""
from __future__ import annotations

import math
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# Hằng số
_MIN_PREDICTED = 4.5
_MAX_PREDICTED = 9.8
_PASS_THRESHOLD_SCORE10 = 5.0


@dataclass
class GradeContext:
    """Input cho prediction — derived từ academic_engine snapshot."""
    student_gpa10: Optional[float] = None        # GPA tích lũy thang 10
    track_gpa10: Optional[float] = None           # GPA của track liên quan
    prereq_avg_score10: Optional[float] = None    # Điểm TB tiên quyết của SV
    course_avg_score10: Optional[float] = None    # Điểm TB toàn trường cho môn
    course_pass_rate: Optional[float] = None      # Tỷ lệ qua môn
    difficulty_factor: float = 0.5                 # 0=dễ, 1=khó
    n_data_points: int = 0                         # số source signal có


@dataclass
class GradePrediction:
    expected_score: float
    std: float                          # uncertainty
    pass_probability: float             # 0-1
    confidence: str                     # "high" | "medium" | "low"
    components: dict                     # breakdown để giải thích


# ── ML model loader ─────────────────────────────────────────────────────────
_ML_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_models" / "grade_model.pkl"
_ml_cache = {"model": None, "loaded": False}


def _load_ml_model():
    if _ml_cache["loaded"]:
        return _ml_cache["model"]
    _ml_cache["loaded"] = True
    try:
        if _ML_MODEL_PATH.exists():
            with open(_ML_MODEL_PATH, "rb") as fh:
                _ml_cache["model"] = pickle.load(fh)
                return _ml_cache["model"]
    except Exception as exc:
        print(f"[grade_predictor] ML load failed: {exc}")
    return None


# ── Rule-based regression ──────────────────────────────────────────────────
def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _sigmoid(x: float) -> float:
    try:
        return 1 / (1 + math.exp(-x))
    except OverflowError:
        return 0.0 if x < 0 else 1.0


def predict_rule_based(ctx: GradeContext) -> GradePrediction:
    """Rule-based prediction. Blend 3 signal theo data có sẵn:

    - Nếu có cả prereq_avg + track_gpa + course_difficulty → high confidence
      base = 0.45*prereq + 0.30*track + 0.25*ease
    - Nếu chỉ có track_gpa + difficulty → medium
      base = 0.65*track + 0.35*ease
    - Nếu thiếu cả track_gpa → low confidence
      base = 0.50*student_gpa + 0.50*ease (giảm spread)
    """
    components = {}
    n_signals = 0

    # Course ease score (10 = dễ, dùng 1 - difficulty)
    course_ease_10 = (1.0 - ctx.difficulty_factor) * 10
    components["course_ease_score10"] = round(course_ease_10, 2)

    # Track GPA fallback chain
    track_gpa = ctx.track_gpa10 if ctx.track_gpa10 is not None else ctx.student_gpa10
    if track_gpa is None:
        track_gpa = 6.5  # fallback trung bình
        confidence = "low"
    else:
        n_signals += 1
        confidence = "medium"
    components["track_gpa10"] = round(track_gpa, 2)

    # Prereq performance signal (mạnh nhất khi có)
    prereq = ctx.prereq_avg_score10
    if prereq is not None:
        n_signals += 1
    components["prereq_avg_score10"] = round(prereq, 2) if prereq is not None else None

    # Difficulty signal
    if ctx.course_pass_rate is not None or ctx.course_avg_score10 is not None:
        n_signals += 1

    # Blend
    if prereq is not None:
        base = prereq * 0.45 + track_gpa * 0.30 + course_ease_10 * 0.25
        confidence = "high" if n_signals >= 3 else "medium"
        std = 0.6 if n_signals >= 3 else 0.85
    else:
        base = track_gpa * 0.65 + course_ease_10 * 0.35
        std = 1.0 if confidence == "medium" else 1.4

    expected = _clamp(base, _MIN_PREDICTED, _MAX_PREDICTED)

    # Pass probability: sigmoid của (expected - 5) / std
    pass_prob = _sigmoid((expected - _PASS_THRESHOLD_SCORE10) / max(std, 0.5))
    # Cap by course pass_rate (nếu có) — không thể >1 nhưng SV cũng không cao hơn rate trung bình quá nhiều
    if ctx.course_pass_rate is not None and ctx.course_pass_rate > 0:
        # Blend pass_prob với pass_rate (60-40 weighting toward pass_prob)
        pass_prob = pass_prob * 0.6 + ctx.course_pass_rate * 0.4

    return GradePrediction(
        expected_score=round(expected, 1),
        std=round(std, 2),
        pass_probability=round(pass_prob, 3),
        confidence=confidence,
        components=components,
    )


def predict_ml(ctx: GradeContext) -> Optional[GradePrediction]:
    """Predict via ML model nếu có. None nếu chưa train."""
    model = _load_ml_model()
    if model is None:
        return None
    try:
        vec = [[
            ctx.student_gpa10 or 6.5,
            ctx.track_gpa10 or ctx.student_gpa10 or 6.5,
            ctx.prereq_avg_score10 or 6.5,
            ctx.course_avg_score10 or 6.5,
            ctx.course_pass_rate or 0.75,
            ctx.difficulty_factor,
        ]]
        # Assume model is GradientBoostingRegressor — predict expected score
        expected = float(model.predict(vec)[0])
        expected = _clamp(expected, _MIN_PREDICTED, _MAX_PREDICTED)
        # Use rule-based for std + pass prob (no quantile model)
        rule = predict_rule_based(ctx)
        pass_prob = _sigmoid((expected - _PASS_THRESHOLD_SCORE10) / max(rule.std, 0.5))
        return GradePrediction(
            expected_score=round(expected, 1),
            std=rule.std,
            pass_probability=round(pass_prob, 3),
            confidence="high",
            components={**rule.components, "model": "ml_regression"},
        )
    except Exception as exc:
        print(f"[grade_predictor] ML predict failed: {exc}")
        return None


def predict(ctx: GradeContext) -> GradePrediction:
    """Public API: ưu tiên ML, fallback rule-based."""
    ml = predict_ml(ctx)
    if ml is not None:
        return ml
    return predict_rule_based(ctx)
