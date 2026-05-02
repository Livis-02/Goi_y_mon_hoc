# -*- coding: utf-8 -*-
"""
generate_demo_k14.py — Sinh 3 file XLSX bảng điểm cho 3 SV K14 demo.

Output:
  data/demo/sv14010_diem.xlsx — đã học HK1-3, GPA tốt (3.2+)
  data/demo/sv14011_diem.xlsx — đã học HK1-2, GPA trung bình (2.8)
  data/demo/sv14012_diem.xlsx — chỉ HK1, GPA cao (3.5+, mới khôi phục)

Sử dụng để admin upload qua /admin/grades/import (tab quản lý SV → "..." → Upload điểm).

Chạy: python -m backend.scripts.generate_demo_k14
"""
import sys
from pathlib import Path

# Import TRƯỚC khi wrap stdout (vì module kia cũng wrap → tránh double-wrap close).
# Reuse helpers từ generate_sample_data.py để đỡ duplicate logic.
from backend.scripts.generate_sample_data import (
    write_xlsx, hk1_common, hk2_common, hk3_common,
)

OUT_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "demo"
OUT_DIR.mkdir(parents=True, exist_ok=True)


def gen_sv14010():
    """SV K14 đã học HK1-3, GPA ~3.2 (tốt)."""
    semesters = [
        (1, hk1_common(gpa_base=8.5)),   # HK1: ~8.0-9.0 → GPA ~3.5
        (2, hk2_common(gpa_base=7.8)),   # HK2: ~7.5-8.3 → GPA ~3.3
        (4, hk3_common(gpa_base=8.0)),   # HK3 (idx 4 trong CTDT cũ): ~7.7-8.5
    ]
    return write_xlsx(OUT_DIR / "sv14010_diem.xlsx", "sv14010", semesters)


def gen_sv14011():
    """SV K14 đã học HK1-2, GPA ~2.8 (trung bình)."""
    semesters = [
        (1, hk1_common(gpa_base=7.0)),   # HK1: 6.5-7.5 → GPA ~2.7
        (2, hk2_common(gpa_base=6.8)),   # HK2: 6.3-7.3 → GPA ~2.5
    ]
    return write_xlsx(OUT_DIR / "sv14011_diem.xlsx", "sv14011", semesters)


def gen_sv14012():
    """SV K14 mới khôi phục, chỉ HK1, GPA cao (3.5+)."""
    semesters = [
        (1, hk1_common(gpa_base=9.0)),   # HK1: 8.7-9.5 → GPA gần 4.0
    ]
    return write_xlsx(OUT_DIR / "sv14012_diem.xlsx", "sv14012", semesters)


def main():
    print(f"[demo_k14] Output → {OUT_DIR}\n")
    print("Generated files:")
    gen_sv14010()
    gen_sv14011()
    gen_sv14012()
    print("\nDone. Upload qua admin UI:")
    print("  Sinh viên → SV row '...' → Upload điểm → chọn file tương ứng.")


if __name__ == "__main__":
    main()
