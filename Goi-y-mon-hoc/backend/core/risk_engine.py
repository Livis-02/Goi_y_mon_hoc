"""
risk_engine.py — Graduation Risk Prediction Engine

Mục đích:
  Dự đoán xác suất 1 sinh viên TN trễ hạn (delayed graduation), trả về:
    - risk_score: 0.0 - 1.0
    - predicted_grad_term: kỳ TN dự kiến (VD: "HK1/2027")
    - factors: list các yếu tố rủi ro chính với weight + label

Cách tiếp cận:
  1. Feature engineering từ bảng điểm + tiến độ
  2. Rule-based scoring (luôn chạy, dễ giải thích) — baseline
  3. ML scoring (GradientBoosting) — nếu có model đã train, dùng song song để so sánh

Output combine: risk_score = max(rule_score, ml_score) — chọn cao hơn để safe-side
                Hoặc weighted blend: 0.6 × ml + 0.4 × rule (nếu có ML)

Không chèn weights random/giả — mọi factor đều derivable từ dữ liệu + có công thức rõ.
"""
from __future__ import annotations

import math
import os
import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from sqlalchemy.orm import Session

from backend.db import models
from backend.core import academic_engine as ae


# ── Hằng số ──────────────────────────────────────────────────────────────────
RISK_THRESHOLD_OPEN_CASE = 0.60      # Vượt ngưỡng này → tạo case
RISK_THRESHOLD_HIGH = 0.75            # Mức "nguy cơ rất cao"
RISK_THRESHOLD_MED = 0.40             # Mức "cần chú ý"

STANDARD_PROGRAM_TERMS = 8            # Chương trình chuẩn 8 kỳ chính (không tính HK3)
MAX_PROGRAM_TERMS = 12                # Tối đa 12 kỳ trước khi quá hạn

# Ngưỡng so chuẩn (tính trên main terms HK1+HK2)
EXPECTED_CREDITS_PER_TERM = 19.0      # ~153 TC / 8 kỳ
EXPECTED_TOTAL_CREDITS = 153.0


# ── Feature container ────────────────────────────────────────────────────────
@dataclass
class RiskFeatures:
    """Features sống của 1 SV cho risk prediction."""
    # Tiến độ
    earned_credits: float
    expected_credits: float           # kỳ vọng tại thời điểm này
    credits_pct: float                # earned / 153
    main_terms_studied: int           # số HK1/HK2 đã học (không đếm HK3)
    summer_terms_studied: int

    # Học lực
    gpa4: Optional[float]
    gpa4_recent_2: Optional[float]    # GPA trung bình 2 kỳ gần nhất
    gpa4_trend: Optional[float]       # delta giữa kỳ gần nhất vs trung bình

    # Trượt môn
    failed_count: int                  # số lượt F (đã loại sau học lại OK)
    failed_unrecovered: int            # số môn vẫn trượt chưa qua
    retake_count: int                  # số lần đã học lại

    # Pace
    pace_ratio: float                  # earned / expected (1.0 = đúng tiến độ)

    # Eligibility flags
    on_internship_eligible: bool
    on_thesis_eligible: bool


# ── Feature extraction ───────────────────────────────────────────────────────
def _term_sort_key(term: str) -> tuple:
    """Parse term → (year_start, hk_num). Hỗ trợ 2 format đồng thời:

    - Short: "HK1/2024-2025" → (2024, 1)
    - Long:  "Học kỳ 1 - Năm học 2024-2025" → (2024, 1)
    """
    try:
        if not term:
            return (0, 0)
        import re as _re
        # Tìm số HK (1, 2, 3) sau "HK" hoặc sau "Học kỳ"
        hk_match = _re.search(r"(?:HK|Học kỳ)\s*(\d)", term, _re.IGNORECASE)
        hk_num = int(hk_match.group(1)) if hk_match else 0
        # Tìm năm bắt đầu (2020-2030 range, đầu tiên trong chuỗi)
        year_match = _re.search(r"(20\d{2})", term)
        year_start = int(year_match.group(1)) if year_match else 0
        return (year_start, hk_num)
    except Exception:
        return (0, 0)


