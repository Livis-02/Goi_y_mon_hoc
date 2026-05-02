# -*- coding: utf-8 -*-
"""
seed_demo_full.py — Seed dataset đầy đủ cho demo hội đồng.

Tạo:
  • 6 advisors (1 head/CN + 2 GV chung)
  • 18 sinh viên K14 phân bổ qua 6 CN + đại cương
  • Bảng điểm XLSX cho 1 số SV (source='admin' khi admin upload)

Output:
  data/demo/seed_passwords.txt — danh sách MK mặc định
  data/demo/svXXX_diem.xlsx    — bảng điểm để admin upload

Chạy:
  python -m backend.scripts.seed_demo_full

Idempotent: SV/advisor đã tồn tại → bỏ qua, không fail.
"""
import sys
from pathlib import Path

# Reuse helpers TRƯỚC khi wrap stdout (sync với generate_demo_k14.py)
from backend.scripts.generate_sample_data import (
    write_xlsx,
    hk1_common, hk2_common, hk3_common, hk4_common, hk5_common, hk6_common,
    hk7_khmt, hk7_httt, hk7_mmt, hk7_cnpm,
)
from backend.db.db import SessionLocal
from backend.db import models
from backend.main import _hash_temp_password, _hash_password, _IMPORT_VALID_SPECIALIZATIONS

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)
PWD_FILE = OUT_DIR / "seed_passwords.txt"

# ── Advisor ──────────────────────────────────────────────────────────────
ADVISORS = [
    # (teacher_code, full_name, managed_specialization, is_head)
    ("KHMT001", "Nguyễn Thị Hậu",   "7480201_07", True),   # Trưởng KHMT
    ("KHMT002", "Trần Văn Nam",      "7480201_07", False),
    ("HTTT001", "Lê Thị Hà",         "7480201_09", True),   # Trưởng HTTT
    ("MMT001",  "Phạm Văn Khải",     "7480201_06", True),   # Trưởng MMT
    ("CNPM001", "Đỗ Thị Lan",        "7480201_05", True),   # Trưởng CNPM
    ("GV001",   "Hoàng Thị Mai",     None,         False),  # Đại cương
]

# ── Sinh viên K14 ────────────────────────────────────────────────────────
# (mssv, full_name, specialization, gpa_base — GPA target để gen điểm)
STUDENTS = [
    # KHMT (5 SV) — đã có CN
    ("sv14001", "Dương Minh Long",    "7480201_07", 8.5),  # giỏi
    ("sv14002", "Ngô Thị Kim",        "7480201_07", 7.5),  # khá
    ("sv14003", "Phan Thảo My",       "7480201_07", 9.0),  # xuất sắc
    ("sv14004", "Trần Văn Hải",       "7480201_07", 6.8),  # trung bình
    ("sv14005", "Bùi Thị Lan",        "7480201_07", 7.2),

    # HTTT (3 SV)
    ("sv14010", "Trần Thị Bình",      "7480201_09", 8.0),
    ("sv14011", "Lê Văn Cường",       "7480201_09", 7.0),
    ("sv14012", "Phạm Thị Diệu",      "7480201_09", 8.5),

    # MMT (3 SV)
    ("sv14020", "Vũ Văn Hoàng",       "7480201_06", 7.8),
    ("sv14021", "Đinh Thị Hương",     "7480201_06", 6.5),  # nguy cơ thấp
    ("sv14022", "Hồ Văn Tuấn",        "7480201_06", 8.2),

    # CNPM (2 SV)
    ("sv14030", "Nguyễn Văn Phúc",    "7480201_05", 8.0),
    ("sv14031", "Mai Thị Quỳnh",      "7480201_05", 7.5),

    # Đại cương / chưa CN (5 SV K14 đầu)
    ("sv14040", "Cao Văn Sáng",       None,         8.0),
    ("sv14041", "Lý Thị Tâm",         None,         7.3),
    ("sv14042", "Tô Văn Uy",          None,         6.0),  # thấp
    ("sv14043", "Trương Thị Vy",      None,         8.7),
    ("sv14044", "Phùng Văn Xuân",     None,         7.0),
]


