from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
import unicodedata

from sqlalchemy.orm import Session

from backend import models

TRACKS = {
    "data_ai": {
        "label": "Dữ liệu / AI",
        "keywords": ["du lieu", "tri tue nhan tao", "hoc may", "khai pha", "co so du lieu", "thi giac may tinh", "thong ke"],
    },
    "software": {
        "label": "Phát triển phần mềm",
        "keywords": ["lap trinh", "web", "he thong", "doi tuong", "java", "c++", "ma nguon mo", "thuong mai dien tu"],
    },
    "network_security_iot": {
        "label": "Mạng / An ninh / IoT",
        "keywords": ["mang", "an ninh", "iot", "dam may", "ha tang", "kien truc"],
    },
}


@dataclass
class StudentSnapshot:
    courses: list[models.Course]
    course_by_code: dict[str, models.Course]
    best_grades: dict[str, models.UserGrade]
    completed_codes: set[str]
    avg_score10: float | None
    avg_score4: float | None
    total_credits: float
    earned_credits: float


def _normalize_text(value) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text.replace("\u0111", "d").replace("\u0110", "d"))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _to_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _course_credits(course: models.Course) -> float:
    credits = _to_float(course.credits)
    return round(credits, 1) if credits is not None else 0.0


def _score10_from_grade(grade: models.UserGrade) -> float | None:
    score10 = _to_float(grade.score10)
    if score10 is not None:
        return score10
    score4 = _to_float(grade.score4)
    if score4 is not None:
        return max(0.0, min(10.0, score4 * 2.5))
    return None


def _score4_from_grade(grade: models.UserGrade) -> float | None:
    score4 = _to_float(grade.score4)
    if score4 is not None:
        return score4
    score10 = _to_float(grade.score10)
    if score10 is None:
        return None
    if score10 >= 9.0:
        return 4.0
    if score10 >= 8.5:
        return 3.7
    if score10 >= 8.0:
        return 3.5
    if score10 >= 7.0:
        return 3.0
    if score10 >= 6.5:
        return 2.5
    if score10 >= 5.5:
        return 2.0
    if score10 >= 5.0:
        return 1.5
    if score10 >= 4.0:
        return 1.0
    return 0.0


def _select_best_grade_per_course(grades: list[models.UserGrade]) -> dict[str, models.UserGrade]:
    by_code: dict[str, models.UserGrade] = {}
    for grade in grades:
        existing = by_code.get(grade.course_code)
        if not existing:
            by_code[grade.course_code] = grade
            continue

        rank_new = (1 if grade.passed else 0, _score10_from_grade(grade) or -1.0, _score4_from_grade(grade) or -1.0)
        rank_old = (1 if existing.passed else 0, _score10_from_grade(existing) or -1.0, _score4_from_grade(existing) or -1.0)
        if rank_new > rank_old:
            by_code[grade.course_code] = grade
    return by_code


def _weighted_average(values: list[tuple[float, float]]) -> float | None:
    if not values:
        return None
    numerator = sum(v * w for v, w in values)
    denominator = sum(w for _, w in values)
    if denominator <= 0:
        return None
    return numerator / denominator


def _counts_toward_credits(course: models.Course) -> bool:
    """Return False for courses excluded from the official credit count (GDTC, military practical, etc.)."""
    flag = getattr(course, "count_toward_credits", None)
    # If the column exists and is explicitly False, exclude the course
    if flag is False or flag == 0:
        return False
    return True