def _is_main_term(term: str) -> bool:
    """True nếu là HK1 hoặc HK2 (không phải HK3 — kỳ hè)."""
    if not term:
        return False
    sk = _term_sort_key(term)
    return sk[1] in (1, 2)


def _is_summer_term(term: str) -> bool:
    if not term:
        return False
    return _term_sort_key(term)[1] == 3


def extract_features(db: Session, student_id: int) -> RiskFeatures:
    """Trích features cho 1 SV từ dữ liệu thực."""
    user = db.query(models.User).filter(models.User.id == student_id).first()
    if not user or user.role != "student":
        raise ValueError(f"User {student_id} không phải student")

    snapshot = ae._build_snapshot(db, student_id, user.specialization)

    earned = float(snapshot.earned_credits or 0)
    gpa4 = snapshot.avg_score4

    # Lấy tất cả grades (kể cả trượt) để phân tích trend + failed count
    grades = db.query(models.UserGrade).filter(
        models.UserGrade.user_id == student_id
    ).all()

    # Group theo course_code + semester
    by_term: dict[str, list[models.UserGrade]] = {}
    by_course: dict[str, list[models.UserGrade]] = {}
    for g in grades:
        term = (g.term or "").strip()
        if term:
            by_term.setdefault(term, []).append(g)
        by_course.setdefault(g.course_code, []).append(g)

    # Đếm main terms (HK1, HK2) vs summer (HK3) — robust với cả 2 format
    main_terms = 0
    summer_terms = 0
    for term in by_term:
        if _is_main_term(term):
            main_terms += 1
        elif _is_summer_term(term):
            summer_terms += 1

    # Trượt môn — đếm môn còn trượt (best grade vẫn fail) + tổng số lần học lại
    failed_unrecovered = 0
    retake_count = 0
    for code, gs in by_course.items():
        if len(gs) > 1:
            retake_count += len(gs) - 1
        # Best grade: cao nhất theo score4
        best_score4 = None
        for g in gs:
            s4 = ae._score4_from_grade(g)
            if s4 is not None:
                if best_score4 is None or s4 > best_score4:
                    best_score4 = s4
        if best_score4 is not None and best_score4 < 1.0:
            failed_unrecovered += 1

    # Tổng số lần F (kể cả đã pass sau retake)
    failed_count = sum(
        1 for g in grades
        if (ae._score4_from_grade(g) or 0) < 1.0
    )

    # GPA trend: 2 kỳ gần nhất
    sorted_terms = sorted(
        [(t, gs) for t, gs in by_term.items() if _is_main_term(t)],
        key=lambda x: _term_sort_key(x[0])
    )
    gpa_per_term: list[float] = []
    for _term, gs in sorted_terms:
        weighted = []
        for g in gs:
            course = snapshot.course_by_code.get(g.course_code)
            if not course or not ae._counts_toward_credits(course):
                continue
            s4 = ae._score4_from_grade(g)
            credits = ae._course_credits(course)
            if s4 is not None and credits > 0:
                weighted.append((s4, credits))
        avg = ae._weighted_average(weighted)
        if avg is not None:
            gpa_per_term.append(avg)

    gpa_recent_2 = None
    gpa_trend = None
    if len(gpa_per_term) >= 2:
        gpa_recent_2 = (gpa_per_term[-1] + gpa_per_term[-2]) / 2
        if len(gpa_per_term) >= 3:
            historical_avg = sum(gpa_per_term[:-2]) / max(1, len(gpa_per_term) - 2)
            gpa_trend = gpa_recent_2 - historical_avg
        else:
            gpa_trend = gpa_per_term[-1] - gpa_per_term[-2]

    # Expected credits at this point: bao nhiêu TC SV "lẽ ra" đã có
    expected = main_terms * EXPECTED_CREDITS_PER_TERM
    pace_ratio = (earned / expected) if expected > 0 else 1.0

    # Thresholds
    thresholds = ae._get_academic_thresholds(db)
    return RiskFeatures(
        earned_credits=earned,
        expected_credits=expected,
        credits_pct=earned / EXPECTED_TOTAL_CREDITS if EXPECTED_TOTAL_CREDITS > 0 else 0,
        main_terms_studied=main_terms,
        summer_terms_studied=summer_terms,
        gpa4=gpa4,
        gpa4_recent_2=gpa_recent_2,
        gpa4_trend=gpa_trend,
        failed_count=failed_count,
        failed_unrecovered=failed_unrecovered,
        retake_count=retake_count,
        pace_ratio=pace_ratio,
        on_internship_eligible=earned >= thresholds.get("internship_min_credits", 90.0),
        on_thesis_eligible=(
            earned >= thresholds.get("thesis_min_credits", 130.0)
            and (gpa4 is None or gpa4 >= thresholds.get("thesis_min_gpa4", 2.0))
        ),
    )


