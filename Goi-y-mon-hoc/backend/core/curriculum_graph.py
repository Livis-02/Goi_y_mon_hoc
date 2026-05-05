"""
CurriculumGraph — knowledge graph xây từ database.

Cung cấp:
- Track tags tĩnh cho từng mã môn (từ CTDT 7480201)
- Thứ tự học kỳ thiết kế trong CTDT
- Đồ thị tiên quyết (prereq / dependents)
- Điểm unlock (bắc cầu), curriculum alignment
- Hàm extract_features() dùng chung cho training và inference
"""
from __future__ import annotations

import unicodedata
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy.orm import Session
from backend.db import models


# ── Static CTDT knowledge ────────────────────────────────────────────────────────
# Gắn track tag cho từng mã môn trong CTDT 7480201.
# Cập nhật tại đây khi chương trình đào tạo thay đổi.

COURSE_TRACK_TAGS: dict[str, frozenset] = {
    # Foundation / Toán
    "7010102": frozenset({"foundation"}),               # Đại số tuyến tính
    "7010103": frozenset({"foundation"}),               # Giải tích 1
    "7010104": frozenset({"foundation"}),               # Giải tích 2
    "7010111": frozenset({"foundation"}),               # Phương pháp tính
    "7010120": frozenset({"foundation", "data_ai"}),    # Xác suất thống kê
    "7010204": frozenset({"foundation"}),               # Vật lý đại cương 1
    # Lập trình cơ bản
    "7080514": frozenset({"foundation"}),               # Nhập môn ngành CNTT
    "7080208": frozenset({"software", "foundation"}),   # Cơ sở lập trình
    "7080216": frozenset({"software"}),                 # Kỹ thuật LT HĐT C++
    "7080512": frozenset({"software"}),                 # LT HĐT Java
    "7080206": frozenset({"software", "data_ai"}),      # CTDL & Giải thuật
    "7080516": frozenset({"software", "data_ai"}),      # Phân tích & thiết kế thuật toán
    # Cơ sở dữ liệu
    "7080207": frozenset({"software", "data_ai"}),      # Cơ sở dữ liệu
    "7080211": frozenset({"software", "data_ai"}),      # Hệ QTCSDL
    # Data / AI
    "7080509": frozenset({"data_ai"}),                  # Khoa học dữ liệu
    "7080508": frozenset({"data_ai"}),                  # Khai phá dữ liệu
    "7080122": frozenset({"data_ai"}),                  # Trí tuệ nhân tạo
    "7080518": frozenset({"data_ai"}),                  # Thị giác máy tính
    "7080510": frozenset({"data_ai"}),                  # Kỹ nghệ tri thức & học máy
    "7080506": frozenset({"data_ai"}),                  # Đồ án Khoa học máy tính
    "7080520": frozenset({"software", "data_ai"}),      # Web ngữ nghĩa
    # Web / Software Engineering
    "7080116": frozenset({"software"}),                 # Phát triển ứng dụng Web
    "7080113": frozenset({"software"}),                 # Phân tích & thiết kế hệ thống
    "7080515": frozenset({"software"}),                 # Phân tích & thiết kế HĐT
    "7080111": frozenset({"software"}),                 # Mã nguồn mở
    "7080626": frozenset({"software"}),                 # Thương mại điện tử
    # Network / Security / IoT
    "7080712": frozenset({"network_security_iot"}),     # Kiến trúc máy tính
    "7080112": frozenset({"network_security_iot"}),     # Nguyên lý HĐH
    "7080717": frozenset({"network_security_iot"}),     # Mạng máy tính
    "7080703": frozenset({"network_security_iot"}),     # Cơ sở an ninh mạng
    "7080713": frozenset({"network_security_iot"}),     # Kiến trúc & hạ tầng mạng IoT
    "7080517": frozenset({"network_security_iot"}),     # Phát triển ứng dụng IoT
    "7080504": frozenset({"network_security_iot", "software"}),  # Điện toán đám mây
}