def _calc_credits(
    db: Session,
    course_by_code: dict,
    completed_codes: set,
    specialization: str | None,
) -> tuple[float, float]:
    """Calculate (total, earned) credits, capping elective groups at min_credits_required.
    Courses with count_toward_credits=False are excluded from both totals."""
    rules = []
    group_mappings = []
    if specialization:
        from sqlalchemy import or_
        rules = db.query(models.ElectiveRule).filter(
            or_(
                models.ElectiveRule.specialization == specialization,
                models.ElectiveRule.specialization == "Chung",
            )
        ).all()
        group_mappings = db.query(models.CourseElectiveGroup).filter(
            or_(
                models.CourseElectiveGroup.specialization == specialization,
                models.CourseElectiveGroup.specialization == "Chung",
            )
        ).all()

    if not rules or not group_mappings:
        total = round(sum(_course_credits(c) for c in course_by_code.values() if _counts_toward_credits(c)), 1)
        earned = round(sum(
            _course_credits(course_by_code[c])
            for c in completed_codes
            if c in course_by_code and _counts_toward_credits(course_by_code[c])
        ), 1)
        return total, earned

    elective_codes: set[str] = {m.course_code for m in group_mappings}
    group_courses: dict[tuple, set] = defaultdict(set)
    for m in group_mappings:
        group_courses[(m.program_code, m.specialization, m.group_type)].add(m.course_code)

    total = sum(
        _course_credits(c) for code, c in course_by_code.items()
        if code not in elective_codes and _counts_toward_credits(c)
    )
    earned = sum(
        _course_credits(course_by_code[c])
        for c in completed_codes
        if c in course_by_code and c not in elective_codes and _counts_toward_credits(course_by_code[c])
    )

    for rule in rules:
        min_req = _to_float(rule.min_credits_required) or 0.0
        key = (rule.program_code, rule.specialization, rule.group_type)
        earned_in_group = sum(
            _course_credits(course_by_code[code])
            for code in group_courses.get(key, set())
            if code in completed_codes and code in course_by_code
        )
        total += min_req
        earned += min(earned_in_group, min_req)

    return round(total, 1), round(earned, 1)


GRADUATION_CREDIT_THRESHOLD = 150.0
INTERNSHIP_REMAINING_BUFFER = 6.0  # non-special credits allowed to remain when starting internship


def _find_internship_thesis(
    courses: list[models.Course],
    specialization: str | None,
) -> tuple[models.Course | None, models.Course | None]:
    """Return (internship_course, thesis_course) for the user's specialisation."""
    if not specialization:
        return None, None
    internship = None
    thesis = None
    for c in courses:
        if c.required_specialization != specialization:
            continue
        n = _normalize_text(c.course_name)
        if "thuc tap" in n and "tot nghiep" in n:
            internship = c
        elif "do an" in n and "tot nghiep" in n:
            thesis = c
    return internship, thesis


def _build_snapshot(db: Session, user_id: int, specialization: str | None = None) -> StudentSnapshot:
    from sqlalchemy import or_
    all_courses = db.query(models.Course).order_by(models.Course.course_code.asc()).all()
    if specialization:
        # Courses in the user's elective pools (their spec + "Chung")
        user_elective_codes: set[str] = {
            m.course_code for m in db.query(models.CourseElectiveGroup).filter(
                or_(
                    models.CourseElectiveGroup.specialization == specialization,
                    models.CourseElectiveGroup.specialization == "Chung",
                )
            ).all()
        }
        # Courses that exist in OTHER specializations' elective pools but NOT in user's
        other_elective_codes: set[str] = {
            m.course_code for m in db.query(models.CourseElectiveGroup).filter(
                models.CourseElectiveGroup.specialization != specialization,
                models.CourseElectiveGroup.specialization != "Chung",
            ).all()
        } - user_elective_codes

        courses = [
            c for c in all_courses
            if (
                # Required for user's spec, or shared and not exclusively another spec's elective
                (c.required_specialization is None and c.course_code not in other_elective_codes)
                or c.required_specialization == specialization
            )
        ]
    else:
        courses = all_courses
    course_by_code = {c.course_code: c for c in courses}

    grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()
    best_grades = _select_best_grade_per_course(grades)
    completed_codes = {code for code, g in best_grades.items() if g.passed}

    total_credits, earned_credits = _calc_credits(db, course_by_code, completed_codes, specialization)

    weighted_10: list[tuple[float, float]] = []
    weighted_4: list[tuple[float, float]] = []
    for code, grade in best_grades.items():
        if not grade.passed or code not in course_by_code:
            continue
        credits = _course_credits(course_by_code[code])
        if credits <= 0:
            continue
        s10 = _score10_from_grade(grade)
        s4 = _score4_from_grade(grade)
        if s10 is not None:
            weighted_10.append((s10, credits))
        if s4 is not None:
            weighted_4.append((s4, credits))

    return StudentSnapshot(
        courses=courses,
        course_by_code=course_by_code,
        best_grades=best_grades,
        completed_codes=completed_codes,
        avg_score10=_weighted_average(weighted_10),
        avg_score4=_weighted_average(weighted_4),
        total_credits=round(total_credits, 1),
        earned_credits=round(earned_credits, 1),
    )


