"""
Synthetic student data generator — đọc từ DB thực.

Thay vì dùng CTDT hard-code, module này:
1. Đọc courses, prereqs, elective rules từ DB
2. Mô phỏng hành trình học của các archetype sinh viên khác nhau
3. Trả về (X, y) training examples với label chất lượng:
   label = 1 nếu sinh viên qua môn với điểm ≥ 6.5 VÀ
           (môn nằm trên critical path HOẶC khớp định hướng)
   label = 0 nếu trượt / điểm thấp / không phù hợp

Sử dụng:
    from backend.scripts.synthetic_data import generate_training_data
    X, y = generate_training_data(db, specialization="Khoa học dữ liệu", n_students=500)
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session

from backend.core.curriculum_graph import (
    CurriculumGraph,
    CAREER_TO_TRACKS,
    CURRICULUM_SEMESTER,
    MAX_CURRICULUM_SEM,
    FEATURE_NAMES,
)


# ── Archetype định nghĩa ─────────────────────────────────────────────────────────
@dataclass
class StudentArchetype:
    name: str
    gpa_mean: float         # GPA trung bình (thang 10)
    gpa_std: float          # Độ lệch chuẩn GPA
    pass_floor: float       # Điểm tối thiểu để qua (thường 5.0)
    max_tc: float           # TC tối đa mỗi kỳ
    career: str             # "ai_data" | "web" | "network_security" | "general"
    strategy: str           # "optimal" | "track_first" | "easy_first" | "random"
    weight: float           # Tỷ lệ xuất hiện trong dataset


# Phân phối xấp xỉ thực tế của sinh viên UIT
ARCHETYPES: list[StudentArchetype] = [
    StudentArchetype("gioi_ai",    8.3, 0.6, 5.0, 21, "ai_data",          "optimal",     0.08),
    StudentArchetype("gioi_sw",    8.1, 0.6, 5.0, 21, "web",              "optimal",     0.08),
    StudentArchetype("gioi_net",   8.0, 0.6, 5.0, 21, "network_security", "optimal",     0.06),
    StudentArchetype("kha_ai",     7.2, 0.8, 5.0, 18, "ai_data",          "track_first", 0.12),
    StudentArchetype("kha_sw",     7.0, 0.9, 5.0, 18, "web",              "track_first", 0.12),
    StudentArchetype("kha_net",    7.1, 0.8, 5.0, 18, "network_security", "track_first", 0.10),
    StudentArchetype("tb_chung",   6.2, 1.0, 5.0, 15, "general",          "easy_first",  0.18),
    StudentArchetype("yeu_chung",  5.7, 1.2, 5.0, 12, "general",          "easy_first",  0.14),
    StudentArchetype("tre_sw",     6.8, 0.9, 5.0, 18, "web",              "random",      0.06),
    StudentArchetype("tre_ai",     6.9, 0.8, 5.0, 18, "ai_data",          "random",      0.06),
]


@dataclass
class CourseOutcome:
    course_code: str
    score10: float
    passed: bool
    semester_idx: int


@dataclass
class StudentJourney:
    archetype: StudentArchetype
    semesters: list[list[CourseOutcome]] = field(default_factory=list)
    gpa_history: list[float] = field(default_factory=list)  # GPA sau mỗi kỳ


# ── Mô phỏng điểm số ────────────────────────────────────────────────────────────
def _simulate_score(
    student_gpa: float,
    course_code: str,
    prereq_scores: list[float],
    track_match: bool,
    course_avg: float,
    rng: random.Random,
) -> float:
    """
    Mô phỏng điểm dựa trên:
    - GPA nền tảng sinh viên (50%)
    - Độ khó môn học - course_avg (25%)
    - Điểm nền tảng tiên quyết (15%)
    - Track alignment (10%)
    """
    base = student_gpa
    difficulty_adj = (course_avg - 6.5) * 0.3       # môn khó → penalty
    prereq_adj = 0.0
    if prereq_scores:
        prereq_avg = sum(prereq_scores) / len(prereq_scores)
        prereq_adj = (prereq_avg - student_gpa) * 0.25
    track_adj = 0.35 if track_match else -0.15

    expected = base + difficulty_adj + prereq_adj + track_adj
    noise = rng.gauss(0, 0.85)
    score = max(0.0, min(10.0, round(expected + noise, 1)))
    return score


def _rolling_gpa(journey: StudentJourney) -> float:
    all_scores = [
        c.score10 for sem in journey.semesters for c in sem if c.passed
    ]
    return sum(all_scores) / len(all_scores) if all_scores else 5.5


def _gpa_trend(journey: StudentJourney) -> float:
    """Trả về -1/0/1 dựa trên 3 kỳ gần nhất."""
    if len(journey.gpa_history) < 2:
        return 0.0
    vals = journey.gpa_history[-3:]
    diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
    avg_diff = sum(diffs) / len(diffs)
    if avg_diff > 0.1:
        return 1.0
    if avg_diff < -0.1:
        return -1.0
    return 0.0


def _credits_earned(journey: StudentJourney, graph: CurriculumGraph) -> float:
    total = 0.0
    for sem in journey.semesters:
        for c in sem:
            if c.passed:
                course = graph.courses.get(c.course_code)
                total += float(course.credits or 0) if course else 0.0
    return total


def _prereq_scores_for(
    course_code: str,
    prereq_map: dict[str, list[str]],
    completed_scores: dict[str, float],
) -> list[float]:
    return [
        completed_scores[p]
        for p in prereq_map.get(course_code, [])
        if p in completed_scores
    ]


# ── Chiến lược chọn môn ─────────────────────────────────────────────────────────
def _select_courses(
    eligible: list[str],
    archetype: StudentArchetype,
    graph: CurriculumGraph,
    completed: set[str],
    difficulty_stats: dict[str, dict],
    unlock_scores: dict[str, int],
    rng: random.Random,
) -> list[str]:
    """Chọn môn theo chiến lược của archetype, không vượt quá max_tc."""
    career_tracks = CAREER_TO_TRACKS.get(archetype.career, set())

    def course_priority(code: str) -> float:
        course = graph.courses.get(code)
        tc = float(course.credits or 3) if course else 3.0
        ctdt_sem = graph.get_curriculum_semester(code)
        course_tracks = graph.get_course_tracks(code)
        track_hit = bool(course_tracks & career_tracks)
        unlock = unlock_scores.get(code, 0)
        pass_rate = difficulty_stats.get(code, {}).get("pass_rate", 0.75)

        if archetype.strategy == "optimal":
            # Ưu tiên: critical path + track + đúng thời điểm
            return unlock * 3 + (5 if track_hit else 0) + (1 / (abs(ctdt_sem - len(graph.courses)) + 1))
        elif archetype.strategy == "track_first":
            return (10 if track_hit else 0) + unlock
        elif archetype.strategy == "easy_first":
            return pass_rate * 10 - tc  # Ưu tiên môn dễ, ít tín chỉ
        else:  # random
            return rng.random() * 10

    sorted_eligible = sorted(eligible, key=course_priority, reverse=True)

    # Thêm yếu tố ngẫu nhiên 30% để đa dạng hóa (tránh quá deterministic)
    if rng.random() < 0.3:
        rng.shuffle(sorted_eligible)

    selected, total_tc = [], 0.0
    for code in sorted_eligible:
        course = graph.courses.get(code)
        tc = float(course.credits or 3) if course else 3.0
        if total_tc + tc <= archetype.max_tc:
            selected.append(code)
            total_tc += tc
        if total_tc >= archetype.max_tc * 0.80:
            break

    return selected


# ── Simulation engine ────────────────────────────────────────────────────────────
def _simulate_journey(
    archetype: StudentArchetype,
    graph: CurriculumGraph,
    difficulty_stats: dict[str, dict],
    rng: random.Random,
) -> StudentJourney:
    journey = StudentJourney(archetype=archetype)
    completed: set[str] = set()
    completed_scores: dict[str, float] = {}
    failed_attempts: dict[str, int] = {}

    # Thêm nhiễu cá nhân: mỗi sinh viên giỏi/yếu hơn mean một chút
    personal_bias = rng.gauss(0, 0.4)
    effective_gpa = max(4.0, min(9.5, archetype.gpa_mean + personal_bias))

    all_codes = set(graph.courses.keys())

    for sem_idx in range(1, 12):   # tối đa 11 kỳ (5.5 năm)
        # Môn eligible: prereq đã qua, chưa hoàn thành, không trong nhóm tự chọn đã đủ
        eligible = [
            code for code in all_codes
            if code not in completed
            and all(p in completed for p in graph.prereq_map.get(code, []))
            and not graph.is_elective_extra(code)
        ]

        if not eligible:
            break   # Tốt nghiệp hoặc tắc nghẽn

        # Tính unlock scores
        remaining_codes = set(all_codes) - completed
        unlock_scores = graph.compute_unlock_scores(remaining_codes)
        max_unlock = max(unlock_scores.values()) if unlock_scores else 1

        # Cho phép thi lại môn đã trượt (tối đa 1 môn/kỳ, xác suất 60%)
        failed = [c for c in all_codes if c not in completed and c in failed_attempts and
                  all(p in completed for p in graph.prereq_map.get(c, []))]
        if failed and rng.random() < 0.6:
            retake = rng.choice(failed[:3])
            if retake not in eligible:
                eligible.append(retake)

        selected = _select_courses(
            eligible, archetype, graph, completed, difficulty_stats, unlock_scores, rng
        )

        if not selected:
            break

        sem_outcomes: list[CourseOutcome] = []
        for code in selected:
            course = graph.courses.get(code)
            course_avg = difficulty_stats.get(code, {}).get("avg_score10", 6.5)
            prereq_scores = _prereq_scores_for(code, graph.prereq_map, completed_scores)
            career_tracks = CAREER_TO_TRACKS.get(archetype.career, set())
            track_match = bool(graph.get_course_tracks(code) & career_tracks)

            # GPA hiện tại của sinh viên (tích lũy đến kỳ này)
            current_gpa = _rolling_gpa(journey) if journey.semesters else effective_gpa

            score = _simulate_score(
                current_gpa, code, prereq_scores, track_match, course_avg, rng
            )
            passed = score >= archetype.pass_floor

            # Trượt lần đầu → thêm vào failed_attempts
            if not passed:
                failed_attempts[code] = failed_attempts.get(code, 0) + 1
            else:
                completed.add(code)
                completed_scores[code] = score

            sem_outcomes.append(CourseOutcome(
                course_code=code,
                score10=score,
                passed=passed,
                semester_idx=sem_idx,
            ))

        journey.semesters.append(sem_outcomes)

        # Cập nhật GPA history
        sem_passed_scores = [c.score10 for c in sem_outcomes if c.passed]
        if sem_passed_scores:
            journey.gpa_history.append(
                (_rolling_gpa(journey) * (sem_idx - 1) + sum(sem_passed_scores) / len(sem_passed_scores))
                / sem_idx
            )
        elif journey.gpa_history:
            journey.gpa_history.append(journey.gpa_history[-1])

        # Kiểm tra tốt nghiệp (>= 80% credits)
        earned = _credits_earned(journey, graph)
        if earned >= graph.total_credits * 0.85:
            break

    return journey


# ── Training example builder ─────────────────────────────────────────────────────
def _build_training_examples(
    journey: StudentJourney,
    graph: CurriculumGraph,
    difficulty_stats: dict[str, dict],
    rng: random.Random,
) -> tuple[list[list[float]], list[int]]:
    """
    Từ một hành trình sinh viên, tạo ra các training examples:
    - Positive (label=1): môn được chọn, qua với điểm ≥ 6.5, và có giá trị chiến lược
    - Negative (label=0): môn eligible NHƯNG không chọn hoặc chọn nhưng trượt/điểm thấp

    Trả về (X, y) lists.
    """
    X: list[list[float]] = []
    y: list[int] = []

    all_codes = set(graph.courses.keys())
    completed_so_far: set[str] = set()
    completed_scores: dict[str, float] = {}

    for sem_idx, sem_outcomes in enumerate(journey.semesters):
        sem_codes_chosen = {c.course_code for c in sem_outcomes}

        # State sinh viên TẠI THỜI ĐIỂM này (trước kỳ này)
        current_gpa = journey.gpa_history[sem_idx - 1] if sem_idx > 0 and journey.gpa_history else journey.archetype.gpa_mean
        gpa_trend = _gpa_trend(journey) if sem_idx > 1 else 0.0
        credits_earned = sum(
            float(graph.courses[c].credits or 0)
            for c in completed_so_far if c in graph.courses
        )
        sem_count = sem_idx

        # Eligible ở thời điểm này
        eligible_now = [
            code for code in all_codes
            if code not in completed_so_far
            and all(p in completed_so_far for p in graph.prereq_map.get(code, []))
            and not graph.is_elective_extra(code)
        ]

        # Unlock scores tại thời điểm này
        remaining = set(all_codes) - completed_so_far
        unlock_scores = graph.compute_unlock_scores(remaining)
        max_unlock = max(unlock_scores.values()) if unlock_scores else 1

        for code in eligible_now:
            course = graph.courses.get(code)
            if not course:
                continue

            dstat = difficulty_stats.get(code, {})
            pass_rate = dstat.get("pass_rate", 0.75)
            course_avg = dstat.get("avg_score10", 6.5)

            prereq_scores_list = [
                completed_scores[p]
                for p in graph.prereq_map.get(code, [])
                if p in completed_scores
            ]
            prereq_avg = (
                sum(prereq_scores_list) / len(prereq_scores_list)
                if prereq_scores_list else None
            )

            features = graph.extract_features(
                course_code=code,
                student_gpa10=current_gpa,
                student_gpa_trend=gpa_trend,
                student_credits_earned=credits_earned,
                student_sem_count=sem_count,
                course_pass_rate=pass_rate,
                course_avg_score10=course_avg,
                unlock_count=unlock_scores.get(code, 0),
                max_unlock_count=max_unlock,
                prereq_avg_score=prereq_avg,
                career_track=journey.archetype.career,
            )

            # ── Xác định label ───────────────────────────────────────────────
            if code in sem_codes_chosen:
                # Môn được chọn — tìm outcome
                outcome = next((c for c in sem_outcomes if c.course_code == code), None)
                if outcome and outcome.passed and outcome.score10 >= 6.5:
                    # Chất lượng tốt: qua với điểm >= 6.5
                    # Tăng giá trị nếu có unlock cao hoặc track match
                    has_strategic_value = (
                        unlock_scores.get(code, 0) >= 1
                        or graph.is_elective_needed(code)
                        or code in graph.required_codes
                    )
                    label = 1 if has_strategic_value else 0
                else:
                    # Trượt hoặc điểm thấp → label 0
                    label = 0
            else:
                # Môn eligible nhưng không chọn kỳ này
                # Label 0 với xác suất cao (30% skip để tránh quá nhiều negative)
                if rng.random() < 0.30:
                    label = 0
                else:
                    continue   # Skip để không làm dataset quá mất cân bằng

            X.append(features)
            y.append(label)

        # Cập nhật completed
        for c in sem_outcomes:
            if c.passed:
                completed_so_far.add(c.course_code)
                completed_scores[c.course_code] = c.score10

    return X, y


# ── Public API ───────────────────────────────────────────────────────────────────
def generate_training_data(
    db: Session,
    specialization: str,
    n_students: int = 600,
    seed: int = 42,
) -> tuple[list[list[float]], list[int]]:
    """
    Sinh training data từ DB thực.

    Args:
        db: SQLAlchemy session
        specialization: VD "Khoa học dữ liệu"
        n_students: Số sinh viên mô phỏng (khuyến nghị 500–1000)
        seed: Random seed để reproducibility

    Returns:
        (X, y): X là list of feature vectors, y là list of labels (0/1)
    """
    from backend.core.academic_engine import _get_difficulty_stats

    rng = random.Random(seed)

    # Build graph từ DB (không truyền completed — dùng graph "trống" cho training)
    graph = CurriculumGraph.from_db(db, specialization, completed_codes=set())

    # Difficulty stats từ dữ liệu thực (nếu có, ngược lại dùng default)
    difficulty_stats = _get_difficulty_stats(db)

    # Chọn archetype theo weight
    total_w = sum(a.weight for a in ARCHETYPES)
    weights = [a.weight / total_w for a in ARCHETYPES]

    all_X: list[list[float]] = []
    all_y: list[int] = []

    for i in range(n_students):
        # Chọn archetype theo phân phối
        archetype = rng.choices(ARCHETYPES, weights=weights, k=1)[0]

        journey = _simulate_journey(archetype, graph, difficulty_stats, rng)
        X_student, y_student = _build_training_examples(journey, graph, difficulty_stats, rng)
        all_X.extend(X_student)
        all_y.extend(y_student)

    # Tích hợp real data từ DB nếu có (course_registrations với outcome đã biết)
    real_X, real_y = _collect_real_examples(db, graph, difficulty_stats)
    if real_X:
        # Real data có trọng số x5 (quan trọng hơn synthetic)
        all_X.extend(real_X * 5)
        all_y.extend(real_y * 5)

    pos = sum(all_y)
    neg = len(all_y) - pos
    print(f"[synthetic_data] Generated {len(all_y)} examples "
          f"({pos} positive={100*pos/max(1,len(all_y)):.1f}%, {neg} negative) "
          f"from {n_students} synthetic + {len(real_X)} real students")

    return all_X, all_y


def _collect_real_examples(
    db: Session,
    graph: CurriculumGraph,
    difficulty_stats: dict[str, dict],
) -> tuple[list[list[float]], list[int]]:
    """Thu thập training examples từ course_registrations thực (nếu có đủ data)."""
    from backend.db import models as m
    from backend.core.academic_engine import _select_best_grade_per_course, _score10_from_grade

    X: list[list[float]] = []
    y: list[int] = []

    # Lấy tất cả registrations có outcome đã biết
    regs = db.query(m.CourseRegistration).filter(
        m.CourseRegistration.outcome.in_(["passed", "failed"])
    ).all()

    if len(regs) < 20:
        return X, y   # Không đủ để học

    # Nhóm theo user
    by_user: dict[int, list[m.CourseRegistration]] = {}
    for r in regs:
        by_user.setdefault(r.user_id, []).append(r)

    for user_id, user_regs in by_user.items():
        user = db.query(m.User).filter(m.User.id == user_id).first()
        if not user:
            continue

        grades = db.query(m.UserGrade).filter(m.UserGrade.user_id == user_id).all()
        best_grades = _select_best_grade_per_course(grades)
        completed = {code for code, g in best_grades.items() if g.passed}

        gpa_scores = [
            (_score10_from_grade(g) or 0) * float(graph.courses[g.course_code].credits or 0)
            for g in best_grades.values()
            if g.passed and g.course_code in graph.courses
        ]
        total_w = sum(
            float(graph.courses[g.course_code].credits or 0)
            for g in best_grades.values()
            if g.passed and g.course_code in graph.courses
        )
        current_gpa = sum(gpa_scores) / total_w if total_w > 0 else 6.0

        credits_earned = sum(
            float(graph.courses[c].credits or 0)
            for c in completed if c in graph.courses
        )
        sem_count = len({g.term for g in grades if g.term})

        remaining = set(graph.courses.keys()) - completed
        unlock_scores = graph.compute_unlock_scores(remaining)
        max_unlock = max(unlock_scores.values()) if unlock_scores else 1

        for reg in user_regs:
            code = reg.course_code
            if code not in graph.courses:
                continue

            dstat = difficulty_stats.get(code, {})
            prereq_scores_list = [
                _score10_from_grade(best_grades[p]) or 6.0
                for p in graph.prereq_map.get(code, [])
                if p in best_grades and best_grades[p].passed
            ]
            prereq_avg = sum(prereq_scores_list) / len(prereq_scores_list) if prereq_scores_list else None

            features = graph.extract_features(
                course_code=code,
                student_gpa10=current_gpa,
                student_gpa_trend=0.0,
                student_credits_earned=credits_earned,
                student_sem_count=sem_count,
                course_pass_rate=dstat.get("pass_rate"),
                course_avg_score10=dstat.get("avg_score10"),
                unlock_count=unlock_scores.get(code, 0),
                max_unlock_count=max_unlock,
                prereq_avg_score=prereq_avg,
                career_track=user.career_goal,
            )

            # Label từ kết quả thực
            grade_rec = best_grades.get(code)
            if grade_rec:
                score10 = _score10_from_grade(grade_rec) or 0.0
                label = 1 if (grade_rec.passed and score10 >= 6.5) else 0
            else:
                label = 1 if reg.outcome == "passed" else 0

            X.append(features)
            y.append(label)

    return X, y