# Mã môn → học kỳ thiết kế trong CTDT (1..9)
CURRICULUM_SEMESTER: dict[str, int] = {
    # HK1
    "7010102": 1, "7010103": 1, "7010120": 1, "7010601": 1,
    "7010701": 1, "7020105": 1, "7080514": 1, "7300103": 1,
    "7300104": 1, "7300202": 1, "7300203": 1,
    # HK2
    "7010104": 2, "7010111": 2, "7010202": 2, "7010204": 2,
    "7010602": 2, "7010702": 2, "7020302": 2, "7080208": 2,
    # HK3
    "7010304": 3, "7010703": 3, "7020202": 3, "7080112": 3,
    "7080207": 3, "7080216": 3, "7080712": 3,
    # HK4
    "7020201": 4, "7080206": 4, "7080211": 4, "7080512": 4,
    "7080717": 4, "7300101": 4,
    # HK5
    "7020303": 5, "7080111": 5, "7080116": 5, "7080509": 5,
    "7080703": 5, "7080713": 5, "7300102": 5,
    # HK6
    "7020104": 6, "7080113": 6, "7080122": 6, "7080517": 6,
    "7080626": 6, "7300201": 6,
    # HK7
    "7080504": 7, "7080508": 7, "7080515": 7, "7080518": 7,
    "7080516": 7, "7080520": 7,
    # HK8
    "7080506": 8, "7080510": 8,
    # HK9 — thực tập / đồ án
    "7080513": 9, "7080519": 9,
}

MAX_CURRICULUM_SEM = 9

# Career goal → track tags mapping (dùng để tính track_match feature)
CAREER_TO_TRACKS: dict[str, set[str]] = {
    "ai_data":          {"data_ai"},
    "web":              {"software"},
    "network_security": {"network_security_iot"},
    "general":          {"foundation", "software", "data_ai", "network_security_iot"},
}


def _normalize(text: str) -> str:
    s = str(text or "").strip().lower()
    s = s.replace("\u0111", "d").replace("\u0110", "d")
    s = unicodedata.normalize("NFKD", s)
    return "".join(c for c in s if not unicodedata.combining(c))


def _keyword_tracks(name: str) -> frozenset:
    """Fallback keyword-based track detection from course name."""
    n = _normalize(name)
    found: set[str] = set()
    _kw = {
        "data_ai":              ["du lieu", "tri tue nhan tao", "hoc may", "khai pha",
                                 "thi giac", "thong ke", "xac suat"],
        "software":             ["lap trinh", "web", "he thong", "doi tuong", "java",
                                 "ma nguon mo", "thuong mai", "thuật toan", "giai thuat"],
        "network_security_iot": ["mang", "an ninh", "iot", "dam may", "ha tang",
                                 "kien truc", "bao mat"],
    }
    for track, kws in _kw.items():
        if any(kw in n for kw in kws):
            found.add(track)
    return frozenset(found) if found else frozenset({"foundation"})


# ── Tên của 14 features ─────────────────────────────────────────────────────────
FEATURE_NAMES: list[str] = [
    "student_gpa10",        # GPA tích lũy thang 10 (0–10)
    "student_gpa_trend",    # Xu hướng GPA: 0=giảm, 0.5=ổn định, 1=tăng
    "student_credits_ratio",# Tỷ lệ tín chỉ tích lũy (0–1)
    "student_sem_count_n",  # Số kỳ đã học, chuẩn hóa 0–1 (/ MAX_CURRICULUM_SEM)
    "course_credits_n",     # Số tín chỉ môn, chuẩn hóa 0–1 (/ 10)
    "course_curriculum_sem_n",  # HK thiết kế trong CTDT, chuẩn hóa 0–1
    "course_pass_rate",     # Tỷ lệ qua môn toàn hệ thống (0–1; 0.75 nếu chưa có)
    "ability_gap_n",        # (GPA_SV - avg_course) / 10, chuẩn hóa
    "curriculum_alignment", # Mức khớp thời điểm học (0–1)
    "track_match",          # 1 nếu môn khớp định hướng sinh viên
    "prereq_perf_n",        # Điểm TB các môn tiên quyết, chuẩn hóa (0–1)
    "unlock_count_n",       # Unlock count chuẩn hóa 0–1
    "is_required",          # 1 nếu môn bắt buộc
    "is_elective_needed",   # 1 nếu nhóm tự chọn vẫn còn thiếu tín chỉ
]