def _elective_progress(
    db,
    snapshot: StudentSnapshot,
    rules: list[models.ElectiveRule],
) -> list[dict]:
    # Build mapping: (program_code, specialization, group_type) -> set of course_codes
    group_mappings = db.query(models.CourseElectiveGroup).all()
    group_courses: dict[tuple[str, str, str], set[str]] = defaultdict(set)
    for m in group_mappings:
        key = (m.program_code, m.specialization, m.group_type)
        group_courses[key].add(m.course_code)

    result: list[dict] = []
    for rule in rules:
        min_required = _to_float(rule.min_credits_required) or 0.0
        key = (rule.program_code, rule.specialization, rule.group_type)
        courses_in_group = group_courses.get(key, set())

        earned = sum(
            _course_credits(snapshot.course_by_code[code])
            for code in courses_in_group
            if code in snapshot.completed_codes and code in snapshot.course_by_code
        )
        remaining = max(0.0, min_required - earned)
        result.append(
            {
                "specialization": rule.specialization,
                "group_type": rule.group_type,
                "min_credits_required": round(min_required, 1),
                "earned_credits": round(earned, 1),
                "remaining_credits": round(remaining, 1),
                "completed": remaining <= 0,
            }
        )
    result.sort(key=lambda x: ((x.get("specialization") or ""), x["group_type"]))
    return result


def _graduation_estimate(db: Session, user_id: int, snapshot: StudentSnapshot) -> dict:
    """Estimate remaining terms based on past term credit velocity."""
    grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()
    term_credits: dict[str, float] = {}
    for g in grades:
        if g.passed and g.term and g.course_code in snapshot.course_by_code:
            term = g.term.strip()
            term_credits[term] = term_credits.get(term, 0.0) + _course_credits(snapshot.course_by_code[g.course_code])

    terms_studied = len(term_credits)
    remaining_credits = snapshot.total_credits - snapshot.earned_credits

    if terms_studied > 0:
        avg_credits_per_term = sum(term_credits.values()) / terms_studied
        estimated_terms = (remaining_credits / avg_credits_per_term) if avg_credits_per_term > 0 else None
    else:
        avg_credits_per_term = None
        estimated_terms = None

    return {
        "terms_studied": terms_studied,
        "avg_credits_per_term": round(avg_credits_per_term, 1) if avg_credits_per_term is not None else None,
        "estimated_terms_remaining": round(estimated_terms, 1) if estimated_terms is not None else None,
    }


def _required_score_for_target(snapshot: StudentSnapshot, target_gpa4: float) -> float | None:
    """Calculate required average score10 to reach target GPA (4-scale) overall."""
    remaining_credits = snapshot.total_credits - snapshot.earned_credits
    if remaining_credits <= 0:
        return None
    # Convert target GPA4 to score10 weighted target
    # target_gpa4 = (current_avg4 * earned + required_avg4 * remaining) / total
    # required_avg4 = (target_gpa4 * total - current_avg4 * earned) / remaining
    current_avg4 = snapshot.avg_score4 or 0.0
    required_avg4 = (target_gpa4 * snapshot.total_credits - current_avg4 * snapshot.earned_credits) / remaining_credits
    if required_avg4 > 4.0:
        return None  # impossible
    required_avg4 = max(0.0, required_avg4)
    # Convert back to score10 (approximate inverse of _score4_from_grade)
    if required_avg4 >= 3.7:
        return 8.5
    if required_avg4 >= 3.5:
        return 8.0
    if required_avg4 >= 3.0:
        return 7.0
    if required_avg4 >= 2.5:
        return 6.5
    if required_avg4 >= 2.0:
        return 5.5
    if required_avg4 >= 1.5:
        return 5.0
    if required_avg4 >= 1.0:
        return 4.0
    return 2.0