# ── Rule-based scoring (luôn dùng được, transparent) ─────────────────────────
def _sigmoid(x: float, k: float = 1.0, x0: float = 0.0) -> float:
    """Sigmoid để smooth-clip score về 0-1."""
    try:
        return 1 / (1 + math.exp(-k * (x - x0)))
    except OverflowError:
        return 0.0 if x < x0 else 1.0


def score_rule_based(f: RiskFeatures) -> tuple[float, list[dict]]:
    """Tính risk score bằng quy tắc — trả về (score, factors_list).

    Mỗi factor có {code, label, contribution: 0-1}. Score tổng = weighted sum.
    """
    factors: list[dict] = []
    contributions: list[tuple[str, str, float, float]] = []  # (code, label, weight, raw_contribution)

    # 1. Pace ratio (TC tích lũy / kỳ vọng): ratio < 0.85 = chậm
    #    Áp dụng từ kỳ thứ 3 trở đi (1-2 kỳ đầu chưa nói lên gì)
    if f.main_terms_studied >= 3:
        pace_score = max(0, min(1, (1.0 - f.pace_ratio) / 0.4))  # 0.6 ratio → 1.0 score
        if pace_score > 0.1:
            label = (
                f"Tốc độ tích lũy chậm — đã {f.main_terms_studied} kỳ chính, "
                f"có {f.earned_credits:.0f}/{f.expected_credits:.0f} TC kỳ vọng "
                f"({f.pace_ratio*100:.0f}%)"
            )
            contributions.append(("slow_credits", label, 0.30, pace_score))

    # 2. GPA hệ 4 thấp
    if f.gpa4 is not None:
        if f.gpa4 < 2.0:
            label = f"GPA hệ 4 ({f.gpa4:.2f}) dưới ngưỡng tốt nghiệp 2.0 — không đủ điều kiện TN"
            contributions.append(("low_gpa", label, 0.30, 1.0))
        elif f.gpa4 < 2.3:
            label = f"GPA hệ 4 ({f.gpa4:.2f}) sát ngưỡng 2.0 — rủi ro nếu kỳ tới sa sút"
            contributions.append(("borderline_gpa", label, 0.20, 0.7))
        elif f.gpa4 < 2.5:
            label = f"GPA hệ 4 ({f.gpa4:.2f}) ở mức TB-thấp"
            contributions.append(("moderate_gpa", label, 0.10, 0.4))

    # 3. GPA trend (2 kỳ gần nhất tụt so với trước)
    if f.gpa4_trend is not None and f.gpa4_trend < -0.2:
        intensity = min(1.0, abs(f.gpa4_trend) / 0.6)
        label = (
            f"GPA tụt {abs(f.gpa4_trend):.2f} điểm trong 2 kỳ gần nhất "
            f"(GPA gần đây: {f.gpa4_recent_2:.2f})"
        )
        contributions.append(("falling_gpa", label, 0.20, intensity))

    # 4. Số môn còn trượt chưa qua
    if f.failed_unrecovered >= 1:
        intensity = min(1.0, f.failed_unrecovered / 5.0)
        label = f"Còn {f.failed_unrecovered} môn chưa pass — cần học lại trước khi xét TN"
        contributions.append(("unrecovered_fails", label, 0.15, intensity))

    # 5. Học lại nhiều lần
    if f.retake_count >= 2:
        intensity = min(1.0, (f.retake_count - 1) / 4.0)
        label = f"Đã học lại {f.retake_count} lượt — pattern dễ kéo dài thời gian học"
        contributions.append(("frequent_retakes", label, 0.10, intensity))

    # 6. Đã học quá nhiều kỳ mà TC còn thấp
    if f.main_terms_studied >= STANDARD_PROGRAM_TERMS and f.credits_pct < 0.95:
        label = (
            f"Đã học {f.main_terms_studied} kỳ chính (chương trình chuẩn 8) "
            f"nhưng mới có {f.credits_pct*100:.0f}% TC"
        )
        contributions.append(("overdue_terms", label, 0.25, 1.0))

    # 7. Quá nhiều kỳ → escalation
    if f.main_terms_studied >= 10:
        label = f"Đã học {f.main_terms_studied} kỳ chính — vượt lộ trình chuẩn 2+ kỳ"
        contributions.append(("severe_overdue", label, 0.30, 1.0))

    # Tổng hợp score: weighted sum của (weight × contribution)
    if not contributions:
        return 0.0, []

    raw_score = sum(w * c for _code, _lbl, w, c in contributions)
    # Squash về 0-1 bằng sigmoid (k=4, x0=0.5 → 0.5 raw ~ 0.5 final)
    final_score = _sigmoid(raw_score, k=4.0, x0=0.5)

    # Build factor list — chỉ giữ top contributions
    contributions.sort(key=lambda x: x[2] * x[3], reverse=True)
    for code, label, w, c in contributions[:5]:
        factors.append({
            "code": code,
            "label": label,
            "contribution": round(w * c, 3),
        })

    return round(final_score, 3), factors


