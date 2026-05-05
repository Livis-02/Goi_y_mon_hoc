from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import log
import unicodedata

from sqlalchemy.orm import Session

from backend.db import models

# Generic fallback tracks (used when specialization is unknown)
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

# Specialization-specific career sub-directions.
# Keys must match specialization strings stored in the DB.
SPECIALIZATION_TRACKS: dict[str, dict[str, dict]] = {
    "Khoa học máy tính": {
        "ai_ml": {
            "label": "AI / Học máy",
            "icon": "psychology",
            "desc": "Machine learning, deep learning, computer vision, NLP",
            "keywords": ["tri tue nhan tao", "hoc may", "khai pha", "khoa hoc du lieu", "thi giac may tinh", "xu ly ngon ngu", "ky nghe tri thuc"],
        },
        "data_engineer": {
            "label": "Kỹ thuật dữ liệu",
            "icon": "storage",
            "desc": "Data engineering, cloud, big data, databases",
            "keywords": ["co so du lieu", "du lieu lon", "phan tich du lieu", "kho du lieu", "dam may", "dien toan dam may", "quan tri co so du lieu"],
        },
        "software_dev": {
            "label": "Phát triển phần mềm",
            "icon": "code",
            "desc": "Software engineering, web/mobile, open source",
            "keywords": ["lap trinh", "web", "phan mem", "kien truc", "phan tich thiet ke", "ma nguon mo", "thuong mai dien tu"],
        },
    },
    "Mạng máy tính": {
        "network_engineer": {
            "label": "Kỹ sư mạng",
            "icon": "router",
            "desc": "Network infrastructure, system administration, cloud",
            "keywords": ["quan tri mang", "ha tang mang", "kien truc mang", "he thong phan tan", "dam may", "dich vu mang"],
        },
        "security_analyst": {
            "label": "An ninh mạng",
            "icon": "security",
            "desc": "Network security, penetration testing, cryptography",
            "keywords": ["an ninh", "bao mat", "ma hoa", "kiem thu xam nhap", "tuong lua", "an toan thong tin"],
        },
        "iot_cloud": {
            "label": "IoT / Điện toán đám mây",
            "icon": "cloud",
            "desc": "Internet of Things, embedded systems, cloud platforms",
            "keywords": ["iot", "nhung", "cam bien", "thiet bi thong minh", "dam may", "kien truc iot"],
        },
    },
    "Công nghệ phần mềm": {
        "backend_dev": {
            "label": "Backend developer",
            "icon": "dns",
            "desc": ".NET, Java, API, databases, distributed systems",
            "keywords": ["lap trinh", "dotnet", "java", "co so du lieu", "he thong", "api", "backend", "dich vu web"],
        },
        "frontend_mobile": {
            "label": "Frontend / Mobile",
            "icon": "phone_android",
            "desc": "Web frontend, mobile apps, UI/UX",
            "keywords": ["web", "giao dien", "mobile", "ung dung", "thuong mai dien tu", "phat trien ung dung"],
        },
        "devops_architect": {
            "label": "DevOps / Kiến trúc phần mềm",
            "icon": "settings_suggest",
            "desc": "Software architecture, CI/CD, quality assurance, UML",
            "keywords": ["kien truc phan mem", "chat luong", "kiem thu", "uml", "phan tich thiet ke huong doi tuong", "bao mat", "dam may"],
        },
    },
    "Hệ thống thông tin": {
        "system_analyst": {
            "label": "Phân tích hệ thống",
            "icon": "manage_search",
            "desc": "Business analysis, ERP, process modeling, IT governance",
            "keywords": ["phan tich", "thiet ke he thong", "quy trinh nghiep vu", "he thong thong tin", "quan ly"],
        },
        "data_bi": {
            "label": "Dữ liệu / Business Intelligence",
            "icon": "bar_chart",
            "desc": "Data warehousing, BI, reporting, analytics",
            "keywords": ["co so du lieu", "kho du lieu", "bao cao", "phan tich du lieu", "tri thuc", "hoc may"],
        },
        "enterprise_dev": {
            "label": "Phát triển hệ thống doanh nghiệp",
            "icon": "corporate_fare",
            "desc": "Enterprise software, web systems, integration",
            "keywords": ["lap trinh", "he thong phan tan", "web", "phan mem", "tich hop he thong", "dich vu"],
        },
    },
    "Tin học kinh tế": {
        "fintech": {
            "label": "Tài chính số / FinTech",
            "icon": "payments",
            "desc": "Financial software, accounting systems, banking IT",
            "keywords": ["tai chinh", "ke toan", "ngan hang", "thuong mai dien tu", "kinh te so", "toan ung dung"],
        },
        "business_software": {
            "label": "Phần mềm quản lý doanh nghiệp",
            "icon": "business_center",
            "desc": "ERP, management systems, business process automation",
            "keywords": ["quan ly", "doanh nghiep", "erp", "phan mem quan ly", "nghiep vu", "kinh doanh"],
        },
        "data_analytics": {
            "label": "Phân tích dữ liệu kinh tế",
            "icon": "insights",
            "desc": "Economic data analysis, statistics, decision support",
            "keywords": ["phan tich", "thong ke", "du lieu", "kinh te luong", "toan", "bao cao", "ho tro quyet dinh"],
        },
    },
    "Công nghệ thông tin Địa học": {
        "gis_dev": {
            "label": "Phát triển GIS / Bản đồ số",
            "icon": "map",
            "desc": "GIS application development, web mapping, spatial databases",
            "keywords": ["gis", "dia hoc", "thong tin dia ly", "ban do", "khong gian", "he thong thong tin dia ly"],
        },
        "spatial_analysis": {
            "label": "Phân tích không gian / Viễn thám",
            "icon": "satellite_alt",
            "desc": "Remote sensing, spatial analysis, geospatial data science",
            "keywords": ["vien tham", "anh ve tinh", "phan tich khong gian", "mo hinh hoa", "thi giac may tinh", "du lieu khong gian"],
        },
        "geospatial_software": {
            "label": "Phần mềm địa không gian",
            "icon": "layers",
            "desc": "Geospatial software engineering, cloud GIS, IoT+location",
            "keywords": ["lap trinh", "phan mem", "web", "he thong thong tin", "dam may", "iot", "dia hoc"],
        },
    },
}


def _get_spec_tracks(specialization: str | None) -> dict[str, dict]:
    """Return the sub-directions for the given specialization, falling back to TRACKS."""
    if specialization and specialization in SPECIALIZATION_TRACKS:
        return SPECIALIZATION_TRACKS[specialization]
    return TRACKS


def _course_spec_track_score(course_name: str, sub_direction: str, spec_tracks: dict[str, dict]) -> float:
    """Score 0..1 how well a course name matches a given sub-direction's keywords."""
    track = spec_tracks.get(sub_direction)
    if not track:
        return 0.0
    normalized = _normalize_text(course_name)
    hits = sum(1 for kw in track["keywords"] if kw in normalized)
    return min(1.0, hits / max(1, len(track["keywords"]) * 0.3))