def build_progress_snapshot(db: Session, user_id: int, target_gpa: float | None = None) -> dict:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    specialization = user.specialization if user else None
    snapshot = _build_snapshot(db, user_id, specialization=specialization)

    # Override earned_credits with the official "Số tín chỉ tích lũy" from the transcript
    # if available — this is the authoritative university figure.
    if user and user.official_earned_credits is not None:
        snapshot.earned_credits = round(float(user.official_earned_credits), 1)

    from sqlalchemy import or_
    if specialization:
        rules = db.query(models.ElectiveRule).filter(
            or_(
                models.ElectiveRule.specialization == specialization,
                models.ElectiveRule.specialization == "Chung",
            )
        ).all()
    else:
        rules = db.query(models.ElectiveRule).all()
    elective_groups = _elective_progress(db, snapshot, rules)

    # Build elective group remaining map to filter out elective-extra courses
    elective_group_remaining = _elective_group_remaining(
        db, snapshot.course_by_code, snapshot.completed_codes, specialization
    )
    all_elective_mappings = db.query(models.CourseElectiveGroup).filter(
        or_(
            models.CourseElectiveGroup.specialization == specialization,
            models.CourseElectiveGroup.specialization == "Chung",
        )
    ).all() if specialization else []
    course_to_group: dict[str, tuple] = {
        m.course_code: (m.program_code, m.specialization, m.group_type)
        for m in all_elective_mappings
    }

    def _is_elective_extra(course: models.Course) -> bool:
        key = course_to_group.get(course.course_code)
        if key is None:
            return False
        return elective_group_remaining.get(key, 0.0) <= 0.0

    all_incomplete = [c for c in snapshot.courses if c.course_code not in snapshot.completed_codes]
    remaining_courses = [c for c in all_incomplete if not _is_elective_extra(c)]
    remaining_courses.sort(key=lambda c: c.course_code)
    import sys
    print(f"[DEBUG] user={user_id} spec={specialization!r} all_incomplete={len(all_incomplete)} remaining={len(remaining_courses)} egr={elective_group_remaining}", file=sys.stderr, flush=True)

    completion_percent = (snapshot.earned_credits / snapshot.total_credits * 100.0) if snapshot.total_credits > 0 else 0.0

    grad = _graduation_estimate(db, user_id, snapshot)

    required_score10 = None
    if target_gpa is not None:
        required_score10 = _required_score_for_target(snapshot, target_gpa)

    # --- Internship / thesis eligibility ---
    internship_course, thesis_course = _find_internship_thesis(snapshot.courses, specialization)

    internship_done = (
        internship_course is not None
        and internship_course.course_code in snapshot.completed_codes
    )
    thesis_done = (
        thesis_course is not None
        and thesis_course.course_code in snapshot.completed_codes
    )

    internship_outstanding = (
        _course_credits(internship_course)
        if internship_course and not internship_done
        else 0.0
    )
    thesis_outstanding = (
        _course_credits(thesis_course)
        if thesis_course and not thesis_done
        else 0.0
    )
    remaining_non_special = (
        snapshot.total_credits - snapshot.earned_credits
        - thesis_outstanding - internship_outstanding
    )

    internship_eligible = (
        internship_course is not None
        and not internship_done
        and remaining_non_special <= INTERNSHIP_REMAINING_BUFFER
    )
    thesis_eligible = (
        thesis_course is not None
        and not thesis_done
        and internship_done
    )
    graduation_ready = snapshot.earned_credits >= GRADUATION_CREDIT_THRESHOLD

    # --- Prerequisite issues ---
    from collections import defaultdict as _dd
    prereqs = db.query(models.CoursePrerequisite).all()
    prereq_map: dict[str, list[str]] = _dd(list)
    for p in prereqs:
        prereq_map[p.course_code].append(p.prerequisite_code)

    prereq_issues = []
    for c in remaining_courses:
        required = prereq_map.get(c.course_code, [])
        missing = [code for code in required if code not in snapshot.completed_codes]
        if missing:
            prereq_issues.append({
                "course_code": c.course_code,
                "course_name": c.course_name,
                "missing_prereq_codes": missing,
            })

    return {
        "total_courses": len(snapshot.courses),
        "completed_courses": len(snapshot.completed_codes.intersection(snapshot.course_by_code.keys())),
        "remaining_courses": len(remaining_courses),
        "total_credits": snapshot.total_credits,
        "earned_credits": snapshot.earned_credits,
        "completion_percent": round(completion_percent, 2),
        "avg_score10": round(snapshot.avg_score10, 2) if snapshot.avg_score10 is not None else None,
        "avg_score4": round(snapshot.avg_score4, 2) if snapshot.avg_score4 is not None else None,
        "elective_groups": elective_groups,
        "remaining_course_items": [
            {"course_code": c.course_code, "course_name": c.course_name, "credits": _course_credits(c)}
            for c in remaining_courses
        ],
        "terms_studied": grad["terms_studied"],
        "avg_credits_per_term": grad["avg_credits_per_term"],
        "estimated_terms_remaining": grad["estimated_terms_remaining"],
        "required_score10_for_target": round(required_score10, 1) if required_score10 is not None else None,
        "target_gpa": target_gpa,
        "graduation_threshold": GRADUATION_CREDIT_THRESHOLD,
        "graduation_ready": graduation_ready,
        "internship_eligible": internship_eligible,
        "internship_done": internship_done,
        "thesis_eligible": thesis_eligible,
        "thesis_done": thesis_done,
        "prereq_issues": prereq_issues,
    }