# ── ML scoring (optional, persistent) ────────────────────────────────────────
_ML_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_models" / "risk_model.pkl"
_ml_model_cache = {"model": None, "loaded": False}


def _load_ml_model():
    """Load model từ disk nếu có. Trả về None nếu không."""
    if _ml_model_cache["loaded"]:
        return _ml_model_cache["model"]
    _ml_model_cache["loaded"] = True
    try:
        if _ML_MODEL_PATH.exists():
            with open(_ML_MODEL_PATH, "rb") as fh:
                _ml_model_cache["model"] = pickle.load(fh)
                return _ml_model_cache["model"]
    except Exception as exc:
        print(f"[risk_engine] ML model load failed: {exc}")
    return None


def _features_to_vec(f: RiskFeatures) -> list[float]:
    """Vector hóa features cho ML."""
    return [
        f.earned_credits,
        f.expected_credits,
        f.credits_pct,
        float(f.main_terms_studied),
        float(f.summer_terms_studied),
        f.gpa4 if f.gpa4 is not None else 2.5,
        f.gpa4_recent_2 if f.gpa4_recent_2 is not None else 2.5,
        f.gpa4_trend if f.gpa4_trend is not None else 0.0,
        float(f.failed_count),
        float(f.failed_unrecovered),
        float(f.retake_count),
        f.pace_ratio,
        1.0 if f.on_internship_eligible else 0.0,
        1.0 if f.on_thesis_eligible else 0.0,
    ]


def score_ml(f: RiskFeatures) -> Optional[float]:
    """Trả về xác suất rủi ro từ ML model. None nếu chưa có model."""
    model = _load_ml_model()
    if model is None:
        return None
    try:
        vec = [_features_to_vec(f)]
        proba = model.predict_proba(vec)[0]
        return float(proba[1])  # P(class=1=delayed)
    except Exception as exc:
        print(f"[risk_engine] ML predict failed: {exc}")
        return None


# ── Predicted graduation term ───────────────────────────────────────────────
def _next_main_term(after_term: tuple, k_terms_ahead: int) -> str:
    """Cho (year_start, hk_num), tính kỳ chính kế tiếp k vị trí. HK3 không tính."""
    year, hk = after_term
    if year == 0:
        return ""
    main_seq = []  # đếm theo HK1, HK2 only
    cur_year, cur_hk = year, hk
    for _ in range(20):
        if cur_hk == 1:
            cur_hk = 2
        else:
            cur_hk = 1
            cur_year += 1
        if cur_hk in (1, 2):
            main_seq.append((cur_year, cur_hk))
            if len(main_seq) >= k_terms_ahead:
                break
    if not main_seq:
        return ""
    fy, fhk = main_seq[-1]
    return f"HK{fhk}/{fy}-{fy+1}"