def seed_advisors(db):
    """Tạo advisor mới, skip nếu đã có. Trả dict teacher_code → password."""
    import random as _rnd
    pw_map = {}
    for tc, name, spec, is_head in ADVISORS:
        existing = db.query(models.User).filter(models.User.username == tc).first()
        if existing:
            print(f"  [skip] advisor {tc} đã tồn tại")
            continue
        pw = str(_rnd.randint(100000, 999999))
        adv = models.User(
            username=tc,
            full_name=name,
            password_hash=_hash_temp_password(pw),
            role="advisor",
            managed_specialization=spec,
            teacher_code=tc,
            is_head_of_department=is_head,
            is_first_login=False,  # admin tạo trực tiếp, không cần setup
            email=f"{tc.lower()}@uni.edu",  # email mặc định cho advisor
            default_password=pw,
        )
        db.add(adv)
        pw_map[tc] = pw
        print(f"  [+] advisor {tc} ({name}) · CN={spec or 'chung'} · head={is_head}")
    db.commit()
    return pw_map


def seed_students(db):
    """Tạo SV mới + auto-assign advisor theo CN."""
    import random as _rnd
    from backend.main import assign_advisor_for_student
    pw_map = {}
    for mssv, name, spec, _gpa in STUDENTS:
        existing = db.query(models.User).filter(models.User.username == mssv).first()
        if existing:
            print(f"  [skip] SV {mssv} đã tồn tại")
            continue
        pw = str(_rnd.randint(100000, 999999))
        sv = models.User(
            username=mssv,
            full_name=name,
            password_hash=_hash_temp_password(pw),
            role="student",
            specialization=spec if spec in _IMPORT_VALID_SPECIALIZATIONS else None,
            cohort="14",
            is_first_login=True,  # buộc setup khi đăng nhập đầu
            default_password=pw,
        )
        db.add(sv)
        db.flush()
        if sv.specialization:
            try:
                assign_advisor_for_student(db, sv.id, sv.specialization)
            except Exception:
                pass
        pw_map[mssv] = pw
        print(f"  [+] SV {mssv} ({name}) · CN={spec or 'chưa CN'}")
    db.commit()
    return pw_map


def gen_grade_files():
    """Tạo file XLSX bảng điểm cho 6 SV mẫu (admin sẽ upload)."""
    print("\n=== Generate grade XLSX files (admin upload sau) ===")

    # SV đã học HK1-3 (đại cương đầy đủ)
    profiles = [
        ("sv14001", 8.5, [(1, hk1_common(8.5)), (2, hk2_common(8.5)), (4, hk3_common(8.5))]),
        ("sv14002", 7.5, [(1, hk1_common(7.5)), (2, hk2_common(7.5)), (4, hk3_common(7.5))]),
        ("sv14010", 8.0, [(1, hk1_common(8.0)), (2, hk2_common(8.0)), (4, hk3_common(8.0))]),
        ("sv14011", 7.0, [(1, hk1_common(7.0)), (2, hk2_common(7.0))]),  # mới HK2
        ("sv14020", 7.8, [(1, hk1_common(7.8)), (2, hk2_common(7.8)), (4, hk3_common(7.8))]),
        ("sv14021", 6.5, [(1, hk1_common(6.5)), (2, hk2_common(6.5))]),  # GPA thấp
    ]
    for mssv, _gpa, semesters in profiles:
        write_xlsx(OUT_DIR / f"{mssv}_diem.xlsx", mssv, semesters)


def write_passwords(adv_pw, sv_pw):
    lines = ["# Demo passwords — KHÔNG commit lên git!", "", "## Cố vấn", ""]
    for tc, _name, _, _ in ADVISORS:
        if tc in adv_pw:
            lines.append(f"  {tc}: {adv_pw[tc]}")
    lines += ["", "## Sinh viên", ""]
    for mssv, _name, _, _ in STUDENTS:
        if mssv in sv_pw:
            lines.append(f"  {mssv}: {sv_pw[mssv]}")
    PWD_FILE.write_text("\n".join(lines), encoding="utf-8")
    print(f"\n[passwords] đã ghi vào {PWD_FILE}")


def main():
    print(f"[seed] Output → {OUT_DIR}\n")
    db = SessionLocal()
    try:
        print("=== Tạo cố vấn ===")
        adv_pw = seed_advisors(db)
        print("\n=== Tạo sinh viên K14 ===")
        sv_pw = seed_students(db)
    finally:
        db.close()

    gen_grade_files()
    write_passwords(adv_pw, sv_pw)

    print("\n========== HƯỚNG DẪN DEMO ==========")
    print("1. Đăng nhập admin (admin/admin) → upload các file *_diem.xlsx (Quản lý SV → ... → Upload điểm)")
    print("2. Đăng nhập 1 advisor (vd KHMT001) — xem badges + tab Bảng điểm")
    print("3. Đăng nhập 1 SV (vd sv14001) → setup email + password → xem lộ trình + bảng điểm")
    print(f"\nMật khẩu mặc định: xem {PWD_FILE}")


if __name__ == "__main__":
    main()