def _course_tracks(course_name: str) -> set[str]:
    normalized_name = _normalize_text(course_name)
    matched: set[str] = set()
    for track_key, config in TRACKS.items():
        if any(keyword in normalized_name for keyword in config["keywords"]):
            matched.add(track_key)
    return matched


def _build_track_strengths(snapshot: StudentSnapshot) -> dict[str, float]:
    score_bucket: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for code, grade in snapshot.best_grades.items():
        if not grade.passed or code not in snapshot.course_by_code:
            continue
        score10 = _score10_from_grade(grade)
        if score10 is None:
            continue
        credits = _course_credits(snapshot.course_by_code[code])
        if credits <= 0:
            continue
        for track in _course_tracks(snapshot.course_by_code[code].course_name):
            score_bucket[track].append((score10, credits))

    strengths: dict[str, float] = {}
    for track_key, values in score_bucket.items():
        avg = _weighted_average(values)
        if avg is not None:
            strengths[track_key] = avg
    return strengths


def _difficulty_score(course: models.Course) -> float:
    score = _course_credits(course)
    name = _normalize_text(course.course_name)
    if "do an" in name:
        score += 1.5
    if "thuc tap" in name:
        score += 1.2
    if "tri tue nhan tao" in name:
        score += 0.8
    if "du lieu" in name:
        score += 0.4
    return score


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _elective_group_remaining(
    db: Session,
    course_by_code: dict,
    completed_codes: set,
    specialization: str | None,
) -> dict[tuple, float]:
    """Return {(program_code, specialization, group_type): remaining_credits_needed}."""
    if not specialization:
        return {}
    from sqlalchemy import or_
    rules = db.query(models.ElectiveRule).filter(
        or_(
            models.ElectiveRule.specialization == specialization,
            models.ElectiveRule.specialization == "Chung",
        )
    ).all()
    group_mappings = db.query(models.CourseElectiveGroup).filter(
        or_(
            models.CourseElectiveGroup.specialization == specialization,
            models.CourseElectiveGroup.specialization == "Chung",
        )
    ).all()
    group_courses: dict[tuple, set] = defaultdict(set)
    for m in group_mappings:
        group_courses[(m.program_code, m.specialization, m.group_type)].add(m.course_code)

    remaining: dict[tuple, float] = {}
    for rule in rules:
        key = (rule.program_code, rule.specialization, rule.group_type)
        earned = sum(
            _course_credits(course_by_code[code])
            for code in group_courses.get(key, set())
            if code in completed_codes and code in course_by_code
        )
        rem = max(0.0, float(rule.min_credits_required) - earned)
        remaining[key] = rem
    return remaining