# Official curriculum semester position for each course (1-9).
# Common core (HK1-HK6) is the same across all specializations.
# HK7-HK9 are specialization-specific.
CURRICULUM_ORDER: dict[str, int] = {
    # ── HK 1 ────────────────────────────────────────────────────────────────
    "7010120": 1, "7080514": 1, "7010102": 1, "7010601": 1,
    "7010103": 1, "7010701": 1, "7020105": 1,
    # ── HK 2 ────────────────────────────────────────────────────────────────
    "7010111": 2, "7010204": 2, "7010202": 2, "7010602": 2,
    "7010104": 2, "7010702": 2, "7020302": 2, "7080208": 2,
    # ── HK 3 ────────────────────────────────────────────────────────────────
    "7080112": 3, "7080216": 3, "7080207": 3, "7010304": 3,
    "7080712": 3, "7010703": 3, "7020202": 3,
    # ── HK 4 ────────────────────────────────────────────────────────────────
    "7080211": 4, "7080717": 4, "7080206": 4, "7080512": 4,
    "7020201": 4,
    # ── HK 5 ────────────────────────────────────────────────────────────────
    "7080116": 5, "7080111": 5, "7080713": 5, "7080703": 5,
    "7080509": 5, "7020303": 5,
    "7300103": 5, "7300104": 5,  # QPAN HK5
    # ── HK 6 ────────────────────────────────────────────────────────────────
    "7080517": 6, "7080122": 6, "7080113": 6, "7080626": 6,
    "7020104": 6,
    "7300202": 6, "7300203": 6,  # QPAN HK6
    # ── HK 7 - Specialization specific ──────────────────────────────────────
    # Cơ sở ngành CHUNG (mọi CN đều học) — KHÔNG cho vào _SPEC_HK7_PLUS
    "7080504": 7,                 # Điện toán đám mây và ứng dụng (chung HK7)
    # Khoa học máy tính (KHMT)
    "7080508": 7, "7080515": 7,
    # Công nghệ thông tin địa học (CNTTDH)
    "7080313": 7, "7050303": 7,
    # Tin học kinh tế (THKT)
    "7080633": 7, "7080616": 7,
    # Mạng máy tính (MMT)
    "7080721": 7,
    # Hệ thống thông tin (HTTT) — per CTDT_CHUAN.md L481-482: 7080212+7080213 ở HK7
    "7080212": 7, "7080213": 7,   # 7080212=HT phân tán, 7080213=Học máy thống kê
    # Công nghệ phần mềm (CNPM)
    "7080104": 7, "7080108": 7, "7080114": 7,
    # ── HK 8 ────────────────────────────────────────────────────────────────
    # KHMT
    "7080510": 8, "7080506": 8,
    # CNTTDH — per CTDT_CHUAN.md L564 + bug log L659: HK8 phải có 7080309 + 7080403
    "7080309": 8, "7080403": 8,   # 7080309=HT CSDL không gian, 7080403=Đồ án CNTTDH
    # THKT
    "7080638": 8, "7080603": 8,
    # MMT
    "7080728": 8, "7080720": 8, "7080729": 8,
    # HTTT — per CTDT_CHUAN.md L483-484: 7080204+7080210 ở HK8
    "7080204": 8, "7080210": 8,   # 7080204=Các hệ cơ sở tri thức, 7080210=Đồ án HTTT
    # CNPM
    "7080102": 8, "7080106": 8,   # 7080102=Chuyên đề, 7080106=Đồ án CNPM
    # ── HK 9 - Thực tập & Đồ án tốt nghiệp ─────────────────────────────────
    "7080513": 9, "7080519": 9,   # KHMT
    "7080311": 9, "7080314": 9,   # CNTTDH (7080311=ĐATN CNTTDH, 7080314=TTTN CNTTDH)
    "7080617": 9, "7080604": 9,   # THKT
    "7080715": 9, "7080723": 9,   # MMT
    "7080224": 9, "7080218": 9,   # HTTT
    "7080119": 9, "7080110": 9,   # CNPM
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


def score10_to_score4(score10: float | None) -> float | None:
    """Public helper: map a score10 value to GPA-4 scale per VN convention.

    Used by simulator endpoints where we don't have a UserGrade row yet.
    """
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


def letter_from_score10(score10: float | None) -> str:
    if score10 is None:
        return "?"
    if score10 >= 9.0:  return "A+"
    if score10 >= 8.5:  return "A"
    if score10 >= 8.0:  return "B+"
    if score10 >= 7.0:  return "B"
    if score10 >= 6.5:  return "C+"
    if score10 >= 5.5:  return "C"
    if score10 >= 5.0:  return "D+"
    if score10 >= 4.0:  return "D"
    return "F"


def classify_gpa4(gpa4: float | None) -> str:
    if gpa4 is None:
        return "Chưa đủ dữ liệu"
    if gpa4 >= 3.6: return "Xuất sắc"
    if gpa4 >= 3.2: return "Giỏi"
    if gpa4 >= 2.5: return "Khá"
    if gpa4 >= 2.0: return "Trung bình"
    return "Yếu"


def _score4_from_grade(grade: models.UserGrade) -> float | None:
    score4 = _to_float(grade.score4)
    if score4 is not None:
        return score4
    return score10_to_score4(_to_float(grade.score10))


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
    return round(numerator / denominator, 2)


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


# ── Caches ────────────────────────────────────────────────────────────────────
_LLM_CACHE_TTL = 300  # seconds — LLM recommendation results cached 5 minutes per user
_llm_rec_cache: dict[str, dict] = {}  # { cache_key: { items, ai_ranked, ts } }

_DEFAULT_GRADUATION_THRESHOLD = 153.0
INTERNSHIP_REMAINING_BUFFER = 6.0  # non-special credits allowed to remain when starting internship

_DEFAULT_ACADEMIC_THRESHOLDS = {
    "internship_min_credits": 90.0,
    "thesis_min_credits": 130.0,
    "thesis_min_gpa4": 2.0,
}
_academic_thresholds_cache: dict[str, float] | None = None


def _get_academic_thresholds(db: Session) -> dict[str, float]:
    """Đọc 3 ngưỡng học vụ (TT DN, ĐATN TC, ĐATN GPA) từ SystemConfig với fallback default."""
    global _academic_thresholds_cache
    if _academic_thresholds_cache is not None:
        return _academic_thresholds_cache
    result = dict(_DEFAULT_ACADEMIC_THRESHOLDS)
    rows = db.query(models.SystemConfig).filter(
        models.SystemConfig.key.in_(list(_DEFAULT_ACADEMIC_THRESHOLDS.keys()))
    ).all()
    for cfg in rows:
        try:
            result[cfg.key] = float(cfg.value)
        except (ValueError, TypeError):
            pass
    _academic_thresholds_cache = result
    return result


def _invalidate_academic_thresholds_cache() -> None:
    global _academic_thresholds_cache
    _academic_thresholds_cache = None

# ── Course difficulty stats cache (aggregate from all students' grades) ────────
import time as _time
_difficulty_stats_cache: dict[str, dict] | None = None
_difficulty_stats_ts: float = 0.0
_DIFFICULTY_STATS_TTL = 1800  # 30 minutes


def _build_difficulty_stats(db: Session) -> dict[str, dict]:
    """Compute pass_rate, avg_score10, std_dev for every course from ALL students."""
    from math import sqrt
    all_grades = db.query(models.UserGrade).all()
    by_code: dict[str, list[models.UserGrade]] = defaultdict(list)
    for g in all_grades:
        by_code[g.course_code].append(g)

    stats: dict[str, dict] = {}
    for code, grades in by_code.items():
        total = len(grades)
        passed = sum(1 for g in grades if g.passed)
        scores = [s for g in grades for s in [_score10_from_grade(g)] if s is not None]
        avg = sum(scores) / len(scores) if scores else None
        std = sqrt(sum((s - avg) ** 2 for s in scores) / len(scores)) if avg and len(scores) > 1 else None
        stats[code] = {
            "total_students": total,
            "pass_rate": round(passed / total, 3) if total else None,
            "avg_score10": round(avg, 2) if avg is not None else None,
            "std_dev": round(std, 2) if std is not None else None,
        }
    return stats


def _get_difficulty_stats(db: Session) -> dict[str, dict]:
    global _difficulty_stats_cache, _difficulty_stats_ts
    if _difficulty_stats_cache is None or (_time.time() - _difficulty_stats_ts) > _DIFFICULTY_STATS_TTL:
        _difficulty_stats_cache = _build_difficulty_stats(db)
        _difficulty_stats_ts = _time.time()
    return _difficulty_stats_cache


# ─── Reference-data TTL caches ────────────────────────────────────────────────
# Course, CourseElectiveGroup, CoursePrerequisite, CourseSkill change only when
# admin imports curriculum (rare). Cache them at module level for 5 minutes to
# eliminate ~5 redundant full-table SELECTs per recommendation request.
_REF_CACHE_TTL = 60  # seconds — short enough that admin curriculum edits surface within a minute
_ref_cache: dict[str, tuple[float, object]] = {}


def _ref_cached(key: str, loader):
    """Return cached value or invoke loader and cache for _REF_CACHE_TTL seconds."""
    now = _time.time()
    hit = _ref_cache.get(key)
    if hit and (now - hit[0]) < _REF_CACHE_TTL:
        return hit[1]
    val = loader()
    _ref_cache[key] = (now, val)
    return val


def _invalidate_ref_cache(key: str | None = None) -> None:
    """Call after admin imports/edits curriculum to force fresh fetch."""
    if key is None:
        _ref_cache.clear()
    else:
        _ref_cache.pop(key, None)


def _get_all_courses_cached(db: Session) -> list[models.Course]:
    return _ref_cached(
        "courses_all",
        lambda: db.query(models.Course).order_by(models.Course.course_code.asc()).all(),
    )


def _get_all_elective_mappings_cached(db: Session) -> list[models.CourseElectiveGroup]:
    return _ref_cached(
        "elective_groups_all",
        lambda: db.query(models.CourseElectiveGroup).all(),
    )


def _get_all_prereqs_cached(db: Session) -> list[models.CoursePrerequisite]:
    return _ref_cached(
        "prereqs_all",
        lambda: db.query(models.CoursePrerequisite).all(),
    )


def _get_all_course_skills_cached(db: Session) -> list[models.CourseSkill]:
    return _ref_cached(
        "course_skills_all",
        lambda: db.query(models.CourseSkill).all(),
    )


def invalidate_difficulty_stats_cache() -> None:
    global _difficulty_stats_cache
    _difficulty_stats_cache = None


# ── Critical path: transitive unlock count ─────────────────────────────────────
def _compute_unlock_scores(
    remaining_codes: set[str],
    prereq_map: dict[str, list[str]],
) -> dict[str, int]:
    """For each remaining course, count how many other remaining courses it unlocks transitively."""
    # Reverse map: which remaining courses list each code as prereq
    dependents_of: dict[str, set[str]] = defaultdict(set)
    for dep_code, prereqs in prereq_map.items():
        if dep_code in remaining_codes:
            for p in prereqs:
                dependents_of[p].add(dep_code)

    memo: dict[str, int] = {}

    def _count(code: str, visiting: frozenset) -> int:
        if code in memo:
            return memo[code]
        direct = dependents_of.get(code, set()) & remaining_codes - visiting
        total = len(direct)
        new_visiting = visiting | direct
        for dep in direct:
            total += _count(dep, new_visiting)
        memo[code] = total
        return total

    return {code: _count(code, frozenset()) for code in remaining_codes}


# ── Prereq performance: how well student did in prerequisites ─────────────────
def _prereq_performance(
    course_code: str,
    prereq_map: dict[str, list[str]],
    best_grades: dict[str, models.UserGrade],
) -> tuple[float | None, str | None]:
    """Return (avg_score_in_prereqs, warning_message).
    None if no prereq data available."""
    prereqs = prereq_map.get(course_code, [])
    scores = []
    for p in prereqs:
        g = best_grades.get(p)
        if g and g.passed:
            s = _score10_from_grade(g)
            if s is not None:
                scores.append(s)
    if not scores:
        return None, None
    avg = sum(scores) / len(scores)
    if avg < 5.5:
        return avg, f"Điểm tiên quyết của bạn chỉ {avg:.1f}/10 — nên ôn lại kiến thức nền trước khi đăng ký."
    if avg < 6.5:
        return avg, f"Điểm tiên quyết {avg:.1f}/10 — môn này sẽ đòi hỏi nỗ lực đáng kể."
    return avg, None

# Cache graduation threshold — chỉ query DB 1 lần, reset khi giá trị thay đổi
_grad_threshold_cache: float | None = None

def _get_graduation_threshold(db: Session) -> float:
    global _grad_threshold_cache
    if _grad_threshold_cache is not None:
        return _grad_threshold_cache
    cfg = db.query(models.SystemConfig).filter(models.SystemConfig.key == "graduation_credit_threshold").first()
    if cfg:
        try:
            _grad_threshold_cache = float(cfg.value)
            return _grad_threshold_cache
        except (ValueError, TypeError):
            pass
    _grad_threshold_cache = _DEFAULT_GRADUATION_THRESHOLD
    return _grad_threshold_cache


def _invalidate_graduation_threshold_cache() -> None:
    global _grad_threshold_cache
    _grad_threshold_cache = None


def _find_internship_thesis(
    courses: list[models.Course],
    specialization: str | None,
) -> tuple[models.Course | None, models.Course | None]:
    """Return (internship_course, thesis_course) for the user's specialisation.

    Accepts courses that belong exclusively to the user's specialization OR
    courses with no specialization requirement (required_specialization=None),
    so shared internship/thesis courses are also detected.
    """
    internship = None
    thesis = None
    for c in courses:
        # Skip courses locked to a DIFFERENT specialization
        if c.required_specialization and specialization and c.required_specialization != specialization:
            continue
        n = _normalize_text(c.course_name)
        if "thuc tap" in n and "tot nghiep" in n:
            # Prefer spec-specific over shared; stop once we have one
            if internship is None or (c.required_specialization == specialization and internship.required_specialization != specialization):
                internship = c
        elif "do an" in n and "tot nghiep" in n:
            if thesis is None or (c.required_specialization == specialization and thesis.required_specialization != specialization):
                thesis = c
    return internship, thesis


def _build_snapshot(db: Session, user_id: int, specialization: str | None = None, simulate_failed: list | None = None) -> StudentSnapshot:
    all_courses = _get_all_courses_cached(db)
    all_elective_mappings = _get_all_elective_mappings_cached(db)
    if specialization:
        # Courses in the user's elective pools (their spec + "Chung")
        user_elective_codes: set[str] = {
            m.course_code for m in all_elective_mappings
            if m.specialization == specialization or m.specialization == "Chung"
        }
        # Courses that exist in OTHER specializations' elective pools but NOT in user's
        other_elective_codes: set[str] = {
            m.course_code for m in all_elective_mappings
            if m.specialization != specialization and m.specialization != "Chung"
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
        # spec=None (SV năm 1-2 chưa chọn CN) — chỉ các môn CHUNG (đại cương + cơ sở ngành):
        #   - required_specialization IS NULL
        #   - không nằm trong elective pool của bất kỳ CN cụ thể nào (chỉ giữ "Chung")
        #   - không bị M2M ràng buộc 1 CN cụ thể
        spec_specific_elective_codes: set[str] = {
            m.course_code for m in all_elective_mappings
            if m.specialization != "Chung"
        }
        m2m_spec_tied_codes: set[str] = {
            r.course_code for r in db.query(models.CourseSpecialization).all()
        }
        courses = [
            c for c in all_courses
            if c.required_specialization is None
            and c.course_code not in spec_specific_elective_codes
            and c.course_code not in m2m_spec_tied_codes
        ]
    course_by_code = {c.course_code: c for c in courses}

    grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()
    best_grades = _select_best_grade_per_course(grades)
    completed_codes = {code for code, g in best_grades.items() if g.passed}
    if simulate_failed:
        completed_codes -= set(simulate_failed)

    # Conditional courses (e.g. Tiếng Anh tăng cường 7010610) — chỉ trường gán cho SV
    # có TA THPT < 5. Nếu SV không có grade ghi nhận → KHÔNG đẩy vào remaining_courses
    # để tránh hệ thống tự gợi ý sai. Nếu SV đã có grade (do trường gán) → giữ.
    _CONDITIONAL_COURSES = {"7010610"}  # TA tăng cường 1
    _has_grade_codes = set(best_grades.keys())
    courses = [
        c for c in courses
        if c.course_code not in _CONDITIONAL_COURSES or c.course_code in _has_grade_codes
    ]
    course_by_code = {c.course_code: c for c in courses}

    total_credits, earned_credits = _calc_credits(db, course_by_code, completed_codes, specialization)

    weighted_10: list[tuple[float, float]] = []
    weighted_4: list[tuple[float, float]] = []
    for code, grade in best_grades.items():
        if not grade.passed or code not in course_by_code:
            continue
        course = course_by_code[code]
        if not _counts_toward_credits(course):
            continue
        credits = _course_credits(course)
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
    group_mappings = _get_all_elective_mappings_cached(db)
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
    """Estimate remaining terms based on past term credit velocity.

    Uses official earned_credits (authoritative TC from transcript) divided by
    number of unique terms studied — avoids mismatch with partial DB coverage.
    Remaining credits are computed against graduation threshold, not full CTDT total.
    """
    grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()

    # Count unique terms where student had at least one grade (passed or not)
    unique_terms = {g.term.strip() for g in grades if g.term and g.term.strip()}
    # But only count terms where they passed something (productive terms)
    productive_terms = {
        g.term.strip() for g in grades
        if g.passed and g.term and g.term.strip()
        and "HK3" not in g.term  # exclude summer terms from velocity calc
    }
    terms_studied = len(productive_terms) if productive_terms else len(unique_terms)

    # Use official earned_credits as the authoritative basis (avoids partial DB coverage issue)
    earned = snapshot.earned_credits  # already overridden with official_tc if available

    # Remaining credits to graduation threshold (not total CTDT) for realistic estimate
    graduation_threshold = _get_graduation_threshold(db)
    remaining_credits = max(0.0, graduation_threshold - earned)

    if terms_studied > 0 and earned > 0:
        avg_credits_per_term = earned / terms_studied
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

    # Note: official_earned_credits đã DROP ở refactor 2026-05-05.
    # earned_credits giờ luôn tính từ user_grades (passed=True) trong _build_snapshot.
    official_tc = None
    earned_credits_for_spec = snapshot.earned_credits

    from sqlalchemy import or_
    if specialization:
        rules = db.query(models.ElectiveRule).filter(
            or_(
                models.ElectiveRule.specialization == specialization,
                models.ElectiveRule.specialization == "Chung",
            )
        ).all()
    else:
        # SV chưa có CN → chỉ trả rules "Chung" (chung cho mọi CN).
        # Không trả 6× rules per spec để frontend không phải dedupe.
        # Khi SV chốt CN, sẽ thấy đầy đủ rules của CN đó + Chung.
        rules = db.query(models.ElectiveRule).filter(
            models.ElectiveRule.specialization == "Chung"
        ).all()
    elective_groups = _elective_progress(db, snapshot, rules)

    # Build elective group remaining map to filter out elective-extra courses
    elective_group_remaining = _elective_group_remaining(
        db, snapshot.course_by_code, snapshot.completed_codes, specialization
    )
    if specialization:
        all_elective_mappings = db.query(models.CourseElectiveGroup).filter(
            or_(
                models.CourseElectiveGroup.specialization == specialization,
                models.CourseElectiveGroup.specialization == "Chung",
            )
        ).all()
    else:
        # No specialization selected — still identify shared "Chung" elective courses
        all_elective_mappings = db.query(models.CourseElectiveGroup).filter(
            models.CourseElectiveGroup.specialization == "Chung"
        ).all()
    course_to_group: dict[str, tuple] = {
        m.course_code: (m.program_code, m.specialization, m.group_type)
        for m in all_elective_mappings
    }

    def _is_elective_extra(course: models.Course) -> bool:
        key = course_to_group.get(course.course_code)
        if key is None:
            return False
        return elective_group_remaining.get(key, 0.0) <= 0.0

    # Identify failed elective courses — these can be substituted by other courses in the
    # same elective group, so they should NOT appear as individual items in remaining_courses.
    # The group's credit quota (via _elective_group_remaining) already accounts for the
    # shortfall, so the student can register any 2 other group-B courses instead of retaking
    # the one that failed.
    failed_elective_codes: set[str] = {
        code
        for code, g in snapshot.best_grades.items()
        if not g.passed and code in course_to_group
    }

    all_incomplete = [c for c in snapshot.courses if c.course_code not in snapshot.completed_codes]
    remaining_courses = [
        c for c in all_incomplete
        if not _is_elective_extra(c)
        and c.course_code not in failed_elective_codes
        and _counts_toward_credits(c)
    ]
    remaining_courses.sort(key=lambda c: c.course_code)

    _grad_threshold_for_pct = _get_graduation_threshold(db)
    completion_percent = (
        min(100.0, earned_credits_for_spec / _grad_threshold_for_pct * 100.0)
        if _grad_threshold_for_pct > 0 else 0.0
    )

    grad = _graduation_estimate(db, user_id, snapshot)

    # Compute human-readable graduation semester from estimated_terms_remaining
    estimated_graduation: str | None = None
    estimated_graduation_detail: str | None = None
    _est_terms = grad.get("estimated_terms_remaining")
    if _est_terms is not None and _est_terms >= 0:
        import math as _math2, re as _re2, datetime as _dt
        _terms_ceil = _math2.ceil(_est_terms) if _est_terms > 0 else 0
        try:
            _cfg = db.query(models.SystemConfig).filter(models.SystemConfig.key == "active_semester").first()
            _active_sem = (_cfg.value or "").strip() if _cfg else ""
            _curr_hk: int | None = None
            _curr_year: int | None = None
            if _active_sem:
                _m = _re2.search(r'HK\s*(\d+)[/\-](\d{4})', _active_sem, _re2.IGNORECASE)
                if not _m:
                    _m = _re2.search(r'H[oọ][cọ]\s*k[yỳ]\s+(\d+).*?(\d{4})', _active_sem, _re2.IGNORECASE)
                if _m:
                    _curr_hk = int(_m.group(1))
                    _curr_year = int(_m.group(2))
            if _curr_hk is None:
                _now = _dt.date.today()
                _curr_hk = 1 if _now.month >= 9 else 2
                _curr_year = _now.year if _now.month >= 9 else _now.year - 1
            _curr_idx = _curr_year * 2 + (_curr_hk - 1)
            _grad_idx = _curr_idx + _terms_ceil
            _grad_hk = (_grad_idx % 2) + 1
            _grad_year = _grad_idx // 2
            if _terms_ceil == 0:
                estimated_graduation = "Có thể tốt nghiệp kỳ này"
                estimated_graduation_detail = "Đã đủ điều kiện"
            else:
                estimated_graduation = f"HK{_grad_hk}/{_grad_year}-{_grad_year + 1}"
                if _terms_ceil <= 2:
                    estimated_graduation_detail = f"~{_terms_ceil} kỳ nữa"
                elif _terms_ceil <= 4:
                    estimated_graduation_detail = f"~{_terms_ceil} kỳ nữa"
                else:
                    estimated_graduation_detail = f"~{_terms_ceil} kỳ, cần tăng tốc"
        except Exception:
            pass

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

    academic_thresholds = _get_academic_thresholds(db)
    avg_gpa4 = snapshot.avg_score4 if snapshot.avg_score4 is not None else 0.0
    internship_eligible = (
        internship_course is not None
        and not internship_done
        and remaining_non_special <= INTERNSHIP_REMAINING_BUFFER
        and snapshot.earned_credits >= academic_thresholds["internship_min_credits"]
    )
    thesis_eligible = (
        thesis_course is not None
        and not thesis_done
        and internship_done
        and snapshot.earned_credits >= academic_thresholds["thesis_min_credits"]
        and avg_gpa4 >= academic_thresholds["thesis_min_gpa4"]
    )
    graduation_threshold = _get_graduation_threshold(db)
    graduation_ready = snapshot.earned_credits >= graduation_threshold

    # --- Prerequisite issues ---
    from collections import defaultdict as _dd
    prereqs = _get_all_prereqs_cached(db)
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
        "earned_credits": earned_credits_for_spec,
        "official_earned_credits": official_tc,
        "completion_percent": round(completion_percent, 2),
        "avg_score10": round(snapshot.avg_score10, 2) if snapshot.avg_score10 is not None else None,
        "avg_score4": round(snapshot.avg_score4, 2) if snapshot.avg_score4 is not None else None,
        "specialization": specialization,
        "elective_groups": elective_groups,
        "remaining_course_items": [
            {
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": _course_credits(c),
                "is_elective": c.course_code in course_to_group,
                "elective_group_type": course_to_group[c.course_code][2] if c.course_code in course_to_group else None,
                "required_specialization": c.required_specialization,
            }
            for c in remaining_courses
        ],
        "terms_studied": grad["terms_studied"],
        "avg_credits_per_term": grad["avg_credits_per_term"],
        "estimated_terms_remaining": grad["estimated_terms_remaining"],
        "estimated_graduation": estimated_graduation,
        "estimated_graduation_detail": estimated_graduation_detail,
        "required_score10_for_target": round(required_score10, 1) if required_score10 is not None else None,
        "target_gpa": target_gpa,
        "graduation_threshold": graduation_threshold,
        "graduation_ready": graduation_ready,
        "internship_eligible": internship_eligible,
        "internship_done": internship_done,
        "thesis_eligible": thesis_eligible,
        "thesis_done": thesis_done,
        "prereq_issues": prereq_issues,
        # All failures are included; is_elective flag lets the frontend show the right message.
        # Required failures: must retake. Elective failures: can substitute with another course.
        # In-progress courses (no score yet) are excluded — passed=False + no score = currently studying.
        "failed_courses": [
            {
                "course_code": g.course_code,
                "course_name": (snapshot.course_by_code[g.course_code].course_name
                                if g.course_code in snapshot.course_by_code else g.course_code),
                "is_elective": g.course_code in course_to_group,
            }
            for g in snapshot.best_grades.values()
            if not g.passed
            and (g.score10 is not None or g.score4 is not None or g.letter is not None)
        ],
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


def _build_spec_track_strengths(snapshot: StudentSnapshot, spec_tracks: dict[str, dict]) -> dict[str, float]:
    """Build weighted-average score per sub-direction using specialization-specific keywords."""
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
        course_name = snapshot.course_by_code[code].course_name
        for sub_dir in spec_tracks:
            hit = _course_spec_track_score(course_name, sub_dir, spec_tracks)
            if hit > 0:
                score_bucket[sub_dir].append((score10, credits))

    strengths: dict[str, float] = {}
    for sub_dir, values in score_bucket.items():
        avg = _weighted_average(values)
        if avg is not None:
            strengths[sub_dir] = avg
    return strengths


def _build_track_reasoning(
    snapshot: StudentSnapshot,
    track_strengths: dict[str, float],
    preferred_track: str | None,
    career_goal: str | None,
    spec_tracks: dict[str, dict] | None = None,
) -> str:
    """Return a Vietnamese sentence explaining why this track was chosen."""
    # Resolve track label from spec_tracks or fallback to TRACKS
    _all_tracks = spec_tracks if spec_tracks else TRACKS
    track_label_map = {k: v["label"] for k, v in _all_tracks.items()}

    # If user explicitly chose a career goal that is a valid sub-direction key
    if career_goal and career_goal in track_label_map:
        goal_label = track_label_map[career_goal]
        prefix = f"Bạn đã chọn định hướng **{goal_label}**."
        if not preferred_track or not track_strengths:
            return prefix
    else:
        prefix = None

    if not track_strengths or not preferred_track:
        return prefix or "Chưa đủ dữ liệu để xác định định hướng — hệ thống gợi ý theo nền tảng chung."

    # Find top contributing courses for the preferred track
    contributing: list[tuple[str, float]] = []
    for code, grade in snapshot.best_grades.items():
        if not grade.passed or code not in snapshot.course_by_code:
            continue
        course = snapshot.course_by_code[code]
        if spec_tracks:
            hit = _course_spec_track_score(course.course_name, preferred_track, spec_tracks)
            matched = hit > 0
        else:
            matched = preferred_track in _course_tracks(course.course_name)
        if matched:
            s10 = _score10_from_grade(grade)
            if s10 is not None:
                contributing.append((course.course_name, s10))
    contributing.sort(key=lambda x: -x[1])

    strength_val = track_strengths.get(preferred_track)
    track_label = track_label_map.get(preferred_track, preferred_track)

    parts: list[str] = []
    if strength_val is not None:
        parts.append(f"điểm TB nhóm môn này {strength_val:.1f}/10")
    if contributing:
        top = contributing[:3]
        course_list = ", ".join(f"{n[:18]} ({s:.1f})" for n, s in top)
        parts.append(f"dựa trên: {course_list}")

    if prefix:
        if parts:
            return f"{prefix} Điểm số ủng hộ hướng này: {'; '.join(parts)}."
        return prefix

    if parts:
        return f"Hệ thống phát hiện bạn học tốt nhóm **{track_label}** ({'; '.join(parts)})."
    return f"Gợi ý theo hướng **{track_label}** dựa trên môn học đã hoàn thành."


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


def build_recommendations(
    db: Session,
    user_id: int,
    limit: int = 5,
    available_course_codes: set | None = None,
    career_goal: str | None = None,
) -> dict:
    safe_limit = max(1, min(int(limit), 20))
    user = db.query(models.User).filter(models.User.id == user_id).first()
    specialization = user.specialization if user else None
    difficulty_pref = None  # Deprecated 2026-05-05 — column dropped
    # Deprecated 2026-05-05: user.career_goal dropped — career goal chỉ qua param truyền vào
    pass
    snapshot = _build_snapshot(db, user_id, specialization=specialization)

    # Note: official_earned_credits đã DROP — earned_credits tính live từ grades.

    # Prerequisites map (cached)
    prereqs = _get_all_prereqs_cached(db)
    prereq_map: dict[str, list[str]] = defaultdict(list)
    for p in prereqs:
        prereq_map[p.course_code].append(p.prerequisite_code)

    # Elective group membership & remaining credits needed
    elective_group_remaining = _elective_group_remaining(
        db, snapshot.course_by_code, snapshot.completed_codes, specialization
    )
    _all_elective_groups = _get_all_elective_mappings_cached(db)
    all_elective_mappings = [
        m for m in _all_elective_groups
        if specialization and (m.specialization == specialization or m.specialization == "Chung")
    ]
    course_to_group: dict[str, tuple] = {}
    for m in all_elective_mappings:
        course_to_group[m.course_code] = (m.program_code, m.specialization, m.group_type)

    # Build set of ALL elective codes (any spec) so we can filter them for no-spec users
    _all_elective_codes: set[str] = {m.course_code for m in _all_elective_groups}

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
    _at = _get_academic_thresholds(db)
    _gpa4 = snapshot.avg_score4 if snapshot.avg_score4 is not None else 0.0
    internship_eligible = (
        internship_course is not None and not internship_done
        and remaining_non_special <= INTERNSHIP_REMAINING_BUFFER
        and snapshot.earned_credits >= _at["internship_min_credits"]
    )
    thesis_eligible = (
        thesis_course is not None and not thesis_done and bool(internship_done)
        and snapshot.earned_credits >= _at["thesis_min_credits"]
        and _gpa4 >= _at["thesis_min_gpa4"]
    )

    remaining_courses = [
        c for c in snapshot.courses
        if c.course_code not in snapshot.completed_codes and _counts_toward_credits(c)
    ]

    # ── Pre-compute intelligent scoring data ──────────────────────────────────
    all_difficulty_stats = _get_difficulty_stats(db)
    remaining_codes_set = {c.course_code for c in remaining_courses}
    unlock_scores = _compute_unlock_scores(remaining_codes_set, prereq_map)

    # ── Specialization-aware track strengths ──────────────────────────────────
    spec_tracks = _get_spec_tracks(specialization)
    track_strengths = _build_spec_track_strengths(snapshot, spec_tracks)
    preferred_track = max(track_strengths.items(), key=lambda x: x[1])[0] if track_strengths else None

    # Career goal: now a sub-direction key for the current specialization
    if career_goal and career_goal in spec_tracks:
        preferred_track = career_goal
    elif career_goal == "general":
        preferred_track = None

    baseline_ability = snapshot.avg_score10 if snapshot.avg_score10 is not None else 6.5

    # Deprecated 2026-05-05: user.career_skills field dropped — skill overlap disabled
    user_career_skills: set[str] = set()

    course_skill_map: dict[str, list[tuple[str, float]]] = {}
    if user_career_skills:
        for cs in _get_all_course_skills_cached(db):
            course_skill_map.setdefault(cs.course_code, []).append(
                (cs.skill_code, float(cs.weight))
            )

    # ── Peer ratings: avg star per course (signal "môn này được SV đánh giá tốt") ──
    from sqlalchemy import func as _sf
    rating_rows = db.query(
        models.CourseRating.course_code,
        _sf.avg(models.CourseRating.rating).label("avg_r"),
        _sf.count(models.CourseRating.id).label("count_r"),
    ).group_by(models.CourseRating.course_code).having(
        _sf.count(models.CourseRating.id) >= 3
    ).all()
    rating_map: dict[str, tuple[float, int]] = {
        r.course_code: (float(r.avg_r), int(r.count_r)) for r in rating_rows
    }

    # Pre-compute context for specific reasons
    remaining_required_tc = sum(
        _course_credits(c) for c in remaining_courses
        if c.course_code not in course_to_group
        and c.course_code not in (internship_code, thesis_code)
    )
    # prereq_needed_by[code] = list of course names that need `code` as prereq
    prereq_needed_by: dict[str, list[str]] = defaultdict(list)
    for dep_code, prereq_list in prereq_map.items():
        dep_course = snapshot.course_by_code.get(dep_code)
        if dep_course and dep_code not in snapshot.completed_codes:
            for p in prereq_list:
                if p not in snapshot.completed_codes:
                    prereq_needed_by[p].append(dep_course.course_name)

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
        # BB = môn bắt buộc (không thuộc nhóm tự chọn, không phải TT/ĐATN).
        # Theo CLAUDE.md §5.9, BB KHÔNG được rerank theo skill/track/peer — CTĐT cố định.
        is_compulsory_bb = (group_key is None and not is_thesis and not is_internship)

        # Skip elective courses from groups that are already complete
        if is_elective_extra:
            continue

        # Skip courses locked to a specialization the user hasn't chosen
        if course.required_specialization and course.required_specialization != specialization:
            continue

        # Without a chosen specialization: skip elective-pool courses entirely
        # (they'll appear once the student picks a spec)
        if not specialization and code in _all_elective_codes and group_key is None:
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

        reason_codes: list[str] = ["NOT_COMPLETED"]
        reasons: list[str] = []

        # ── Difficulty stats ──────────────────────────────────────────────────
        dstat = all_difficulty_stats.get(code, {})
        course_avg10 = dstat.get("avg_score10")
        course_pass_rate = dstat.get("pass_rate")
        # Dùng default nếu chưa có đủ dữ liệu (< 5 sinh viên)
        _min_samples = 5
        if dstat.get("total_students", 0) < _min_samples:
            course_avg10 = None
            course_pass_rate = None

        # ── Prereq performance ────────────────────────────────────────────────
        prereq_avg, prereq_warn = _prereq_performance(code, prereq_map, snapshot.best_grades)

        # ── Unlock count ──────────────────────────────────────────────────────
        unlock_count = unlock_scores.get(code, 0)
        max_unlock = max(unlock_scores.values(), default=1)

        # ── Track alignment ───────────────────────────────────────────────────
        # CLAUDE.md §5.9: BB không có "track alignment" có ý nghĩa — bỏ qua cho BB.
        track_hit = bool(
            not is_compulsory_bb
            and preferred_track
            and _course_spec_track_score(course.course_name, preferred_track, spec_tracks) > 0
        )

        # ── Semester availability ─────────────────────────────────────────────
        available_this_term = True
        if available_course_codes is not None:
            available_this_term = code in available_course_codes

        # ════════════════════════════════════════════════════════════════════
        # RULE-BASED SCORE (0..1) — chuẩn hóa, dùng khi ML chưa sẵn sàng
        # Cũng được blend với ML score (50/50)
        # ════════════════════════════════════════════════════════════════════

        # 1. Ability fit (0..1)
        if course_pass_rate is not None and course_avg10 is not None:
            ability_gap = baseline_ability - course_avg10
            if course_pass_rate < 0.60:
                ability_score = _clamp(0.40 + ability_gap * 0.08, 0.0, 1.0)
                if course_pass_rate < 0.40:
                    reason_codes.append("HIGH_DIFFICULTY")
                    reasons.append(
                        f"Môn khó ({course_pass_rate*100:.0f}% qua) — "
                        f"GPA {baseline_ability:.1f}/10 của bạn "
                        f"{'phù hợp' if ability_gap >= 0 else 'cần chuẩn bị kỹ'}."
                    )
            elif course_pass_rate >= 0.85:
                if baseline_ability < 6.5:
                    ability_score = 0.85
                    reason_codes.append("FOUNDATION_BUILD")
                    reasons.append(
                        f"Môn nền tảng (TB {course_avg10:.1f}/10) — "
                        f"phù hợp để củng cố kiến thức trước các môn khó."
                    )
                else:
                    ability_score = 0.60
            else:
                ability_score = _clamp(0.62 + ability_gap * 0.04, 0.0, 1.0)
        else:
            ability_score = 0.58  # neutral default

        # Difficulty preference adjustment
        if difficulty_pref and course_pass_rate is not None:
            if difficulty_pref == "easy":
                # Boost high pass-rate courses, penalize hard ones
                if course_pass_rate >= 0.80:
                    ability_score = _clamp(ability_score + 0.12, 0.0, 1.0)
                elif course_pass_rate < 0.55:
                    ability_score = _clamp(ability_score - 0.12, 0.0, 1.0)
            elif difficulty_pref == "challenging":
                # Boost hard courses, penalize easy ones
                if course_pass_rate < 0.55:
                    ability_score = _clamp(ability_score + 0.12, 0.0, 1.0)
                elif course_pass_rate >= 0.80:
                    ability_score = _clamp(ability_score - 0.08, 0.0, 1.0)

        # 2. Track alignment (0..1) — CLAUDE.md §5.9: chỉ áp dụng cho TC
        if is_compulsory_bb:
            track_score = 0.5  # neutral cho BB (không personalize theo định hướng)
        else:
            has_any_track = any(
                _course_spec_track_score(course.course_name, sd, spec_tracks) > 0
                for sd in spec_tracks
            )
            track_score = 1.0 if track_hit else (0.50 if has_any_track else 0.30)

        # 3. Unlock value (0..1, log scale)
        unlock_score = (
            _clamp(log(1 + unlock_count) / max(0.01, log(2 + max_unlock)), 0.0, 1.0)
            if max_unlock > 0 else 0.0
        )

        # 4. Prereq readiness (0..1)
        prereq_score = _clamp(prereq_avg / 10.0, 0.0, 1.0) if prereq_avg else 0.70
        if prereq_warn:
            reason_codes.append("WEAK_PREREQ_PERF")
            reasons.append(prereq_warn)

        # 5. Skill match (0..1) — CLAUDE.md §5.9: chỉ áp dụng cho TC, BB là cố định
        skill_score = 0.0
        matched_skill_names: list[str] = []
        if not is_compulsory_bb and user_career_skills and code in course_skill_map:
            total_w = 0.0
            matched_w = 0.0
            for skill_code, weight in course_skill_map[code]:
                total_w += weight
                if skill_code in user_career_skills:
                    matched_w += weight
                    matched_skill_names.append(skill_code)
            skill_score = (matched_w / total_w) if total_w > 0 else 0.0

        # 6. Peer rating (0..1) — CLAUDE.md §5.9: signal chủ quan, chỉ áp dụng cho TC
        peer_rating, peer_count = rating_map.get(code, (None, 0))
        if peer_rating is not None and not is_compulsory_bb:
            # Map 1-5 sao → 0..1: (rating - 1) / 4
            peer_score = _clamp((peer_rating - 1.0) / 4.0, 0.0, 1.0)
        else:
            peer_score = 0.5  # neutral cho BB hoặc khi chưa đủ rating

        # Tổng hợp rule_score (weights: ability=0.22, track=0.20, unlock=0.20, prereq=0.10,
        #                              skill=0.13, peer=0.08, base=0.07)
        rule_score = (
            0.22 * ability_score
            + 0.20 * track_score
            + 0.20 * unlock_score
            + 0.10 * prereq_score
            + 0.13 * skill_score
            + 0.08 * peer_score
            + 0.07  # base bonus (mọi eligible course đều > 0)
        )

        # ════════════════════════════════════════════════════════════════════
        # PRIORITY FLOORS — ràng buộc tốt nghiệp ghi đè ML
        # ════════════════════════════════════════════════════════════════════
        priority_floor = 0.0
        failed_grade = snapshot.best_grades.get(code)
        is_retake = failed_grade and not failed_grade.passed and group_key is None

        if is_thesis:
            reason_codes.append("THESIS_READY")
            reasons.append("Bạn đủ điều kiện làm Đồ án tốt nghiệp.")
            priority_floor = 0.90
        elif is_internship:
            reason_codes.append("INTERNSHIP_READY")
            reasons.append("Bạn đủ điều kiện thực tập doanh nghiệp.")
            priority_floor = 0.85
        elif is_retake:
            reason_codes.append("RETAKE_NEEDED")
            reasons.append("Môn bắt buộc chưa đạt — cần học lại để đủ điều kiện tốt nghiệp.")
            priority_floor = 0.72
        elif group_key is None:
            reason_codes.append("REQUIRED")
            hk = course.typical_semester
            hk_note = f" (HK chuẩn: {hk})" if hk else ""
            reasons.append(f"Môn bắt buộc trong CTĐT{hk_note} — phải học để đủ TC tốt nghiệp.")
            # CLAUDE.md §5.9: BB ưu tiên theo HK chuẩn (sớm = cao hơn), KHÔNG personalize.
            # Floor đặt cao hơn TC thông thường để BB nổi lên trong list gợi ý.
            _hk_for_floor = hk if hk and 1 <= hk <= 9 else 5
            priority_floor = max(0.55, 0.74 - (_hk_for_floor - 1) * 0.022)
        else:
            reason_codes.append("ELECTIVE_NEEDED")
            _, gspec, gtype = group_key
            reasons.append(f"Cần thêm tín chỉ nhóm tự chọn {gtype} (còn thiếu {group_remaining:.0f} TC).")

        # Track alignment reason
        if track_hit:
            reason_codes.append("TRACK_ALIGNMENT")
            _track_label = spec_tracks[preferred_track]["label"]
            _track_score = track_strengths.get(preferred_track, 0.0)
            if career_goal and career_goal in spec_tracks:
                reasons.append(f"Thuộc nhóm {_track_label} — điểm TB nhóm này {_track_score:.1f}/10.")
            else:
                reasons.append(f"Nhóm {_track_label} — đây là nhóm môn bạn học tốt nhất ({_track_score:.1f}/10 TB).")

        # Unlock reason
        if unlock_count > 0:
            reason_codes.append("PREREQ_UNLOCK")
            if code in prereq_needed_by:
                dependents = prereq_needed_by[code]
                dep_preview = dependents[0][:25]
                suffix = f" (+{len(dependents)-1} môn khác)" if len(dependents) > 1 else ""
                reasons.append(f"Mở khóa {unlock_count} môn tiếp theo — tiên quyết của {dep_preview}{suffix}.")
            else:
                reasons.append(f"Hoàn thành để mở khóa {unlock_count} môn trong chuỗi học.")

        # Skill match reason
        if matched_skill_names:
            reason_codes.append("SKILL_MATCH")
            preview = ', '.join(matched_skill_names[:3])
            extra = f" (+{len(matched_skill_names)-3})" if len(matched_skill_names) > 3 else ""
            reasons.append(f"Phù hợp kỹ năng bạn quan tâm: {preview}{extra}.")

        # Peer rating reason — CLAUDE.md §5.9: chỉ áp dụng cho TC, BB là cố định
        if peer_rating is not None and peer_rating >= 4.0 and not is_compulsory_bb:
            reason_codes.append("PEER_RATED_HIGH")
            reasons.append(f"Sinh viên trước đánh giá cao ({peer_rating:.1f}/5★, {peer_count} đánh giá).")

        # Availability reason
        if not available_this_term:
            reason_codes.append("NOT_OFFERED_THIS_TERM")
            reasons.append("Môn này không mở trong học kỳ hiện tại.")

        if not reasons:
            reasons.append("Môn chưa hoàn thành trong chương trình.")

        # ── Preliminary score (sẽ được cập nhật sau khi có ML scores) ──────
        preliminary_score = max(rule_score, priority_floor) * 100.0

        direction_track = preferred_track
        if not direction_track or direction_track not in spec_tracks:
            # Pick any sub-direction this course matches
            for sub_dir in spec_tracks:
                if _course_spec_track_score(course.course_name, sub_dir, spec_tracks) > 0:
                    direction_track = sub_dir
                    break
        study_direction = spec_tracks[direction_track]["label"] if direction_track and direction_track in spec_tracks else "Nền tảng tổng hợp"

        scored_items.append({
            "course_code": code,
            "course_name": course.course_name,
            "credits": credits,
            "recommendation_score": round(preliminary_score, 2),
            "fit_probability": round(preliminary_score, 2),
            "reason_codes": sorted(set(reason_codes)),
            "reasons": reasons,
            "study_direction": study_direction,
            "category": "thesis" if is_thesis else (
                "internship" if is_internship else ("elective" if group_key else "required")
            ),
            "elective_group": group_key[2] if group_key else None,
            "available_this_term": available_this_term,
            "pass_rate": course_pass_rate,
            "avg_score10_course": course_avg10,
            "unlock_count": unlock_count,
            "prereq_avg_score": round(prereq_avg, 1) if prereq_avg is not None else None,
            "description": course.description if hasattr(course, "description") else None,
            # Internal: dùng để blend với ML
            "_rule_score": rule_score,
            "_priority_floor": priority_floor,
        })

    # ── Tính GPA trend thực sự từ per-term grades (dùng cho cả ML lẫn LLM) ───────
    _all_user_grades = db.query(models.UserGrade).filter(
        models.UserGrade.user_id == user_id
    ).all()
    _sem_count = len({g.term for g in _all_user_grades if g.term})
    _gpa_trend = 0.0  # -1.0=declining, 0.0=stable, +1.0=improving
    try:
        _term_gpa4: dict = {}
        for _g in _all_user_grades:
            if not _g.passed or not _g.term or "HK3" in (_g.term or ""):
                continue
            _s4 = _score4_from_grade(_g)
            if _s4 is not None:
                _term_gpa4.setdefault(_g.term, []).append(_s4)
        _sorted_avgs = [
            sum(vals) / len(vals)
            for t in sorted(_term_gpa4.keys(), key=_sort_term_key_roadmap)
            if (vals := _term_gpa4[t])
        ]
        if len(_sorted_avgs) >= 2:
            _recent = _sorted_avgs[-3:]
            _diffs = [_recent[i + 1] - _recent[i] for i in range(len(_recent) - 1)]
            _avg_diff = sum(_diffs) / len(_diffs)
            if _avg_diff > 0.05:
                _gpa_trend = 1.0
            elif _avg_diff < -0.05:
                _gpa_trend = -1.0
    except Exception:
        pass

    # ── ML personalization: blend 50% ML + 50% rule-based ──────────────────────
    # ML là hàm scoring chính. Rule-based là fallback và floor enforcement.
    # Khi model chưa được train, 100% rule-based (hệ thống vẫn hoạt động).
    try:
        from backend.core.ml_trainer import ml_score_courses
        _ml_ctx = {
            "avg_score10": snapshot.avg_score10 or 6.0,
            "gpa_trend": _gpa_trend,
            "earned_credits": snapshot.earned_credits,
            "sem_count": _sem_count,
            "career_goal": career_goal,
            "completed_codes": list(snapshot.completed_codes),
            "specialization": specialization,
        }
        _ml_scores = ml_score_courses(_ml_ctx, scored_items, db)
        if _ml_scores:
            for item in scored_items:
                ml_prob = _ml_scores.get(item["course_code"])
                if ml_prob is None:
                    continue
                item["ml_probability"] = round(ml_prob, 3)
                rule_norm = item["_rule_score"]
                # Blend 50/50: ML cá nhân hóa, rule-based đảm bảo logic tốt nghiệp
                blended = 0.50 * ml_prob + 0.50 * rule_norm
                # Áp dụng priority floor (thesis/internship/retake không bị ML hạ cấp)
                final = max(blended, item["_priority_floor"])
                # Penalty môn không mở học kỳ này (nhân 0.5, giữ trong danh sách)
                if not item["available_this_term"]:
                    final *= 0.5
                item["recommendation_score"] = round(final * 100.0, 2)
                item["fit_probability"] = round(final * 100.0, 2)
    except Exception:
        # Fallback: rule-based score + availability penalty
        for item in scored_items:
            if not item["available_this_term"]:
                item["recommendation_score"] = round(item["recommendation_score"] * 0.5, 2)
                item["fit_probability"] = round(item["fit_probability"] * 0.5, 2)

    # ── Score prediction: ước tính điểm sinh viên sẽ đạt ─────────────────────
    overall_gpa = snapshot.avg_score10 or 6.0
    for item in scored_items:
        prereq_avg = item.get("prereq_avg_score")
        pass_rate  = item.get("pass_rate")
        difficulty_factor = (1.0 - pass_rate) if pass_rate is not None else 0.3
        # Dùng điểm TB theo nhóm môn (track) thay vì GPA tổng nếu course khớp track
        _pred_course = snapshot.course_by_code.get(item["course_code"])
        _track_gpa = overall_gpa
        if _pred_course and spec_tracks and track_strengths:
            for _sd in spec_tracks:
                if _course_spec_track_score(_pred_course.course_name, _sd, spec_tracks) > 0:
                    _ts = track_strengths.get(_sd)
                    if _ts is not None and _ts > 0:
                        # Blend 65% track-specific + 35% overall để không quá lệch
                        _track_gpa = _ts * 0.65 + overall_gpa * 0.35
                        break
        # Function #6: dùng grade_predictor module (rule-based + ML hook) thay vì heuristic
        from backend.core.grade_predictor import GradeContext, predict as _gp_predict
        _gp_ctx = GradeContext(
            student_gpa10=overall_gpa if overall_gpa else None,
            track_gpa10=_track_gpa if _track_gpa else None,
            prereq_avg_score10=prereq_avg,
            course_avg_score10=item.get("avg_score10_course"),
            course_pass_rate=item.get("pass_rate"),
            difficulty_factor=difficulty_factor,
        )
        _gp = _gp_predict(_gp_ctx)
        item["predicted_score"] = _gp.expected_score
        item["predicted_score_std"] = _gp.std
        item["pass_probability"] = _gp.pass_probability
        item["prediction_confidence"] = _gp.confidence

    for item in scored_items:
        item.pop("_rule_score", None)
        item.pop("_priority_floor", None)

    scored_items.sort(key=lambda x: (-x["recommendation_score"], x["course_code"]))
    suggested_track_label = spec_tracks[preferred_track]["label"] if preferred_track and preferred_track in spec_tracks else "Nền tảng tổng hợp"
    track_reasoning = _build_track_reasoning(snapshot, track_strengths, preferred_track, career_goal, spec_tracks=spec_tracks)

    # ── Hybrid AI: LLM re-ranks top candidates, falls back to rule-based ────────
    # Cache key: user_id + career_goal + limit + top candidate codes
    _candidate_sig = ",".join(c["course_code"] for c in scored_items[:15])
    _cache_key = f"{user_id}|{career_goal}|{safe_limit}|{_candidate_sig}"

    ai_ranked = False
    top_items: list[dict] = []

    # Check cache first
    _cached = _llm_rec_cache.get(_cache_key)
    if _cached and (datetime.now(timezone.utc) - _cached["ts"]).total_seconds() < _LLM_CACHE_TTL:
        top_items = _cached["items"]
        ai_ranked = _cached["ai_ranked"]
    else:
        try:
            from backend.core.ai_advisor import llm_rerank_courses, enrich_recommendation_reasons
            student_ctx = {
                "avg_score4": snapshot.avg_score4,
                "avg_score10": snapshot.avg_score10,
                "earned_credits": snapshot.earned_credits,
                "total_credits": snapshot.total_credits,
                "specialization": specialization,
                "career_goal": career_goal,
                "preferred_track": suggested_track_label,
                "gpa_trend_direction": "improving" if _gpa_trend > 0 else ("declining" if _gpa_trend < 0 else "stable"),
            }
            candidates = scored_items[:15]
            reranked = llm_rerank_courses(student_ctx, candidates, final_limit=safe_limit)
            if reranked:
                top_items = reranked
                ai_ranked = True
        except Exception:
            pass

        # Fallback: rule-based order + enrich reasons
        if not top_items:
            top_items = scored_items[:safe_limit]
            try:
                ai_reasons = enrich_recommendation_reasons(student_ctx, top_items)
                for item in top_items:
                    ai = ai_reasons.get(item["course_code"])
                    if ai and isinstance(ai, list) and len(ai) > 0:
                        item["reasons"] = ai
            except Exception:
                pass

        # Store in cache
        _llm_rec_cache[_cache_key] = {
            "items": top_items,
            "ai_ranked": ai_ranked,
            "ts": datetime.now(timezone.utc),
        }
        # Evict old entries (keep cache small)
        if len(_llm_rec_cache) > 200:
            oldest = min(_llm_rec_cache, key=lambda k: _llm_rec_cache[k]["ts"])
            del _llm_rec_cache[oldest]

    # ── Plan-based direct suggestions (from official curriculum order) ───────
    completed_plan_sems = {
        CURRICULUM_ORDER.get(code, 0)
        for code in snapshot.completed_codes
        if CURRICULUM_ORDER.get(code, 0) > 0
    }
    current_plan_sem = max(completed_plan_sems) if completed_plan_sems else 0
    next_plan_sem = current_plan_sem + 1
    plan_direct_suggestions = []
    for c in snapshot.courses:
        if c.course_code in snapshot.completed_codes:
            continue
        if CURRICULUM_ORDER.get(c.course_code, 0) == next_plan_sem:
            prereqs_met = all(p in snapshot.completed_codes for p in prereq_map.get(c.course_code, []))
            avail = (c.course_code in available_course_codes) if available_course_codes else None
            plan_direct_suggestions.append({
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": _course_credits(c),
                "prereqs_met": prereqs_met,
                "available_this_term": avail,
            })

    # Build spec_tracks metadata for frontend (labels, icons, per-direction strengths)
    spec_tracks_meta = {
        sub_dir: {
            "label": cfg["label"],
            "icon": cfg.get("icon", "school"),
            "desc": cfg.get("desc", ""),
            "strength": round(track_strengths.get(sub_dir, 0.0), 2),
        }
        for sub_dir, cfg in spec_tracks.items()
    }

    return {
        "generated_at": datetime.now(timezone.utc),
        "total_candidates": len(scored_items),
        "avg_score10_baseline": round(snapshot.avg_score10, 2) if snapshot.avg_score10 is not None else None,
        "avg_score4_baseline": round(snapshot.avg_score4, 2) if snapshot.avg_score4 is not None else None,
        "suggested_track": suggested_track_label,
        "suggested_track_key": preferred_track,
        "track_reasoning": track_reasoning,
        "recommendations": top_items,
        "ai_ranked": ai_ranked,
        "graduation_ready": snapshot.earned_credits >= _get_graduation_threshold(db),
        "internship_eligible": internship_eligible,
        "thesis_eligible": thesis_eligible,
        "current_plan_semester": current_plan_sem,
        "next_plan_semester": next_plan_sem,
        "plan_direct_suggestions": plan_direct_suggestions,
        "specialization": specialization,
        "spec_tracks": spec_tracks_meta,
    }


def _sort_term_key_roadmap(t: str):
    import re
    nums = re.findall(r"\d+", t)
    year = next((int(n) for n in nums if 2000 < int(n) < 2100), 9999)
    hk = next((int(n) for n in nums if 1 <= int(n) <= 4 and int(n) != year), 0)
    return (year, hk)


def build_semester_roadmap(
    db: Session,
    user_id: int,
    max_credits_per_term: float | None = None,
    available_course_codes: set | None = None,
    simulate_failed: list | None = None,
    override_spec: str | None = None,
    target_terms: int = 9,
) -> dict:
    """Project remaining courses into future semesters. Returns completed semesters + upcoming plan + track suggestions.

    Args:
        override_spec: Khi set, dùng CN này thay cho user.specialization để build kế hoạch.
            Phục vụ "explore mode" — SV chưa chốt CN có thể xem lộ trình giả lập với từng CN.
            spec_pending vẫn phản ánh trạng thái thật của user.
        target_terms: Tổng số HK SV muốn TN sau (mặc định 9 = 4.5 năm CTĐT chuẩn).
            Dùng để tính toán nhịp học per-HK khi caller không truyền max_credits_per_term.
            Hỗ trợ SV TN sớm (8 HK) hoặc kéo dài (10-11 HK).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    actual_user_spec = user.specialization if user else None
    specialization = override_spec or actual_user_spec

    # max_credits_per_term sẽ được quyết định ở đây nếu caller không override.
    # Logic:
    #   1. Nếu user có cài max riêng (user.max_credits_per_term) → dùng (theo GPA tier).
    #   2. Else → tính dynamic từ target_terms để spread đều môn ra đủ số HK target.
    # Tính dynamic được làm SAU khi đã build elective_slots (cần total_remaining).
    explicit_max_credits = max_credits_per_term  # giữ original để biết caller có override không

    snapshot = _build_snapshot(db, user_id, specialization=specialization, simulate_failed=simulate_failed)

    # ── Build COMPLETED semesters from grade history ──────────────────────────
    all_grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()
    term_grades: dict[str, list[models.UserGrade]] = defaultdict(list)
    for g in all_grades:
        if g.term:
            term_grades[g.term].append(g)

    completed_semesters = []
    for term in sorted(term_grades.keys(), key=_sort_term_key_roadmap):
        grades = term_grades[term]
        weighted_10: list[tuple[float, float]] = []
        weighted_4: list[tuple[float, float]] = []
        total_tc = 0.0
        course_items = []
        for g in grades:
            c = snapshot.course_by_code.get(g.course_code)
            tc = _course_credits(c) if c else 0.0
            name = c.course_name if c else g.course_code
            s10 = _score10_from_grade(g)
            s4 = _score4_from_grade(g)
            if g.passed and tc > 0:
                total_tc += tc
                if s10 is not None:
                    weighted_10.append((s10, tc))
                if s4 is not None:
                    weighted_4.append((s4, tc))
            course_items.append({
                "course_code": g.course_code,
                "course_name": name,
                "credits": tc,
                "score10": round(s10, 1) if s10 is not None else None,
                "passed": bool(g.passed),
            })
        completed_semesters.append({
            "semester_label": term,
            "total_credits": round(total_tc, 1),
            "gpa4": round(_weighted_average(weighted_4), 2) if weighted_4 else None,
            "gpa10": round(_weighted_average(weighted_10), 2) if weighted_10 else None,
            "courses": course_items,
        })

    # Build prerequisite map (cached)
    prereqs = _get_all_prereqs_cached(db)
    prereq_map: dict[str, list[str]] = defaultdict(list)
    for p in prereqs:
        prereq_map[p.course_code].append(p.prerequisite_code)

    # Identify internship/thesis
    internship_course, thesis_course = _find_internship_thesis(snapshot.courses, specialization)
    internship_code = internship_course.course_code if internship_course else None
    thesis_code = thesis_course.course_code if thesis_course else None

    # Build elective group info & filter out completed groups (same logic as recommendations)
    elective_group_remaining = _elective_group_remaining(
        db, snapshot.course_by_code, snapshot.completed_codes, specialization
    )
    from sqlalchemy import or_ as _or
    all_elective_mappings = db.query(models.CourseElectiveGroup).filter(
        _or(
            models.CourseElectiveGroup.specialization == specialization,
            models.CourseElectiveGroup.specialization == "Chung",
        )
    ).all() if specialization else []
    course_to_group: dict[str, tuple] = {}
    for m in all_elective_mappings:
        course_to_group[m.course_code] = (m.program_code, m.specialization, m.group_type)

    # Build non-elective remaining courses
    non_elective: list[models.Course] = []
    for c in snapshot.courses:
        if c.course_code in snapshot.completed_codes:
            continue
        if c.course_code not in course_to_group:
            non_elective.append(c)

    # Sort required courses: thesis/internship last, then credits desc
    def sort_key(c):
        is_special = c.course_code in (internship_code, thesis_code)
        return (1 if is_special else 0, -_course_credits(c))
    non_elective.sort(key=sort_key)

    # Build elective SLOTS (placeholders) — one 3TC slot per needed credit block per group
    # E.g. Group B needs 9 TC → 3 slots labeled "Tự chọn nhóm B"
    SLOT_TC = 3.0  # each slot represents one course worth of elective credit

    @dataclass
    class ElectiveSlot:
        course_code: str
        course_name: str
        credits: float
        group_type: str
        specialization: str

    elective_slots: list[ElectiveSlot] = []
    for group_key, group_rem in sorted(elective_group_remaining.items()):
        if group_rem <= 0.0:
            continue
        _, gspec, gtype = group_key
        num_slots = int(group_rem / SLOT_TC + 0.5)  # round to nearest whole slot
        label = f"Tự chọn nhóm {gtype}"
        for i in range(num_slots):
            slot_code = f"__ELECTIVE_{gtype}_{i+1}__"
            elective_slots.append(ElectiveSlot(
                course_code=slot_code,
                course_name=label,
                credits=SLOT_TC,
                group_type=gtype,
                specialization=gspec,
            ))

    remaining = non_elective  # type: ignore[assignment]

    semesters: list[dict] = []
    completed_in_roadmap: set[str] = set(snapshot.completed_codes)
    remaining_codes = {c.course_code: c for c in remaining}
    # Add elective slots as pseudo-entries (not real Course objects)
    remaining_slots = list(elective_slots)
    sem_num = 1

    # Compute current_plan_sem early — used to mark HK1-HK4 as school-assigned
    # (full computation also happens later for plan_direct_suggestions; this is harmless dup)
    _completed_plan_sems_early = {
        CURRICULUM_ORDER.get(code, 0)
        for code in snapshot.completed_codes
        if CURRICULUM_ORDER.get(code, 0) > 0
    }
    current_plan_sem_early = max(_completed_plan_sems_early) if _completed_plan_sems_early else 0

    # ── Dynamic per-term cap based on target_terms (D3 pace control) ──────────
    # Target HK còn lại = target_terms - HK đã có (estimate).
    # completed_semesters dùng term_label (HK1 2021-2022 v.v.) — số lượng = HK đã học theo time.
    # current_plan_sem_early = HK theo CTĐT order — có thể khác nếu SV nợ môn HK trước.
    # Dùng max(2 con số) cho an toàn (không spread quá thưa).
    completed_count_est = max(len(completed_semesters), current_plan_sem_early)
    future_target = max(1, target_terms - completed_count_est)

    if explicit_max_credits is None:
        # Deprecated 2026-05-05: user.max_credits_per_term dropped — luôn tính dynamic
        total_rem_est = (
            sum(_course_credits(c) for c in non_elective)
            + sum(s.credits for s in elective_slots)
        )
        if future_target > 0 and total_rem_est > 0:
            import math
            computed = math.ceil(total_rem_est / future_target)
            max_credits_per_term = float(max(14, min(25, computed)))
        else:
            max_credits_per_term = 18.0
    else:
        max_credits_per_term = float(explicit_max_credits)
    max_credits_per_term = max_credits_per_term or 18.0

    # University rule: when sharing a semester with internship or thesis,
    # non-special courses may NOT exceed INTERNSHIP_DEBT_CAP (6 TC).
    INTERNSHIP_DEBT_CAP = 6.0

    # Pre-compute sets of all thesis/internship codes by name pattern for correct ordering
    _all_thesis_codes = {
        c.course_code for c in snapshot.courses
        if "do an" in _normalize_text(c.course_name) and "tot nghiep" in _normalize_text(c.course_name)
    }
    _all_internship_codes = {
        c.course_code for c in snapshot.courses
        if "thuc tap" in _normalize_text(c.course_name) and "tot nghiep" in _normalize_text(c.course_name)
    }

    while remaining_codes:
        # ── Unlock courses whose prerequisites are all satisfied ──────────────
        # Any thesis course is blocked while ANY internship course of the same
        # naming pattern is still pending (covers multi-spec users with no spec set).
        any_internship_remaining = bool(_all_internship_codes & remaining_codes.keys())
        unlocked = [
            c for c in remaining_codes.values()
            if all(p in completed_in_roadmap for p in prereq_map.get(c.course_code, []))
            and not (c.course_code in _all_thesis_codes and any_internship_remaining)
        ]
        if not unlocked:
            unlocked = list(remaining_codes.values())  # circular prereq fallback

        # Separate regular from thesis/internship (use identified codes for special handling)
        all_regular = [c for c in unlocked if c.course_code not in (internship_code, thesis_code)]
        special     = [c for c in unlocked if c.course_code in (internship_code, thesis_code)]

        # Sort regular courses: curriculum order first, then availability, then credits-desc
        # Courses not in CURRICULUM_ORDER are placed after HK6 (default 10)
        def _sort_key(c: models.Course) -> tuple:
            plan_sem = CURRICULUM_ORDER.get(c.course_code, 10)
            not_avail = 0 if (available_course_codes and c.course_code in available_course_codes) else 1
            # At same priority, internship-type before thesis-type
            n = _normalize_text(c.course_name)
            is_thesis_type = 1 if (c.course_code in _all_thesis_codes) else 0
            return (plan_sem, not_avail, is_thesis_type, -_course_credits(c))

        if sem_num == 1 and available_course_codes:
            avail_reg = [c for c in all_regular if c.course_code in available_course_codes]
            pool = avail_reg if avail_reg else all_regular
            regular = sorted(pool, key=_sort_key)
        else:
            regular = sorted(all_regular, key=_sort_key)

        sem_courses: list = []
        sem_credits = 0.0

        # ── Step 1: fill regular required courses up to max_credits_per_term ──
        for c in regular:
            tc = _course_credits(c)
            if sem_credits + tc > max_credits_per_term and sem_courses:
                break
            sem_courses.append(c)
            sem_credits += tc
            if sem_credits >= max_credits_per_term:
                break

        # ── Step 2: decide whether thesis/internship joins THIS semester ───────
        # Rules:
        #   - thesis/internship may only share a semester if other credits ≤ 6 TC.
        #   - THESIS additionally requires all remaining elective slots to fit within
        #     the same semester (≤ INTERNSHIP_DEBT_CAP - current credits). This
        #     prevents elective slots appearing after thesis, which is illogical.
        #   - Internship has no such restriction (electives may follow before thesis).
        remaining_slot_credits = sum(s.credits for s in remaining_slots)
        # Total non-special credits still pending AFTER this semester's regular courses.
        # Internship and thesis are only placed when this is ≤ INTERNSHIP_DEBT_CAP (6 TC).
        sem_course_codes = {c.course_code for c in sem_courses if not isinstance(c, ElectiveSlot)}
        pending_non_special = (
            sum(
                _course_credits(c) for code, c in remaining_codes.items()
                if code not in (internship_code, thesis_code)
                and code not in sem_course_codes
            )
            + remaining_slot_credits
        )
        special_to_add = None
        if special and pending_non_special <= INTERNSHIP_DEBT_CAP:
            for c in special:
                tc = _course_credits(c)
                # Must fit in term limit (or nothing else is scheduled yet)
                if sem_credits + tc > max_credits_per_term and sem_courses:
                    continue
                # THESIS requires ALL elective slots completed first (none may share thesis semester)
                if c.course_code == thesis_code and remaining_slot_credits > 0:
                    continue
                special_to_add = c
                break

        # ── Step 3: fill elective slots — spread tự nhiên qua các HK ────────────
        # Slot fill phần capacity còn lại sau BB. KHÔNG cap slot/HK cứng vì:
        #   - max_credits_per_term đã được tính dynamic = total/future_target → ép spread
        #   - Cap slot cứng + max_credits cao gây dư capacity → tràn ra HK trailing
        # Quy tắc đơn giản:
        #   - HK thesis: 0 slot (không chia chỗ với ĐATN)
        #   - HK internship: tối đa 6 TC khác (INTERNSHIP_DEBT_CAP)
        #   - HK bình thường: fill đến max_credits_per_term
        is_thesis_sem = special_to_add is not None and special_to_add.course_code == thesis_code
        if is_thesis_sem:
            slot_cap = 0
        elif special_to_add:
            slot_cap = INTERNSHIP_DEBT_CAP
        else:
            slot_cap = max_credits_per_term
        while remaining_slots and sem_credits < slot_cap:
            slot = remaining_slots[0]
            if sem_credits + slot.credits > slot_cap:
                break
            sem_courses.append(slot)  # type: ignore[arg-type]
            sem_credits += slot.credits
            remaining_slots.pop(0)

        # ── Step 4: add thesis/internship ──────────────────────────────────────
        if special_to_add:
            tc = _course_credits(special_to_add)
            if sem_credits + tc <= max_credits_per_term or not sem_courses:
                sem_courses.append(special_to_add)
                sem_credits += tc
            else:
                # Won't fit alongside current courses: add alone next iteration
                pass
        elif special and not sem_courses:
            # Edge case: nothing else remains — start the special course alone
            c = special[0]
            sem_courses.append(c)
            sem_credits += _course_credits(c)

        if not sem_courses:
            break

        course_items = []
        for c in sem_courses:
            if isinstance(c, ElectiveSlot):
                course_items.append({
                    "course_code": c.course_code,
                    "course_name": c.course_name,
                    "credits": c.credits,
                    "category": "elective_slot",
                    "available_this_term": None,
                    "elective_group": c.group_type,
                })
            else:
                available = (c.course_code in available_course_codes) if available_course_codes is not None else None
                if c.course_code == internship_code:
                    cat = "internship"
                elif c.course_code == thesis_code:
                    cat = "thesis"
                else:
                    cat = "required"
                course_items.append({
                    "course_code": c.course_code,
                    "course_name": c.course_name,
                    "credits": _course_credits(c),
                    "category": cat,
                    "available_this_term": available,
                })
                completed_in_roadmap.add(c.course_code)
                del remaining_codes[c.course_code]

        # CTĐT HK number (continuous từ HK đã học) → label đúng thay vì luôn "HK 1 (dự kiến)"
        # CHỈ HK1 + HK2 (năm 1) do nhà trường xếp — verified từ 2 bảng điểm K21 thật:
        # SV1 vs SV2 trùng 100% ở HK1+HK2/2021-2022, từ HK3 (kể cả hè) đã khác.
        ctdt_hk_for_this_term = current_plan_sem_early + sem_num
        is_assigned_by_school = ctdt_hk_for_this_term <= 2

        semesters.append({
            "semester_number": ctdt_hk_for_this_term,
            "semester_label": f"Học kỳ {ctdt_hk_for_this_term} (dự kiến)",
            "total_credits": round(sem_credits, 1),
            "courses": course_items,
            "is_assigned_by_school": is_assigned_by_school,
        })
        sem_num += 1
        if sem_num > 20:
            break

    # Distribute any leftover elective slots — vẫn cap 2 slot/HK để spread đều,
    # tránh dồn 6 môn vào 1 HK cuối như trước.
    LEFTOVER_SLOTS_PER_HK = 2
    while remaining_slots and sem_num <= 20:
        slot_sem_credits = 0.0
        slot_sem_courses = []
        slots_added = 0
        while remaining_slots and slot_sem_credits < max_credits_per_term and slots_added < LEFTOVER_SLOTS_PER_HK:
            slot = remaining_slots[0]
            if slot_sem_credits + slot.credits > max_credits_per_term:
                break
            slot_sem_courses.append(slot)
            slot_sem_credits += slot.credits
            remaining_slots.pop(0)
            slots_added += 1
        if not slot_sem_courses:
            break
        ctdt_hk_for_slot_term = current_plan_sem_early + sem_num
        semesters.append({
            "semester_number": ctdt_hk_for_slot_term,
            "semester_label": f"Học kỳ {ctdt_hk_for_slot_term} (dự kiến)",
            "total_credits": round(slot_sem_credits, 1),
            "courses": [
                {"course_code": s.course_code, "course_name": s.course_name,
                 "credits": s.credits, "category": "elective_slot",
                 "available_this_term": None, "elective_group": s.group_type}
                for s in slot_sem_courses
            ],
            "is_assigned_by_school": False,  # elective slots only appear after HK2 → never locked
        })
        sem_num += 1

    # ── Enforce đúng future_target HK ─────────────────────────────────────────
    # Trường hợp 1: loop ra ít hơn target → pad bằng HK trống ở cuối.
    while len(semesters) < future_target and sem_num <= 20:
        ctdt_hk_for_pad = current_plan_sem_early + sem_num
        semesters.append({
            "semester_number": ctdt_hk_for_pad,
            "semester_label": f"Học kỳ {ctdt_hk_for_pad} (dự kiến)",
            "total_credits": 0.0,
            "courses": [],
            "is_assigned_by_school": False,
        })
        sem_num += 1

    # Trường hợp 2: loop ra NHIỀU hơn target (vd 11 HK target 9) → merge HK cuối
    # vào HK kề trước. Ưu tiên merge slot trước (vì slot dễ ghép). Cảnh báo: có thể
    # 1-2 HK bị vượt nhẹ max_credits — chấp nhận để giữ shape CTĐT 9 HK.
    while len(semesters) > future_target:
        last = semesters.pop()
        prev = semesters[-1]
        # Đẩy môn của HK cuối lên HK kề trước
        prev["courses"].extend(last["courses"])
        prev["total_credits"] = round(prev["total_credits"] + last["total_credits"], 1)

    # Round float total_credits trong tất cả HK để tránh hiển thị 19.5562500...
    for sem in semesters:
        sem["total_credits"] = round(sem["total_credits"], 1)

    total_remaining = sum(_course_credits(c) for c in remaining) + sum(s.credits for s in elective_slots)

    # ── Build track-based elective suggestions (specialization-aware) ─────────
    roadmap_spec_tracks = _get_spec_tracks(specialization)
    track_suggestions: dict[str, dict[str, list[dict]]] = {k: {} for k in roadmap_spec_tracks}
    if specialization:
        from sqlalchemy import or_ as _or2
        all_elective_mappings2 = db.query(models.CourseElectiveGroup).filter(
            _or2(
                models.CourseElectiveGroup.specialization == specialization,
                models.CourseElectiveGroup.specialization == "Chung",
            )
        ).all()
        group_to_courses: dict[str, list[models.Course]] = defaultdict(list)
        for m in all_elective_mappings2:
            c = snapshot.course_by_code.get(m.course_code)
            if c and m.course_code not in snapshot.completed_codes:
                group_to_courses[m.group_type].append(c)

        for track_key in roadmap_spec_tracks:
            for gtype, candidates in group_to_courses.items():
                matched = [
                    c for c in candidates
                    if _course_spec_track_score(c.course_name, track_key, roadmap_spec_tracks) > 0
                ]
                if not matched:
                    matched = candidates[:4]
                track_suggestions[track_key][gtype] = [
                    {"course_code": c.course_code, "course_name": c.course_name, "credits": _course_credits(c)}
                    for c in matched[:4]
                ]

    # Build spec_tracks metadata for frontend dynamic rendering
    roadmap_spec_tracks_meta = {
        sub_dir: {"label": cfg["label"], "icon": cfg.get("icon", "school"), "desc": cfg.get("desc", "")}
        for sub_dir, cfg in roadmap_spec_tracks.items()
    }

    # Build a compact prereq_map for remaining courses only (for frontend validation)
    remaining_all_codes = {c.course_code for c in remaining} | {s.course_code for s in elective_slots}
    frontend_prereq_map = {
        code: prereqs_list
        for code, prereqs_list in prereq_map.items()
        if code in remaining_all_codes and prereqs_list
    }

    # ── Plan-based direct suggestions ────────────────────────────────────────
    # Determine the student's current curriculum position and suggest next courses
    completed_plan_sems = {
        CURRICULUM_ORDER.get(code, 0)
        for code in snapshot.completed_codes
        if CURRICULUM_ORDER.get(code, 0) > 0
    }
    current_plan_sem = max(completed_plan_sems) if completed_plan_sems else 0
    next_plan_sem = current_plan_sem + 1

    # Courses in the next curriculum semester that are not yet completed
    plan_direct_suggestions = []
    for c in snapshot.courses:
        if c.course_code in snapshot.completed_codes:
            continue
        if CURRICULUM_ORDER.get(c.course_code, 0) == next_plan_sem:
            prereqs_met = all(p in snapshot.completed_codes for p in prereq_map.get(c.course_code, []))
            plan_direct_suggestions.append({
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": _course_credits(c),
                "prereqs_met": prereqs_met,
                "available_this_term": (c.course_code in available_course_codes) if available_course_codes else None,
            })
    # Also include overdue courses (from earlier plan sems still incomplete)
    overdue = []
    for c in snapshot.courses:
        if c.course_code in snapshot.completed_codes:
            continue
        plan_pos = CURRICULUM_ORDER.get(c.course_code, 0)
        if 0 < plan_pos < next_plan_sem:
            overdue.append({
                "course_code": c.course_code,
                "course_name": c.course_name,
                "credits": _course_credits(c),
                "plan_semester": plan_pos,
                "prereqs_met": all(p in snapshot.completed_codes for p in prereq_map.get(c.course_code, [])),
            })

    # spec_pending phản ánh trạng thái THẬT của user, không phải override_spec.
    # SV đang explore (override_spec) thì spec_pending vẫn True — banner explore vẫn hiện,
    # nhưng kế hoạch HK đã build theo CN giả lập.
    spec_pending = actual_user_spec is None

    return {
        "completed_semesters": completed_semesters,
        "semesters": semesters,
        "total_remaining_credits": round(total_remaining, 1),
        "estimated_terms": len(semesters),
        "max_credits_per_term": max_credits_per_term,
        "track_elective_suggestions": track_suggestions,
        "spec_tracks": roadmap_spec_tracks_meta,
        "prereq_map": frontend_prereq_map,
        "internship_code": internship_code,
        "thesis_code": thesis_code,
        "current_plan_semester": current_plan_sem,
        "next_plan_semester": next_plan_sem,
        "plan_direct_suggestions": plan_direct_suggestions,
        "overdue_courses": overdue,
        "specialization": specialization,
        "actual_user_spec": actual_user_spec,
        "explore_spec": override_spec if (override_spec and override_spec != actual_user_spec) else None,
        "spec_pending": spec_pending,
    }


def build_analytics(db: Session, user_id: int) -> dict:
    """Build analytics: per-term GPA, subject groups, weak/failed courses, trends."""
    user = db.query(models.User).filter(models.User.id == user_id).first()
    specialization = user.specialization if user else None
    snapshot = _build_snapshot(db, user_id, specialization=specialization)

    all_grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user_id).all()
    course_credits_map = {c.course_code: _course_credits(c) for c in snapshot.courses}

    # Per-term GPA
    term_data: dict[str, dict] = defaultdict(lambda: {"num10": 0.0, "num4": 0.0, "den": 0.0})
    for g in all_grades:
        if not g.passed or not g.term:
            continue
        tc = course_credits_map.get(g.course_code, 0.0)
        if tc <= 0:
            continue
        s10 = _score10_from_grade(g)
        s4 = _score4_from_grade(g)
        if s10 is not None:
            term_data[g.term]["num10"] += s10 * tc
        if s4 is not None:
            term_data[g.term]["num4"] += s4 * tc
        term_data[g.term]["den"] += tc

    def _sort_term_key(t: str):
        import re
        nums = re.findall(r"\d+", t)
        year = next((int(n) for n in nums if 2000 < int(n) < 2100), 9999)
        hk = next((int(n) for n in nums if 1 <= int(n) <= 4 and int(n) != year), 0)
        return (year, hk)

    gpa_by_term = []
    for term in sorted(term_data.keys(), key=_sort_term_key):
        d = term_data[term]
        if d["den"] <= 0:
            continue
        gpa_by_term.append({
            "term": term,
            "gpa4": round(d["num4"] / d["den"], 2),
            "gpa10": round(d["num10"] / d["den"], 2),
            "credits_earned": round(d["den"], 1),
        })

    # GPA trend direction
    gpa_trend = "insufficient_data"
    if len(gpa_by_term) >= 2:
        vals = [t["gpa4"] for t in gpa_by_term[-3:]]
        diffs = [vals[i+1] - vals[i] for i in range(len(vals)-1)]
        avg_diff = sum(diffs) / len(diffs)
        if avg_diff > 0.05:
            gpa_trend = "improving"
        elif avg_diff < -0.05:
            gpa_trend = "declining"
        else:
            gpa_trend = "stable"

    # Subject group performance
    group_data: dict[str, dict] = {k: {"num": 0.0, "den": 0.0, "count": 0} for k in TRACKS}
    for g in all_grades:
        if not g.passed:
            continue
        s10 = _score10_from_grade(g)
        if s10 is None:
            continue
        course = snapshot.course_by_code.get(g.course_code)
        if not course:
            continue
        matched_tracks = _course_tracks(course.course_name)
        for track in matched_tracks:
            group_data[track]["num"] += s10
            group_data[track]["den"] += 1
            group_data[track]["count"] += 1

    subject_group_performance = []
    for track_key, info in TRACKS.items():
        d = group_data[track_key]
        if d["den"] > 0:
            subject_group_performance.append({
                "group_name": info["label"],
                "avg_score10": round(d["num"] / d["den"], 2),
                "course_count": d["count"],
            })

    # Elective course map for is_elective flag
    from sqlalchemy import or_
    if specialization:
        _elective_mappings = db.query(models.CourseElectiveGroup).filter(
            or_(
                models.CourseElectiveGroup.specialization == specialization,
                models.CourseElectiveGroup.specialization == "Chung",
            )
        ).all()
    else:
        _elective_mappings = db.query(models.CourseElectiveGroup).filter(
            models.CourseElectiveGroup.specialization == "Chung"
        ).all()
    elective_codes: set[str] = {m.course_code for m in _elective_mappings}

    # Weak and failed courses
    best = snapshot.best_grades
    weak_courses = []
    failed_courses = []
    for code, g in best.items():
        s10 = _score10_from_grade(g)
        course = snapshot.course_by_code.get(code)
        if not course:
            continue
        tc = _course_credits(course)
        item = {
            "course_code": code,
            "course_name": course.course_name,
            "score10": round(s10, 2) if s10 is not None else None,
            "credits": tc,
            "passed": g.passed,
            "is_elective": code in elective_codes,
        }
        if not g.passed and (g.score10 is not None or g.score4 is not None or g.letter is not None):
            # Only include courses that truly failed (have a score); in-progress = no score
            failed_courses.append(item)
        elif g.passed and s10 is not None and s10 < 6.0:
            weak_courses.append(item)

    weak_courses.sort(key=lambda x: x["score10"] or 0)
    failed_courses.sort(key=lambda x: x["course_name"])

    # Study pace
    terms_studied = len(gpa_by_term)
    study_pace = "unknown"
    if terms_studied > 0 and snapshot.total_credits > 0:
        avg_tc_per_term = snapshot.earned_credits / terms_studied
        expected_tc_per_term = snapshot.total_credits / 9  # 4.5-year program = 9 terms
        if avg_tc_per_term >= expected_tc_per_term * 1.1:
            study_pace = "ahead"
        elif avg_tc_per_term >= expected_tc_per_term * 0.85:
            study_pace = "on_track"
        else:
            study_pace = "behind"

    # Recommended credits for next term
    # Cột users.max_credits_per_term đã DROP ở Phase 4 (2026-05-05) — chỉ dùng heuristic theo GPA
    gpa_val = snapshot.avg_score4 or 0.0
    if gpa_val >= 3.2:
        rec_credits = 21.0
    elif gpa_val >= 2.5:
        rec_credits = 18.0
    elif gpa_val >= 2.0:
        rec_credits = 15.0
    else:
        rec_credits = 12.0

    # Graduation timeline
    import math as _math
    import re as _re
    credits_remaining = max(0.0, snapshot.total_credits - snapshot.earned_credits)
    credits_progress_pct = round(snapshot.earned_credits / snapshot.total_credits * 100, 1) if snapshot.total_credits > 0 else 0.0

    terms_remaining: int | None = None
    estimated_graduation_term: str | None = None
    if credits_remaining > 0 and terms_studied > 0:
        avg_tc_actual = snapshot.earned_credits / terms_studied
        effective_tc = min(avg_tc_actual, rec_credits) if avg_tc_actual > 0 else rec_credits
        if effective_tc > 0:
            terms_remaining = _math.ceil(credits_remaining / effective_tc)
            try:
                cfg = db.query(models.SystemConfig).filter(models.SystemConfig.key == "active_semester").first()
                active_sem = cfg.value if cfg else None
                if active_sem:
                    m = _re.search(r'H[oọ][cọ]\s*k[yỳ]\s+(\d+).*?(\d{4})', active_sem, _re.IGNORECASE)
                    if not m:
                        m = _re.search(r'HK\s*(\d+)[/\-](\d{4})', active_sem, _re.IGNORECASE)
                    if m:
                        curr_hk = int(m.group(1))
                        curr_year_start = int(m.group(2))
                        curr_idx = curr_year_start * 2 + (curr_hk - 1)
                        grad_idx = curr_idx + terms_remaining
                        grad_hk = (grad_idx % 2) + 1
                        grad_year_start = grad_idx // 2
                        estimated_graduation_term = f"HK{grad_hk}/{grad_year_start}"
            except Exception:
                pass
    elif credits_remaining <= 0:
        terms_remaining = 0

    return {
        "gpa_by_term": gpa_by_term,
        "subject_group_performance": subject_group_performance,
        "weak_courses": weak_courses,
        "failed_courses": failed_courses,
        "gpa_trend_direction": gpa_trend,
        "study_pace": study_pace,
        "recommended_credits_next_term": rec_credits,
        "credits_remaining": round(credits_remaining, 1),
        "credits_total": round(snapshot.total_credits, 1),
        "credits_progress_pct": credits_progress_pct,
        "terms_remaining": terms_remaining,
        "estimated_graduation_term": estimated_graduation_term,
    }
