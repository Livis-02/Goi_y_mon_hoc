import csv
import io
import unicodedata
from typing import List, Dict, Any
import pandas as pd
import pdfplumber
def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    text = str(value).strip()
    if not text:
        return True
    return text.lower() in {"nan", "none", "null"}
def _to_float(value: Any):
    if _is_missing(value):
        return None
    try:
        return float(str(value).replace(",", ".").strip())
    except Exception:
        return None
def _safe_get(row: list[Any], idx: int):
    if idx < 0 or idx >= len(row):
        return None
    return row[idx]
def normalize_text(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("\u0111", "d").replace("\u0110", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text
def normalize_header(value: Any) -> str:
    return normalize_text(value).replace("\n", " ")
def find_column_index(headers, keywords):
    for i, head in enumerate(headers):
        h = normalize_header(head)
        if not h:
            continue
        for key in keywords:
            if key in h:
                return i
    return -1
def detect_header_row_index(rows, max_scan=12):
    keyword_groups = [
        ["ma mon", "ma mh", "ma hoc phan", "ma hp"],
        ["ten mon hoc", "ten hoc phan", "ten mon"],
        ["so tin chi", "tin chi", "so tc"],
        ["ket qua", "diem tk (10)", "diem tk (c)"]
    ]
    best_index = 0
    best_score = -1
    for i in range(min(len(rows), max_scan)):
        row = rows[i] or []
        score = 0
        for group in keyword_groups:
            if find_column_index(row, group) >= 0:
                score += 1
        if score > best_score:
            best_score = score
            best_index = i
    return best_index if best_score >= 2 else 0
def parse_xlsx_bytes(data: bytes) -> Dict[str, Any]:
    df = pd.read_excel(io.BytesIO(data), sheet_name=0, engine="openpyxl", header=None)
    rows: List[List[Any]] = df.values.tolist()
    return {
        "rows": rows,
        "student_code": extract_student_code(rows),
        "full_name": extract_full_name(rows),
    }
def parse_csv_bytes(data: bytes) -> Dict[str, Any]:
    # Some score files are xlsx content but named .csv
    if data[:2] == b"PK":
        return parse_xlsx_bytes(data)
    text = None
    for enc in ("utf-8-sig", "cp1258", "latin1"):
        try:
            text = data.decode(enc)
            break
        except Exception:
            continue
    if text is None:
        text = data.decode("utf-8", errors="ignore")
    rows: List[List[Any]] = []
    reader = csv.reader(io.StringIO(text))
    for row in reader:
        if any(str(cell).strip() for cell in row):
            rows.append(row)
    return {
        "rows": rows,
        "student_code": extract_student_code(rows),
        "full_name": extract_full_name(rows),
    }
def parse_pdf_bytes(data: bytes) -> List[List[Any]]:
    rows: List[List[Any]] = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    if any(cell and str(cell).strip() for cell in row or []):
                        rows.append([cell for cell in row])
    if rows:
        return rows
    text_rows = []
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for line in text.splitlines():
                if line.strip():
                    text_rows.append([line.strip()])
    return text_rows
def read_rows_from_upload(filename: str, data: bytes) -> Dict[str, Any]:
    """Đọc file upload và trả về {"rows": [...], "student_code": ...}."""
    lower = filename.lower()
    if lower.endswith(".xlsx") or data[:2] == b"PK":
        return parse_xlsx_bytes(data)
    if lower.endswith(".csv"):
        return parse_csv_bytes(data)
    if lower.endswith(".pdf"):
        pdf_rows = parse_pdf_bytes(data)
        return {
            "rows": pdf_rows,
            "student_code": extract_student_code(pdf_rows),
            "full_name": extract_full_name(pdf_rows),
        }
    raise ValueError("Unsupported file type")
def infer_category(ma_mon: str, bat_buoc: Any, nhom: Any, nhanh: Any) -> str:
    if isinstance(bat_buoc, str) and normalize_text(bat_buoc) == "x":
        return "required"
    tokens = " ".join([normalize_text(ma_mon), normalize_text(nhom), normalize_text(nhanh)])
    if "tu chon" in tokens or "nhom b" in tokens or "nhom c" in tokens:
        return "elective"
    return "conditional"
def extract_curriculum(rows: List[List[Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    header_idx = detect_header_row_index(rows)
    header = rows[header_idx] or []
    idx_ma = find_column_index(header, ["ma mon", "ma mh", "ma hoc phan", "ma hp"])
    idx_ten = find_column_index(header, ["ten mon hoc", "ten hoc phan", "ten mon"])
    idx_tc = find_column_index(header, ["so tin chi", "tin chi", "so tc"])
    idx_bat_buoc = find_column_index(header, ["mon bat buoc", "bat buoc"])
    idx_nhom = find_column_index(header, ["nhom"])
    idx_nhanh = find_column_index(header, ["nhanh"])
    idx_tien_quyet = find_column_index(header, ["tien quyet", "tien quyet mon"])
    idx_hoc_truoc = find_column_index(header, ["hoc truoc", "mon hoc truoc"])
    idx_hk = find_column_index(header, ["hoc ky", "hoc ky khuyen nghi"])
    items = []
    for i in range(header_idx + 1, len(rows)):
        row = rows[i] or []
        if not row:
            continue
        ma = _safe_get(row, idx_ma)
        ten = _safe_get(row, idx_ten)
        tc_raw = _safe_get(row, idx_tc)
        credits = _to_float(tc_raw)
        if _is_missing(ma) or _is_missing(ten) or credits is None or credits <= 0:
            continue
        ma_str = str(ma).strip()
        ten_str = str(ten).strip()
        item = {
            "course_code": ma_str,
            "course_name": ten_str,
            "credits": credits,
            "prerequisite": str(_safe_get(row, idx_tien_quyet)).strip() if not _is_missing(_safe_get(row, idx_tien_quyet)) else None,
            "prior_course": str(_safe_get(row, idx_hoc_truoc)).strip() if not _is_missing(_safe_get(row, idx_hoc_truoc)) else None,
            "recommended_semester": None,
            "category": infer_category(ma_str, _safe_get(row, idx_bat_buoc), _safe_get(row, idx_nhom), _safe_get(row, idx_nhanh)),
        }
        hk_val = _safe_get(row, idx_hk)
        if not _is_missing(hk_val):
            try:
                item["recommended_semester"] = int(hk_val)
            except Exception:
                item["recommended_semester"] = None
        items.append(item)
    return items
def score10_to_4(score10: float) -> float:
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
def _normalize_course_code(value: Any) -> str:
    text = str(value).strip()
    if text.endswith(".0"):
        maybe_int = text[:-2]
        if maybe_int.isdigit():
            return maybe_int
    return text
def extract_student_code(rows: List[List[Any]]) -> "str | None":
    """Tìm mã sinh viên (MSSV) trong 5 dòng đầu file.

    Hỗ trợ 2 dạng:
      - Cùng cell: "Mã sinh viên: 2321060xxx"
      - Cell kế: ["Mã sinh viên", "2321060xxx"]
    """
    if not rows:
        return None
    _mssv_keywords = ("ma sinh vien", "mssv", "so sinh vien", "ma so sinh vien", "masv")
    for row in rows[:5]:
        if not row:
            continue
        for i, cell in enumerate(row):
            cell_text = normalize_text(cell)
            if any(kw in cell_text for kw in _mssv_keywords):
                # Case 1: value in same cell after ":"
                raw = str(cell or "").strip()
                if ":" in raw:
                    candidate = raw.split(":", 1)[-1].strip()
                    if candidate and not _is_missing(candidate):
                        return candidate
                # Case 2: value in next cell
                for j in range(i + 1, min(i + 3, len(row))):
                    candidate = str(row[j] or "").strip()
                    if candidate and not _is_missing(candidate):
                        return candidate
    return None


def extract_full_name(rows: List[List[Any]]) -> "str | None":
    """Tìm họ và tên sinh viên trong 5 dòng đầu file.

    Hỗ trợ 2 dạng:
      - Cùng cell: "Họ và tên: Nguyễn Văn A"
      - Cell kế: ["Họ và tên", "Nguyễn Văn A"]
    """
    if not rows:
        return None
    _name_keywords = ("ho va ten", "ho ten", "hoten", "full name", "fullname", "ten sinh vien")
    for row in rows[:5]:
        if not row:
            continue
        for i, cell in enumerate(row):
            cell_text = normalize_text(cell)
            if any(kw in cell_text for kw in _name_keywords):
                raw = str(cell or "").strip()
                if ":" in raw:
                    candidate = raw.split(":", 1)[-1].strip()
                    if candidate and not _is_missing(candidate):
                        return candidate
                for j in range(i + 1, min(i + 3, len(row))):
                    candidate = str(row[j] or "").strip()
                    if candidate and not _is_missing(candidate):
                        return candidate
    return None


def extract_tich_luy(rows: List[List[Any]]) -> "float | None":
    """Extract 'Số tín chỉ tích lũy' — return MAX value (final cumulative total).
    Portal exports semesters newest-first; test data is oldest-first.
    TC tích lũy is monotonically non-decreasing, so MAX is always correct."""
    max_val = None
    for row in rows:
        if not row:
            continue
        for i, cell in enumerate(row):
            cell_text = normalize_text(cell)
            if "so tin chi tich luy" in cell_text:
                raw = str(cell or "").strip()
                if ":" in raw:
                    val = _to_float(raw.split(":")[-1].strip())
                    if val is not None:
                        if max_val is None or val > max_val:
                            max_val = val
                        continue
                for j in range(i + 1, len(row)):
                    val = _to_float(row[j])
                    if val is not None:
                        if max_val is None or val > max_val:
                            max_val = val
                        break
    return max_val


def extract_grades(rows: List[List[Any]]) -> List[Dict[str, Any]]:
    if not rows:
        return []
    header_idx = detect_header_row_index(rows)
    header = rows[header_idx] or []
    idx_ma = find_column_index(header, ["ma mon", "ma mh", "ma hoc phan", "ma hp"])
    idx_ten = find_column_index(header, ["ten mon hoc", "ten hoc phan", "ten mon"])
    idx_tc = find_column_index(header, ["so tin chi", "tin chi", "so tc"])
    idx_diem10 = find_column_index(header, ["diem tk (10)", "diem tong ket (10)", "diem he 10"])
    idx_diem4 = find_column_index(header, ["diem tk (4)", "diem tong ket (4)", "diem he 4"])
    idx_diemc = find_column_index(header, ["diem tk (c)", "diem tk c", "diem chu"])
    idx_ket_qua = find_column_index(header, ["ket qua"])
    grades = []
    current_term = None
    for i in range(header_idx + 1, len(rows)):
        row = rows[i] or []
        if not row:
            continue
        first_cell = normalize_text(_safe_get(row, 0))
        if first_cell.startswith("hoc ky"):
            current_term = str(_safe_get(row, 0)).strip()
            continue
        ma = _safe_get(row, idx_ma)
        ten = _safe_get(row, idx_ten)
        credits = _to_float(_safe_get(row, idx_tc))
        if _is_missing(ma) or _is_missing(ten) or credits is None or credits <= 0:
            continue
        score10 = _to_float(_safe_get(row, idx_diem10))
        score4 = _to_float(_safe_get(row, idx_diem4))
        letter = None
        diemc_val = _safe_get(row, idx_diemc)
        if not _is_missing(diemc_val):
            letter = str(diemc_val).strip()
        passed = False
        ketqua_val = _safe_get(row, idx_ket_qua)
        if not _is_missing(ketqua_val):
            ket = normalize_text(ketqua_val)
            passed = "dat" in ket and "khong" not in ket
        elif score10 is not None:
            passed = score10 >= 4.0
        elif letter:
            passed = normalize_text(letter) not in ("f", "i", "x")
        if score4 is None and score10 is not None:
            score4 = score10_to_4(score10)
        grades.append(
            {
                "course_code": _normalize_course_code(ma),
                "course_name": str(ten).strip(),
                "credits": credits,
                "term": current_term,
                "score10": score10,
                "score4": score4,
                "letter": letter,
                "passed": passed,
            }
        )
    return grades