def build_recommendations(db: Session, user_id: int, limit: int = 5) -> dict:
    safe_limit = max(1, min(int(limit), 20))
    user = db.query(models.User).filter(models.User.id == user_id).first()
    specialization = user.specialization if user else None
    snapshot = _build_snapshot(db, user_id, specialization=specialization)

    if user and user.official_earned_credits is not None:
        snapshot.earned_credits = round(float(user.official_earned_credits), 1)

    # Prerequisites map
    prereqs = db.query(models.CoursePrerequisite).all()
    prereq_map: dict[str, list[str]] = defaultdict(list)
    for p in prereqs:
        prereq_map[p.course_code].append(p.prerequisite_code)

    # Elective group membership & remaining credits needed
    elective_group_remaining = _elective_group_remaining(
        db, snapshot.course_by_code, snapshot.completed_codes, specialization
    )
    from sqlalchemy import or_
    all_elective_mappings = db.query(models.CourseElectiveGroup).filter(
        or_(
            models.CourseElectiveGroup.specialization == specialization,
            models.CourseElectiveGroup.specialization == "Chung",
        )
    ).all() if specialization else []
    course_to_group: dict[str, tuple] = {}
    for m in all_elective_mappings:
        course_to_group[m.course_code] = (m.program_code, m.specialization, m.group_type)

    # Identify internship and thesis
    internship_course, thesis_course = _find_internship_thesis(snapshot.courses, specialization)
    internship_done = internship_course and internship_course.course_code in snapshot.completed_codes
    thesis_done = thesis_course and thesis_course.course_code in snapshot.completed_codes
    internship_code = internship_course.course_code if internship_course else None
    thesis_code = thesis_course.course_code if thesis_course else None

    internship_outstanding = (
        _course_credits(internship_course) if internship_course and not internship_done else 0.0
    )
    thesis_outstanding = (
        _course_credits(thesis_course) if thesis_course and not thesis_done else 0.0
    )
    remaining_non_special = (
        snapshot.total_credits - snapshot.earned_credits - thesis_outstanding - internship_outstanding
    )
    internship_eligible = (
        internship_course is not None and not internship_done
        and remaining_non_special <= INTERNSHIP_REMAINING_BUFFER
    )
    thesis_eligible = (
        thesis_course is not None and not thesis_done and bool(internship_done)
    )

    remaining_courses = [c for c in snapshot.courses if c.course_code not in snapshot.completed_codes]

    track_strengths = _build_track_strengths(snapshot)
    preferred_track = max(track_strengths.items(), key=lambda x: x[1])[0] if track_strengths else None
    baseline_ability = snapshot.avg_score10 if snapshot.avg_score10 is not None else 6.5
    scored_items: list[dict] = []

    for course in remaining_courses:
        code = course.course_code
        credits = _course_credits(course)

        # Determine course category
        is_thesis = code == thesis_code
        is_internship = code == internship_code
        group_key = course_to_group.get(code)
        group_remaining = elective_group_remaining.get(group_key, 0.0) if group_key else 0.0
        is_elective_needed = group_key is not None and group_remaining > 0.0
        is_elective_extra = group_key is not None and group_remaining <= 0.0

        # Skip elective courses from groups that are already complete
        if is_elective_extra:
            continue

        # Check prerequisites
        missing_prereqs = [p for p in prereq_map.get(code, []) if p not in snapshot.completed_codes]
        if missing_prereqs:
            continue  # cannot take this course yet

        # Special handling for thesis/internship gating
        if is_thesis and not thesis_eligible:
            continue
        if is_internship and not internship_eligible:
            continue

        recommendation_score = 50.0
        reason_codes: list[str] = ["NOT_COMPLETED"]
        reasons: list[str] = []

        # Thesis / internship — highest priority
        if is_thesis:
            recommendation_score += 40.0
            reason_codes.append("THESIS_READY")
            reasons.append("Bạn đủ điều kiện làm Đồ án tốt nghiệp.")
        elif is_internship:
            recommendation_score += 35.0
            reason_codes.append("INTERNSHIP_READY")
            reasons.append("Bạn đủ điều kiện thực tập doanh nghiệp.")
        elif group_key is None:
            # Required non-elective course
            recommendation_score += 20.0
            reason_codes.append("REQUIRED")
            reasons.append("Môn bắt buộc trong chương trình đào tạo.")
        else:
            # Elective needed for group completion
            recommendation_score += 15.0
            reason_codes.append("ELECTIVE_NEEDED")
            _, gspec, gtype = group_key
            reasons.append(f"Cần thêm tín chỉ nhóm tự chọn {gtype} (còn thiếu {group_remaining:.0f} TC).")

        # Ability fit / difficulty
        difficulty = _difficulty_score(course)
        target_difficulty = 3.2 if baseline_ability < 6.5 else (4.2 if baseline_ability >= 7.5 else 3.7)
        ability_fit = 12.0 - abs(difficulty - target_difficulty) * 4.0
        recommendation_score += ability_fit

        if baseline_ability < 6.5 and credits <= 3:
            recommendation_score += 5.0
            reason_codes.append("BALANCED_LOAD")
            reasons.append("Khối lượng tín chỉ vừa phải.")
        elif baseline_ability >= 7.5 and credits >= 4:
            recommendation_score += 4.0
            reason_codes.append("CHALLENGE_READY")
            reasons.append("Năng lực phù hợp để học môn có độ khó cao.")

        # Track alignment
        candidate_tracks = _course_tracks(course.course_name)
        if preferred_track and preferred_track in candidate_tracks:
            recommendation_score += 14.0
            reason_codes.append("TRACK_ALIGNMENT")
            reasons.append("Phù hợp với nhóm môn bạn học tốt nhất.")
        elif candidate_tracks:
            recommendation_score += 6.0

        if not reasons:
            reasons.append("Môn chưa hoàn thành trong chương trình.")

        fit_probability = _clamp(recommendation_score, 1.0, 99.0)
        direction_track = preferred_track
        if candidate_tracks and (not direction_track or direction_track not in candidate_tracks):
            direction_track = sorted(candidate_tracks)[0]
        study_direction = TRACKS[direction_track]["label"] if direction_track else "Nền tảng tổng hợp"

        scored_items.append({
            "course_code": code,
            "course_name": course.course_name,
            "credits": credits,
            "recommendation_score": round(recommendation_score, 2),
            "fit_probability": round(fit_probability, 2),
            "reason_codes": sorted(set(reason_codes)),
            "reasons": reasons,
            "study_direction": study_direction,
            "category": "thesis" if is_thesis else ("internship" if is_internship else ("elective" if group_key else "required")),
            "elective_group": group_key[2] if group_key else None,
        })

    scored_items.sort(key=lambda x: (-x["recommendation_score"], x["course_code"]))
    suggested_track_label = TRACKS[preferred_track]["label"] if preferred_track else "Nền tảng tổng hợp"

    return {
        "generated_at": datetime.now(timezone.utc),
        "total_candidates": len(scored_items),
        "avg_score10_baseline": round(snapshot.avg_score10, 2) if snapshot.avg_score10 is not None else None,
        "avg_score4_baseline": round(snapshot.avg_score4, 2) if snapshot.avg_score4 is not None else None,
        "suggested_track": suggested_track_label,
        "recommendations": scored_items[:safe_limit],
        "graduation_ready": snapshot.earned_credits >= GRADUATION_CREDIT_THRESHOLD,
        "internship_eligible": internship_eligible,
        "thesis_eligible": thesis_eligible,
    }