@dataclass
class CurriculumGraph:
    """Đồ thị tri thức chương trình đào tạo xây từ DB."""

    courses: dict[str, models.Course] = field(default_factory=dict)
    prereq_map: dict[str, list[str]] = field(default_factory=dict)
    dependents_map: dict[str, list[str]] = field(default_factory=dict)
    elective_group_map: dict[str, tuple] = field(default_factory=dict)
    elective_group_remaining: dict[tuple, float] = field(default_factory=dict)
    required_codes: set[str] = field(default_factory=set)
    total_credits: float = 0.0

    # ── Factory ─────────────────────────────────────────────────────────────────
    @classmethod
    def from_db(
        cls,
        db: Session,
        specialization: str | None,
        completed_codes: set[str] | None = None,
    ) -> "CurriculumGraph":
        from sqlalchemy import or_

        # Lọc courses theo chuyên ngành
        all_courses = db.query(models.Course).all()
        if specialization:
            user_elective_codes: set[str] = {
                m.course_code
                for m in db.query(models.CourseElectiveGroup).filter(
                    or_(
                        models.CourseElectiveGroup.specialization == specialization,
                        models.CourseElectiveGroup.specialization == "Chung",
                    )
                ).all()
            }
            other_elective_codes: set[str] = {
                m.course_code
                for m in db.query(models.CourseElectiveGroup).filter(
                    models.CourseElectiveGroup.specialization != specialization,
                    models.CourseElectiveGroup.specialization != "Chung",
                ).all()
            } - user_elective_codes
            courses = [
                c for c in all_courses
                if (c.required_specialization is None and c.course_code not in other_elective_codes)
                or c.required_specialization == specialization
            ]
        else:
            courses = all_courses

        course_dict = {c.course_code: c for c in courses}

        # Tiên quyết
        prereq_map: dict[str, list[str]] = defaultdict(list)
        dependents_map: dict[str, list[str]] = defaultdict(list)
        for p in db.query(models.CoursePrerequisite).all():
            if p.course_code in course_dict:
                prereq_map[p.course_code].append(p.prerequisite_code)
                dependents_map[p.prerequisite_code].append(p.course_code)

        # Nhóm tự chọn
        elective_group_map: dict[str, tuple] = {}
        elective_group_remaining: dict[tuple, float] = {}
        if specialization:
            from sqlalchemy import or_ as _or
            rules = db.query(models.ElectiveRule).filter(
                _or(
                    models.ElectiveRule.specialization == specialization,
                    models.ElectiveRule.specialization == "Chung",
                )
            ).all()
            mappings = db.query(models.CourseElectiveGroup).filter(
                _or(
                    models.CourseElectiveGroup.specialization == specialization,
                    models.CourseElectiveGroup.specialization == "Chung",
                )
            ).all()
            group_courses_sets: dict[tuple, set[str]] = defaultdict(set)
            for m in mappings:
                key = (m.program_code, m.specialization, m.group_type)
                elective_group_map[m.course_code] = key
                group_courses_sets[key].add(m.course_code)

            completed = completed_codes or set()
            for rule in rules:
                key = (rule.program_code, rule.specialization, rule.group_type)
                min_req = float(rule.min_credits_required or 0)
                earned = sum(
                    float(course_dict[c].credits or 0)
                    for c in group_courses_sets.get(key, set())
                    if c in completed and c in course_dict
                )
                elective_group_remaining[key] = max(0.0, min_req - earned)

        required_codes = {c.course_code for c in courses if c.course_code not in elective_group_map}
        total_credits = sum(
            float(c.credits or 0) for c in courses
            if getattr(c, "count_toward_credits", True)
        )

        return cls(
            courses=course_dict,
            prereq_map=dict(prereq_map),
            dependents_map=dict(dependents_map),
            elective_group_map=elective_group_map,
            elective_group_remaining=elective_group_remaining,
            required_codes=required_codes,
            total_credits=total_credits,
        )

    # ── Track helpers ────────────────────────────────────────────────────────────
    def get_course_tracks(self, course_code: str) -> frozenset:
        tags = COURSE_TRACK_TAGS.get(course_code)
        if tags:
            return tags
        course = self.courses.get(course_code)
        if course:
            return _keyword_tracks(course.course_name)
        return frozenset({"foundation"})

    def get_curriculum_semester(self, course_code: str) -> int:
        return CURRICULUM_SEMESTER.get(course_code, 5)

    # ── Unlock / critical path ───────────────────────────────────────────────────
    def compute_unlock_scores(self, remaining_codes: set[str]) -> dict[str, int]:
        """Transitive unlock count cho mỗi môn còn lại."""
        dependents_of: dict[str, set[str]] = defaultdict(set)
        for dep_code, prereqs in self.prereq_map.items():
            if dep_code in remaining_codes:
                for p in prereqs:
                    dependents_of[p].add(dep_code)

        memo: dict[str, int] = {}

        def _count(code: str, visiting: frozenset) -> int:
            if code in memo:
                return memo[code]
            direct = dependents_of.get(code, set()) & remaining_codes - visiting
            total = len(direct)
            for dep in direct:
                total += _count(dep, visiting | direct)
            memo[code] = total
            return total

        return {c: _count(c, frozenset()) for c in remaining_codes}

    # ── Elective helpers ─────────────────────────────────────────────────────────
    def is_elective_needed(self, course_code: str) -> bool:
        key = self.elective_group_map.get(course_code)
        return key is not None and self.elective_group_remaining.get(key, 0.0) > 0.0

    def is_elective_extra(self, course_code: str) -> bool:
        key = self.elective_group_map.get(course_code)
        return key is not None and self.elective_group_remaining.get(key, 0.0) <= 0.0

    # ── Feature extraction (dùng chung cho training và inference) ───────────────
    def extract_features(
        self,
        course_code: str,
        # Student state
        student_gpa10: float,
        student_gpa_trend: float,          # -1 giảm / 0 ổn / 1 tăng
        student_credits_earned: float,
        student_sem_count: int,
        # Difficulty stats (từ DB hoặc default)
        course_pass_rate: float | None,
        course_avg_score10: float | None,
        # Context
        unlock_count: int,
        max_unlock_count: int,
        prereq_avg_score: float | None,    # TB điểm các môn tiên quyết (0–10)
        career_track: str | None,          # "ai_data" | "web" | "network_security" | "general"
    ) -> list[float]:
        """
        Trả về vector 14 features cho cặp (sinh viên, môn học).
        Tất cả features đã chuẩn hóa về khoảng hợp lý để GBT hoạt động tốt.
        """
        # ── Student features ──────────────────────────────────────────────────
        gpa = max(0.0, min(10.0, student_gpa10))
        gpa_trend_n = (student_gpa_trend + 1) / 2.0            # → 0/0.5/1
        credits_ratio = max(0.0, min(1.0,
            student_credits_earned / self.total_credits if self.total_credits > 0 else 0.5
        ))
        sem_n = min(1.0, student_sem_count / MAX_CURRICULUM_SEM)

        # ── Course features ───────────────────────────────────────────────────
        course = self.courses.get(course_code)
        credits = float(course.credits or 3) if course else 3.0
        credits_n = min(1.0, credits / 10.0)

        ctdt_sem = self.get_curriculum_semester(course_code)
        ctdt_sem_n = (ctdt_sem - 1) / (MAX_CURRICULUM_SEM - 1)     # 0..1

        pass_rate = course_pass_rate if course_pass_rate is not None else 0.75
        course_avg = course_avg_score10 if course_avg_score10 is not None else 6.5

        # ── Interaction features ───────────────────────────────────────────────
        ability_gap_n = (gpa - course_avg) / 10.0                  # -1..1

        # Curriculum alignment: gần với HK hiện tại sinh viên thì tốt
        estimated_student_sem = student_sem_count + 1
        alignment = max(0.0, 1.0 - abs(ctdt_sem - estimated_student_sem) / MAX_CURRICULUM_SEM)

        # Track match
        course_tracks = self.get_course_tracks(course_code)
        student_track_set = CAREER_TO_TRACKS.get(career_track or "general", set())
        track_match = 1.0 if bool(course_tracks & student_track_set) else 0.0

        # Prereq performance
        prereq_perf = min(1.0, (prereq_avg_score / 10.0)) if prereq_avg_score is not None else 0.7

        # Unlock
        unlock_n = (unlock_count / max_unlock_count) if max_unlock_count > 0 else 0.0
        unlock_n = min(1.0, unlock_n)

        # Required / elective needed
        is_req = 1.0 if course_code in self.required_codes else 0.0
        is_elec_needed = 1.0 if self.is_elective_needed(course_code) else 0.0

        return [
            gpa,
            gpa_trend_n,
            credits_ratio,
            sem_n,
            credits_n,
            ctdt_sem_n,
            pass_rate,
            ability_gap_n,
            alignment,
            track_match,
            prereq_perf,
            unlock_n,
            is_req,
            is_elec_needed,
        ]


# ── Module-level cache: tái sử dụng graph trong cùng request ────────────────────
_graph_cache: dict[str, tuple[float, CurriculumGraph]] = {}
_CACHE_TTL = 300.0   # 5 phút


def get_graph(
    db: Session,
    specialization: str | None,
    completed_codes: set[str] | None = None,
) -> CurriculumGraph:
    """Trả về CurriculumGraph từ cache hoặc build mới."""
    import time
    key = f"{specialization}|{hash(frozenset(completed_codes or set()))}"
    cached = _graph_cache.get(key)
    if cached and (time.time() - cached[0]) < _CACHE_TTL:
        return cached[1]
    graph = CurriculumGraph.from_db(db, specialization, completed_codes)
    _graph_cache[key] = (time.time(), graph)
    # Evict old entries
    if len(_graph_cache) > 50:
        oldest = min(_graph_cache, key=lambda k: _graph_cache[k][0])
        del _graph_cache[oldest]
    return graph


def invalidate_graph_cache() -> None:
    _graph_cache.clear()