def predict_graduation_term(f: RiskFeatures, latest_term: Optional[str]) -> Optional[str]:
    """Dự đoán kỳ TN dựa trên pace + TC còn thiếu."""
    remaining = max(0, EXPECTED_TOTAL_CREDITS - f.earned_credits)
    if remaining <= 0:
        return "Đã đủ TC"
    # Pace gần đây dự kiến: dùng avg credits/main term (nhưng cap ở 25)
    if f.main_terms_studied > 0:
        avg_per_term = f.earned_credits / f.main_terms_studied
    else:
        avg_per_term = EXPECTED_CREDITS_PER_TERM
    avg_per_term = max(8.0, min(25.0, avg_per_term))  # clamp
    terms_needed = math.ceil(remaining / avg_per_term)

    if not latest_term:
        return None
    sk = _term_sort_key(latest_term)
    if sk == (0, 0):
        return None
    return _next_main_term(sk, terms_needed)


def _latest_term_of(db: Session, student_id: int) -> Optional[str]:
    grades = db.query(models.UserGrade).filter(
        models.UserGrade.user_id == student_id,
        models.UserGrade.term.isnot(None),
    ).all()
    terms = sorted({g.term for g in grades if g.term}, key=_term_sort_key)
    return terms[-1] if terms else None


# ── Public: top-level prediction function ────────────────────────────────────
def predict_risk_for_student(db: Session, student_id: int) -> dict:
    """API chính — trả về dict đầy đủ cho 1 SV."""
    f = extract_features(db, student_id)
    rule_score, factors = score_rule_based(f)
    ml_score = score_ml(f)

    if ml_score is not None:
        # Blend: 0.6 ML + 0.4 rule (ML là model học pattern, rule là guarantee floor)
        final_score = 0.6 * ml_score + 0.4 * rule_score
    else:
        final_score = rule_score

    final_score = max(0.0, min(1.0, final_score))
    latest = _latest_term_of(db, student_id)
    predicted_term = predict_graduation_term(f, latest)

    # On-time check
    on_time = None
    if predicted_term and predicted_term != "Đã đủ TC":
        # Standard: started + 8 main terms = 4 năm
        # Heuristic: nếu predicted year đủ trong khoảng 4-4.5 năm từ bắt đầu thì on_time
        first_term = None
        terms = db.query(models.UserGrade.term).filter(
            models.UserGrade.user_id == student_id,
            models.UserGrade.term.isnot(None),
        ).distinct().all()
        all_terms = sorted({t[0] for t in terms if t[0]}, key=_term_sort_key)
        if all_terms:
            first_term = all_terms[0]
            first_y = _term_sort_key(first_term)[0]
            pred_y = _term_sort_key(predicted_term)[0] if predicted_term else 0
            on_time = (pred_y - first_y) <= 4

    return {
        "student_id": student_id,
        "risk_score": round(final_score, 3),
        "rule_score": rule_score,
        "ml_score": ml_score,
        "predicted_grad_term": predicted_term,
        "on_time": on_time,
        "factors": factors,
        "earned_credits": f.earned_credits,
        "gpa4": f.gpa4,
        "main_terms_studied": f.main_terms_studied,
        "level": (
            "high" if final_score >= RISK_THRESHOLD_HIGH else
            "medium" if final_score >= RISK_THRESHOLD_MED else
            "low"
        ),
    }


def predict_risk_for_all_students(db: Session, advisor_id: Optional[int] = None) -> list[dict]:
    """Predict cho tất cả SV (hoặc nhóm của 1 advisor)."""
    q = db.query(models.User).filter(models.User.role == "student")
    if advisor_id is not None:
        from backend.db.models import AdvisorAssignment  # local import để tránh circular
        student_ids = {a.student_id for a in db.query(AdvisorAssignment).filter(
            AdvisorAssignment.advisor_id == advisor_id
        ).all()}
        q = q.filter(models.User.id.in_(student_ids))
    students = q.all()

    results = []
    for s in students:
        try:
            r = predict_risk_for_student(db, s.id)
            r["full_name"] = s.full_name or s.username
            r["username"] = s.username
            results.append(r)
        except Exception as exc:
            print(f"[risk_engine] failed predict for {s.id}: {exc}")
    results.sort(key=lambda r: r["risk_score"], reverse=True)
    return results


