from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib import request

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.db import models
from backend.core.academic_engine import (
    build_progress_snapshot,
    build_recommendations,
    _get_graduation_threshold,
)


ALLOWED_INTENTS = {
    "recommend", "progress", "career", "explain", "general",
    "graduation", "internship", "thesis", "prereq", "course_info", "greeting",
}


@dataclass
class ChatIntentResult:
    intent: str
    answer: str
    suggestions: list[str]


def _normalize(text: str) -> str:
    return " ".join((text or "").lower().strip().split())


def detect_intent_rule(message: str) -> str:
    import unicodedata

    def _strip(t: str) -> str:
        t = t.replace("đ", "d").replace("Đ", "d")
        return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))

    mn = _strip(_normalize(message))

    # Thesis trước graduation vì "đồ án tốt nghiệp" chứa cả hai keyword
    if any(k in mn for k in ["do an tot nghiep", "luan van", "dieu kien lam do an", "bao ve do an"]):
        return "thesis"
    if any(k in mn for k in ["do an"]) and not any(k in mn for k in ["tot nghiep", "ra truong"]):
        return "thesis"
    if any(k in mn for k in ["tot nghiep", "ra truong", "du dieu kien ra truong"]):
        return "graduation"
    if any(k in mn for k in ["thuc tap", "thuc hanh doanh nghiep", "dieu kien thuc tap"]):
        return "internship"
    if any(k in mn for k in ["tien quyet", "dieu kien hoc", "mon nao can hoc truoc", "prereq"]):
        return "prereq"
    # course_info phải check trước recommend vì prompt "Hỏi AI" có thể chứa "gợi ý"
    if any(k in mn for k in [
        "day ve gi", "day gi", "hoc duoc gi", "mon do la gi", "noi dung mon",
        "mon nay gom", "bao gom gi", "kien thuc gi", "ky nang gi",
        "gioi thieu mon", "mo ta mon", "thong tin mon", "ky nang gi",
    ]):
        return "course_info"
    if any(k in mn for k in ["goi y", "nen hoc", "mon nao", "recommend", "hoc them gi"]):
        return "recommend"
    if any(k in mn for k in ["tien do", "%", "con thieu", "progress", "hoan thanh", "bao nhieu tin chi"]):
        return "progress"
    if any(k in mn for k in ["nghe nghiep", "career", "dinh huong", "hop nganh", "lam gi", "huong di"]):
        return "career"
    if any(k in mn for k in ["tai sao", "vi sao", "giai thich", "explain", "ly do"]):
        return "explain"
    # Greeting — phải check sau cùng để không conflict với các intent khác
    if any(k in mn for k in [
        "hello", "hi ", "hey", "chao", "xin chao", "good morning", "good afternoon",
        "good evening", "sup", "yo ", "howdy", "greet",
    ]) or mn in {"hi", "hey", "yo", "chao", "chao ban", "xin chao"}:
        return "greeting"
    return "general"


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _gemini_chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 500) -> str | None:
    """Google Gemini 2.0 Flash — free tier, primary LLM."""
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    # Convert OpenAI-style messages to Gemini format
    system_text = ""
    contents: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            system_text = m["content"]
        elif m["role"] == "user":
            contents.append({"role": "user", "parts": [{"text": m["content"]}]})
        elif m["role"] == "assistant":
            contents.append({"role": "model", "parts": [{"text": m["content"]}]})

    if not contents:
        return None

    payload: dict = {
        "contents": contents,
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    if system_text:
        payload["system_instruction"] = {"parts": [{"text": system_text}]}

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    req = request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except request.HTTPError as e:
        if e.code == 429:
            import sys
            print("[Gemini chat] Rate limit (429) — đổi API key hoặc đợi", file=sys.stderr)
        return None
    except Exception:
        return None


def _groq_chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 500) -> str | None:
    """Groq free tier — llama-3.3-70b, OpenAI-compatible API."""
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    req = request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "Mozilla/5.0 (compatible; AcademicAdvisor/1.0)",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _openai_chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 500) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    req = request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _claude_chat_with_history(messages: list[dict]) -> str | None:
    """Claude API supporting full conversation history (system + multi-turn)."""
    # Đọc cả ANTHROPIC_API_KEY (chuẩn) + CLAUDE_API_KEY (tên user thường đặt)
    api_key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    if not api_key:
        return None

    system_content = ""
    chat_messages: list[dict] = []
    for m in messages:
        if m["role"] == "system":
            system_content = m["content"]
        else:
            chat_messages.append({"role": m["role"], "content": m["content"]})

    if not chat_messages:
        return None

    payload = {
        "model": (os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL")
                  or "claude-haiku-4-5-20251001").strip(),
        "max_tokens": 500,
        "system": system_content,
        "messages": chat_messages,
    }
    req = request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"].strip()
    except Exception:
        return None


# ── Student context cache ─────────────────────────────────────────────────────
_CTX_CACHE_TTL = 300  # 5 phút
_ctx_cache: dict[int, dict] = {}  # { user_id: { ctx, suggestions, ts } }


def invalidate_student_context_cache(user_id: int) -> None:
    """Gọi sau khi upload điểm hoặc thay đổi profile để buộc rebuild context."""
    _ctx_cache.pop(user_id, None)


# ── Student context builder ───────────────────────────────────────────────────

def _build_student_context_prompt(db: Session, user_id: int) -> tuple[str, list[str]]:
    """Fetch all relevant student data and format as a context block for the LLM system prompt.
    Returns (context_string, suggestion_course_codes). Result cached 5 minutes per user."""
    cached = _ctx_cache.get(user_id)
    if cached and (datetime.now(timezone.utc) - cached["ts"]).total_seconds() < _CTX_CACHE_TTL:
        return cached["ctx"], cached["suggestions"]

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return "Không tìm thấy thông tin sinh viên.", []

    try:
        progress = build_progress_snapshot(db, user_id)
    except Exception:
        progress = {}

    try:
        recs = build_recommendations(db, user_id, limit=5)
        rec_items = recs.get("recommendations", [])
    except Exception:
        rec_items = []

    try:
        cfg = db.query(models.SystemConfig).filter(models.SystemConfig.key == "active_semester").first()
        active_semester = cfg.value if cfg else None
        if active_semester:
            offerings = db.query(models.SemesterOffering).filter(
                models.SemesterOffering.semester_label == active_semester,
                models.SemesterOffering.is_open == True,
            ).all()
            available_codes = [o.course_code for o in offerings]
        else:
            available_codes = []
    except Exception:
        active_semester = None
        available_codes = []

    _career_labels = {
        "web": "Phát triển Web",
        "ai_data": "AI / Dữ liệu",
        "network_security": "Mạng / An ninh mạng",
        "general": "Tổng hợp",
    }

    lines: list[str] = []

    # --- Student info ---
    lines.append("=== THÔNG TIN SINH VIÊN ===")
    lines.append(f"Họ tên: {user.full_name or user.username}")
    lines.append(f"Chuyên ngành (CN ĐT): {user.specialization or 'Chưa được phân công — đang ở năm 1-2'}")
    lines.append("Định hướng nghề nghiệp: xem qua bảng UserCareerChoice")  # career_goal field deprecated

    # Primary career path (từ trang Career Hub — khác career_goal cũ, là path cụ thể như "Backend Dev")
    try:
        choice = db.query(models.UserCareerChoice).filter(
            models.UserCareerChoice.user_id == user_id,
        ).first()
        if choice and choice.primary_path_id:
            cp = db.query(models.CareerPath).filter(
                models.CareerPath.id == choice.primary_path_id
            ).first()
            if cp:
                lines.append(f"Hướng nghề chính (đã chọn ở Career Hub): {cp.name}")
    except Exception:
        pass

    # Deprecated 2026-05-05: user.career_skills field dropped
    try:
        pass
    except Exception:
        pass

    avg10 = progress.get("avg_score10")
    avg4 = progress.get("avg_score4")
    if avg10 is not None:
        gpa_str = f"GPA hệ 10: {avg10:.2f}"
        if avg4 is not None:
            gpa_str += f" | GPA hệ 4: {avg4:.2f}"
        lines.append(gpa_str)
    else:
        lines.append("GPA: Chưa có dữ liệu điểm")

    earned = progress.get("earned_credits", 0)
    total = progress.get("total_credits", _get_graduation_threshold(db))
    pct = progress.get("completion_percent", 0)
    lines.append(f"Tín chỉ tích lũy: {earned}/{total} ({pct}%)")

    terms = progress.get("terms_studied")
    est = progress.get("estimated_terms_remaining")
    if terms:
        lines.append(f"Số học kỳ đã học: {terms}")
    if est:
        lines.append(f"Ước tính còn khoảng: {est} học kỳ nữa")

    # --- Graduation status ---
    lines.append("")
    lines.append("=== TIẾN ĐỘ TỐT NGHIỆP ===")
    lines.append(f"Đủ điều kiện tốt nghiệp: {'Có ✓' if progress.get('graduation_ready') else 'Chưa'}")
    internship_status = (
        "Đã hoàn thành ✓" if progress.get("internship_done")
        else ("Đủ điều kiện đăng ký ✓" if progress.get("internship_eligible") else "Chưa đủ điều kiện")
    )
    thesis_status = (
        "Đã hoàn thành ✓" if progress.get("thesis_done")
        else ("Đủ điều kiện đăng ký ✓" if progress.get("thesis_eligible") else "Chưa đủ điều kiện")
    )
    lines.append(f"Thực tập doanh nghiệp: {internship_status}")
    lines.append(f"Đồ án tốt nghiệp: {thesis_status}")

    # --- Elective groups ---
    elective_groups = progress.get("elective_groups", [])
    if elective_groups:
        lines.append("")
        lines.append("=== NHÓM TỰ CHỌN ===")
        for g in elective_groups:
            status = "Đã đủ ✓" if g.get("completed") else f"còn thiếu {g.get('remaining_credits', 0):.0f} TC"
            spec = g.get("specialization") or ""
            gtype = g.get("group_type", "?")
            earned_g = g.get("earned_credits", 0)
            min_g = g.get("min_credits_required", 0)
            lines.append(f"- Nhóm {gtype} ({spec}): {earned_g:.0f}/{min_g:.0f} TC — {status}")

    # --- Top recommendations ---
    if rec_items:
        lines.append("")
        lines.append("=== GỢI Ý MÔN HỌC ƯU TIÊN (hệ thống đề xuất) ===")
        for i, r in enumerate(rec_items[:5], 1):
            cat = r.get("category", "required")
            cat_label = {"required": "Bắt buộc", "elective": "Tự chọn", "internship": "Thực tập", "thesis": "Đồ án"}.get(cat, cat)
            avail = "" if r.get("available_this_term", True) else " ⚠ Không mở kỳ này"
            lines.append(f"{i}. {r['course_name']} ({r['course_code']}) — {r.get('credits', 0):.0f} TC [{cat_label}]{avail}")
            reasons = r.get("reasons", [])
            if reasons:
                lines.append(f"   Lý do: {reasons[0]}")

    # --- Remaining courses (capped) ---
    remaining = progress.get("remaining_course_items", [])
    if remaining:
        lines.append("")
        lines.append(f"=== CÁC MÔN CÒN CHƯA HOÀN THÀNH ({len(remaining)} môn) ===")
        for c in remaining[:25]:
            elective_tag = f" [Tự chọn {c.get('elective_group_type', '')}]" if c.get("is_elective") else ""
            lines.append(f"- {c['course_name']} ({c['course_code']}) {c.get('credits', 0):.0f} TC{elective_tag}")
        if len(remaining) > 25:
            lines.append(f"... và {len(remaining) - 25} môn khác")

    # --- Semester info ---
    lines.append("")
    if active_semester:
        lines.append(f"=== HỌC KỲ ĐANG MỞ: {active_semester} ===")
        if available_codes:
            lines.append(f"Môn đang mở: {', '.join(available_codes)}")
        else:
            lines.append("(Không có môn nào được cấu hình mở trong học kỳ này)")
    else:
        lines.append("=== HỌC KỲ HIỆN TẠI: Chưa được thiết lập ===")

    # --- Career path reference (always included so LLM can answer about any direction) ---
    lines.append("")
    lines.append("=== CÁC ĐỊNH HƯỚNG NGHỀ NGHIỆP (để tư vấn khi sinh viên hỏi) ===")
    lines.append("1. Lập trình Web (web): HTML/CSS/JS, React/Vue/Angular, Node.js, PHP/Laravel, REST API, Docker.")
    lines.append("   Môn liên quan: Lập trình web, Cơ sở dữ liệu, Mạng máy tính, Công nghệ phần mềm.")
    lines.append("   Phù hợp: thích làm sản phẩm cụ thể, thiên về frontend/backend, thị trường việc làm rộng.")
    lines.append("2. AI / Dữ liệu (ai_data): Python, Machine Learning, Deep Learning, Data Science, SQL/NoSQL, Spark.")
    lines.append("   Môn liên quan: Trí tuệ nhân tạo, Học máy, Xử lý ảnh, Khai phá dữ liệu, Giải tích, Đại số.")
    lines.append("   Phù hợp: GPA cao (≥7.5/10), thích toán/thống kê, muốn nghiên cứu hoặc làm Data Engineer/Scientist.")
    lines.append("3. An toàn mạng (network_security): Bảo mật hệ thống, Kiểm thử xâm nhập, Mã hóa, Firewall, SOC.")
    lines.append("   Môn liên quan: An toàn thông tin, Mạng máy tính, Hệ điều hành, Lập trình hệ thống.")
    lines.append("   Phù hợp: thích phân tích lỗ hổng, muốn làm Security Engineer/Pentester.")
    lines.append("4. Tổng hợp (general): Cân bằng giữa các hướng, phù hợp nếu chưa xác định rõ hoặc muốn linh hoạt.")
    lines.append("Định hướng nghề nghiệp: chưa xác định")  # career_goal field deprecated
    lines.append("LƯU Ý: Nếu sinh viên hỏi về một định hướng khác, hãy so sánh với tình hình hiện tại và tư vấn cụ thể.")

    suggestion_codes = [r["course_code"] for r in rec_items]
    result_ctx = "\n".join(lines)

    # Store in cache, evict if too large
    _ctx_cache[user_id] = {"ctx": result_ctx, "suggestions": suggestion_codes, "ts": datetime.now(timezone.utc)}
    if len(_ctx_cache) > 500:
        oldest = min(_ctx_cache, key=lambda k: _ctx_cache[k]["ts"])
        del _ctx_cache[oldest]

    return result_ctx, suggestion_codes


def _build_advisor_context_prompt(db: Session, user_id: int) -> str:
    """Context block cho AI khi user là cố vấn học tập.

    Gồm: thông tin GV, danh sách SV phụ trách, phân bố trạng thái (risk),
    GPA trung bình nhóm, SV nguy cơ cao, ghi chú gần nhất.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return "Không tìm thấy thông tin cố vấn."

    lines: list[str] = []
    lines.append("=== THÔNG TIN CỐ VẤN ===")
    lines.append(f"Họ tên: {user.full_name or user.username}")
    lines.append(f"Mã GV: {user.teacher_code or '—'}")
    dept = user.managed_specialization or "Đại cương / chưa phân công"
    lines.append(f"Bộ môn phụ trách: {dept}")
    lines.append("Vai trò: Cố vấn học tập")

    # Danh sách SV phụ trách
    assn_rows = db.query(models.AdvisorAssignment).filter(
        models.AdvisorAssignment.advisor_id == user_id
    ).all()
    student_ids = [a.student_id for a in assn_rows]
    students = db.query(models.User).filter(models.User.id.in_(student_ids)).all() if student_ids else []

    lines.append("")
    lines.append(f"=== NHÓM SINH VIÊN PHỤ TRÁCH ({len(students)} SV) ===")
    if not students:
        lines.append("Chưa có sinh viên được phân công.")
    else:
        high_risk: list[str] = []
        needs_att: list[str] = []
        normal: list[str] = []
        gpa_vals: list[float] = []
        completion_vals: list[float] = []
        for s in students[:40]:
            try:
                snap = build_progress_snapshot(db, s.id)
            except Exception:
                snap = {}
            g4 = snap.get("avg_score4")
            cpct = snap.get("completion_percent")
            if g4 is not None:
                gpa_vals.append(float(g4))
            if cpct is not None:
                completion_vals.append(float(cpct))
            # Classify
            est = snap.get("estimated_terms_remaining")
            label = f"{s.full_name or s.username} (GPA {g4:.2f}" if g4 is not None else f"{s.full_name or s.username} (GPA ?"
            label += f", {snap.get('earned_credits',0)}TC)"
            if g4 is not None and g4 < 2.0:
                high_risk.append(label)
            elif est is not None and est > 10:
                needs_att.append(label)
            elif g4 is not None and g4 < 2.5:
                needs_att.append(label)
            else:
                normal.append(label)
        avg_gpa = sum(gpa_vals) / len(gpa_vals) if gpa_vals else None
        avg_cpl = sum(completion_vals) / len(completion_vals) if completion_vals else None
        if avg_gpa is not None:
            lines.append(f"GPA trung bình nhóm (hệ 4): {avg_gpa:.2f}")
        if avg_cpl is not None:
            lines.append(f"Tiến độ tích lũy TB: {avg_cpl:.1f}%")
        lines.append(f"Phân bố: {len(high_risk)} nguy cơ cao | {len(needs_att)} cần chú ý | {len(normal)} bình thường")
        if high_risk:
            lines.append("")
            lines.append("SV NGUY CƠ CAO (ưu tiên tư vấn):")
            for name in high_risk[:8]:
                lines.append(f"  - {name}")
        if needs_att:
            lines.append("SV CẦN CHÚ Ý:")
            for name in needs_att[:8]:
                lines.append(f"  - {name}")

    # Ghi chú gần nhất
    recent_notes = db.query(models.AdvisorNote).filter(
        models.AdvisorNote.advisor_id == user_id
    ).order_by(models.AdvisorNote.created_at.desc()).limit(5).all()
    if recent_notes:
        lines.append("")
        lines.append("=== GHI CHÚ GẦN NHẤT ===")
        for n in recent_notes:
            sv = db.query(models.User).filter(models.User.id == n.student_id).first()
            sv_name = sv.full_name if sv else f"SV#{n.student_id}"
            content = (n.content or "")[:120]
            lines.append(f"  [{sv_name}] {content}")

    lines.append("")
    lines.append("=== VAI TRÒ CỦA BẠN KHI TƯ VẤN ===")
    lines.append("Bạn đang hỗ trợ cố vấn học tập ra quyết định. Trả lời phải:")
    lines.append("- Dựa trên dữ liệu thật của nhóm SV bên trên, không bịa tên SV")
    lines.append("- Gợi ý hành động cụ thể (VD: họp với SV X để bàn kế hoạch học lại)")
    lines.append("- Tôn trọng quyền riêng tư: không nói về SV không có trong danh sách")
    lines.append("- Trả lời tiếng Việt, súc tích, có cấu trúc (bullet khi cần)")
    return "\n".join(lines)


def _build_admin_context_prompt(db: Session) -> str:
    """Context block cho admin. Gồm tổng quan hệ thống: cohort, chuyên ngành, thống kê."""
    from sqlalchemy import func as _sqlfunc
    lines: list[str] = []
    lines.append("=== TỔNG QUAN HỆ THỐNG EDUGUIDE ===")
    total_users = db.query(_sqlfunc.count(models.User.id)).scalar() or 0
    total_students = db.query(_sqlfunc.count(models.User.id)).filter(models.User.role == "student").scalar() or 0
    total_advisors = db.query(_sqlfunc.count(models.User.id)).filter(models.User.role == "advisor").scalar() or 0
    total_courses = db.query(_sqlfunc.count(models.Course.id)).scalar() or 0
    total_grades = db.query(_sqlfunc.count(models.UserGrade.id)).scalar() or 0
    lines.append(f"Người dùng: {total_users} ({total_students} SV, {total_advisors} GV)")
    lines.append(f"Môn học: {total_courses} | Bản ghi điểm: {total_grades}")

    # Phân bố cohort (K20, K21, K22...)
    lines.append("")
    lines.append("=== PHÂN BỐ KHÓA ===")
    students = db.query(models.User).filter(models.User.role == "student").all()
    cohort_count: dict[str, int] = {}
    for s in students:
        u = s.username or ""
        cohort = u[2:4] if u.upper().startswith("SV") and len(u) >= 4 else u[:2]
        if cohort and cohort.isdigit():
            cohort_count[f"K{cohort}"] = cohort_count.get(f"K{cohort}", 0) + 1
    for k, v in sorted(cohort_count.items()):
        lines.append(f"  {k}: {v} SV")

    # Phân bố chuyên ngành
    lines.append("")
    lines.append("=== PHÂN BỐ CHUYÊN NGÀNH ===")
    spec_count: dict[str, int] = {}
    for s in students:
        sp = s.specialization or "Chưa chọn"
        spec_count[sp] = spec_count.get(sp, 0) + 1
    spec_labels = {
        "7480201_07": "Khoa học máy tính",
        "7480201_06": "Mạng máy tính",
        "7480201_05": "Công nghệ phần mềm",
        "7480201_09": "Hệ thống thông tin",
        "7480201_04": "Tin học kinh tế",
        "7480201_08": "CNTT Địa học",
    }
    for code, cnt in sorted(spec_count.items(), key=lambda x: -x[1]):
        lines.append(f"  {spec_labels.get(code, code)}: {cnt} SV")

    # GPA + completion thống kê (mẫu nhỏ để tránh tốn)
    gpa_vals: list[float] = []
    for s in students[:60]:
        try:
            snap = build_progress_snapshot(db, s.id)
            g4 = snap.get("avg_score4")
            if g4 is not None:
                gpa_vals.append(float(g4))
        except Exception:
            pass
    if gpa_vals:
        lines.append("")
        lines.append(f"=== CHẤT LƯỢNG (mẫu {len(gpa_vals)} SV) ===")
        lines.append(f"GPA trung bình hệ 4: {sum(gpa_vals)/len(gpa_vals):.2f}")
        low_gpa = sum(1 for g in gpa_vals if g < 2.0)
        hi_gpa = sum(1 for g in gpa_vals if g >= 3.2)
        lines.append(f"SV GPA < 2.0 (nguy cơ): {low_gpa}")
        lines.append(f"SV GPA ≥ 3.2 (giỏi/xuất sắc): {hi_gpa}")

    # Cố vấn chưa có SV
    advisors = db.query(models.User).filter(models.User.role == "advisor").all()
    adv_no_sv = []
    for a in advisors:
        cnt = db.query(_sqlfunc.count(models.AdvisorAssignment.id)).filter(
            models.AdvisorAssignment.advisor_id == a.id
        ).scalar() or 0
        if cnt == 0:
            adv_no_sv.append(a.teacher_code or a.username)
    if adv_no_sv:
        lines.append("")
        lines.append(f"=== CỐ VẤN CHƯA CÓ SV ({len(adv_no_sv)}) ===")
        lines.append("  " + ", ".join(adv_no_sv[:10]))

    lines.append("")
    lines.append("=== VAI TRÒ CỦA BẠN KHI TƯ VẤN ===")
    lines.append("Bạn đang hỗ trợ quản trị viên EduGuide. Trả lời phải:")
    lines.append("- Dựa trên số liệu tổng hợp bên trên, KHÔNG bịa số")
    lines.append("- Gợi ý hành động quản trị (VD: phân công SV cho GV X, cảnh báo cohort Y)")
    lines.append("- Trả lời tiếng Việt, có cấu trúc (bullet), súc tích")
    return "\n".join(lines)


def _role_fallback_answer(role: str, message: str, ctx: str) -> str:
    """Khi LLM không khả dụng: trích xuất section liên quan từ context block.

    Không thông minh như LLM, nhưng vẫn trả về dữ liệu thật dựa trên từ khoá trong câu hỏi.
    """
    m = (message or "").lower()
    # Split context into sections by "=== ... ==="
    import re as _re
    sections: list[tuple[str, str]] = []
    cur_title = "Tổng quan"
    cur_body: list[str] = []
    for line in ctx.splitlines():
        mt = _re.match(r'^===\s+(.+?)\s+===\s*$', line)
        if mt:
            if cur_body:
                sections.append((cur_title, "\n".join(cur_body).strip()))
            cur_title = mt.group(1)
            cur_body = []
        else:
            cur_body.append(line)
    if cur_body:
        sections.append((cur_title, "\n".join(cur_body).strip()))

    # Keywords to section-title matching
    rules = [
        (["nguy cơ", "khó khăn", "risk", "yếu", "GPA thấp"], ["SV NGUY CƠ CAO", "NHÓM SINH VIÊN"]),
        (["cần chú ý", "cảnh báo", "attention"], ["SV CẦN CHÚ Ý", "NHÓM SINH VIÊN"]),
        (["tóm tắt", "tổng quan", "summary", "tình hình"], ["NHÓM SINH VIÊN", "TỔNG QUAN"]),
        (["cohort", "khóa", "k22", "k21", "k20"], ["PHÂN BỐ KHÓA"]),
        (["chuyên ngành", "ngành"], ["PHÂN BỐ CHUYÊN NGÀNH"]),
        (["gpa", "điểm"], ["CHẤT LƯỢNG", "NHÓM SINH VIÊN"]),
        (["cố vấn", "gv", "chưa có sv"], ["CỐ VẤN CHƯA CÓ SV"]),
        (["ghi chú", "note"], ["GHI CHÚ"]),
    ]
    matched_sections: list[tuple[str, str]] = []
    for kw_list, title_hints in rules:
        if any(kw in m for kw in kw_list):
            for sec_title, sec_body in sections:
                for hint in title_hints:
                    if hint in sec_title.upper() and (sec_title, sec_body) not in matched_sections:
                        matched_sections.append((sec_title, sec_body))
                        break

    if not matched_sections:
        # Fallback: show the most data-rich sections
        keep = ["NHÓM SINH VIÊN", "TỔNG QUAN", "PHÂN BỐ KHÓA", "PHÂN BỐ CHUYÊN NGÀNH"]
        for sec_title, sec_body in sections:
            if any(k in sec_title.upper() for k in keep):
                matched_sections.append((sec_title, sec_body))

    parts = ["**Dữ liệu hiện tại** (AI LLM tạm không khả dụng, trả về số liệu thô):\n"]
    for sec_title, sec_body in matched_sections[:3]:
        parts.append(f"**{sec_title}**")
        parts.append(sec_body[:800])
        parts.append("")
    if role == "advisor":
        parts.append("_Gợi ý: mở tab Sinh viên để xem chi tiết và tư vấn._")
    elif role == "admin":
        parts.append("_Gợi ý: xem Dashboard để có biểu đồ chi tiết._")
    return "\n".join(parts).strip()


# ── Fallback: rule-based local router (dùng khi không có API key) ─────────────

def _career_from_progress(progress: dict) -> tuple[str, float, list[str]]:
    avg10 = progress.get("avg_score10") or 0
    if avg10 >= 8.0:
        return "Dữ liệu / AI", 0.82, ["Điểm trung bình cao", "Có thể theo các môn khó hơn về AI/Data"]
    if avg10 >= 7.0:
        return "Phát triển phần mềm", 0.74, ["Nền tảng ổn định", "Phù hợp lộ trình phát triển hệ thống"]
    return "Hỗ trợ hệ thống / QA", 0.61, ["Nên ưu tiên môn nền tảng", "Cần cải thiện điểm các môn cốt lõi"]


def _no_data_reply(intent: str) -> ChatIntentResult:
    return ChatIntentResult(
        intent=intent,
        answer="Chưa có dữ liệu điểm. Hãy upload bảng điểm để tôi hỗ trợ bạn.",
        suggestions=[],
    )


_COURSE_KB: dict[str, str] = {
    "xử lý ngôn ngữ tự nhiên": (
        "Xử lý ngôn ngữ tự nhiên (NLP) nghiên cứu cách máy tính hiểu và sinh ngôn ngữ của con người. "
        "Nội dung gồm: tiền xử lý văn bản (tokenization, stemming), phân tích cú pháp, phân loại văn bản, "
        "nhận dạng thực thể (NER), dịch máy, chatbot, và các mô hình ngôn ngữ lớn (BERT, GPT). "
        "Kỹ năng đạt được: lập trình Python với NLTK/spaCy/Hugging Face, xây dựng ứng dụng NLP thực tế."
    ),
    "trí tuệ nhân tạo": (
        "Trí tuệ nhân tạo (AI) trang bị nền tảng lý thuyết và kỹ thuật xây dựng hệ thống thông minh. "
        "Nội dung gồm: tìm kiếm (BFS/DFS/A*), logic mệnh đề, học máy cơ bản, mạng nơ-ron, "
        "hệ chuyên gia, xử lý không chắc chắn (Bayes). "
        "Kỹ năng: giải quyết bài toán AI kinh điển, lập trình Python cho AI."
    ),
    "học máy": (
        "Học máy (Machine Learning) dạy máy tính tự học từ dữ liệu mà không lập trình tường minh. "
        "Nội dung: hồi quy tuyến tính/logistic, cây quyết định, SVM, k-NN, k-Means, "
        "đánh giá mô hình (cross-validation, ROC), ensemble (Random Forest, XGBoost). "
        "Kỹ năng: Python với scikit-learn, pandas, phân tích và xử lý dữ liệu thực tế."
    ),
    "học sâu": (
        "Học sâu (Deep Learning) tập trung mạng nơ-ron nhiều lớp. "
        "Nội dung: perceptron, backpropagation, CNN (phân loại ảnh), RNN/LSTM (chuỗi thời gian), "
        "Transformer, GAN, transfer learning. "
        "Kỹ năng: TensorFlow/PyTorch, huấn luyện và tối ưu mô hình deep learning."
    ),
    "khai phá dữ liệu": (
        "Khai phá dữ liệu (Data Mining) tìm kiếm tri thức ẩn trong tập dữ liệu lớn. "
        "Nội dung: luật kết hợp (Apriori), phân cụm, phân lớp, phát hiện ngoại lệ, "
        "quy trình KDD/CRISP-DM. "
        "Kỹ năng: phân tích dữ liệu với Python/R, trực quan hóa kết quả."
    ),
    "lập trình web": (
        "Lập trình Web trang bị kỹ năng xây dựng ứng dụng web đầy đủ. "
        "Nội dung: HTML/CSS/JavaScript (frontend), framework backend (Node.js, Django, Laravel), "
        "REST API, cơ sở dữ liệu web, xác thực người dùng, triển khai ứng dụng. "
        "Kỹ năng: xây dựng website hoàn chỉnh, làm việc với API."
    ),
    "cơ sở dữ liệu": (
        "Cơ sở dữ liệu (Database) dạy thiết kế và quản lý hệ thống lưu trữ dữ liệu. "
        "Nội dung: mô hình quan hệ, SQL (SELECT/JOIN/GROUP BY/subquery), thiết kế ERD, "
        "chuẩn hóa (1NF-3NF), transaction, index, stored procedure. "
        "Kỹ năng: thiết kế CSDL chuẩn, viết truy vấn SQL phức tạp với MySQL/PostgreSQL."
    ),
    "mạng máy tính": (
        "Mạng máy tính nghiên cứu nguyên lý truyền thông và kết nối các thiết bị. "
        "Nội dung: mô hình OSI/TCP-IP, giao thức HTTP/FTP/DNS/DHCP, địa chỉ IP/subnet, "
        "routing, switching, bảo mật mạng cơ bản, socket programming. "
        "Kỹ năng: cấu hình mạng, lập trình socket, phân tích gói tin với Wireshark."
    ),
    "hệ điều hành": (
        "Hệ điều hành (Operating System) nghiên cứu cơ chế quản lý tài nguyên máy tính. "
        "Nội dung: quản lý tiến trình (scheduling, deadlock), quản lý bộ nhớ (paging, virtual memory), "
        "hệ thống file, I/O, đồng bộ hóa (mutex, semaphore). "
        "Kỹ năng: lập trình hệ thống C/C++, hiểu Linux internals."
    ),
    "cấu trúc dữ liệu": (
        "Cấu trúc dữ liệu và Giải thuật là nền tảng lập trình hiệu quả. "
        "Nội dung: mảng, danh sách liên kết, stack, queue, cây (BST, AVL, heap), "
        "đồ thị (BFS/DFS/Dijkstra/MST), sắp xếp, tìm kiếm, độ phức tạp O(n). "
        "Kỹ năng: phân tích và chọn cấu trúc dữ liệu phù hợp, giải bài toán thuật toán."
    ),
    "công nghệ phần mềm": (
        "Công nghệ phần mềm (Software Engineering) dạy quy trình phát triển phần mềm chuyên nghiệp. "
        "Nội dung: vòng đời phần mềm (SDLC), mô hình Agile/Scrum, phân tích yêu cầu, "
        "thiết kế UML, kiểm thử phần mềm, quản lý dự án, Git. "
        "Kỹ năng: làm việc nhóm, quản lý dự án, viết tài liệu kỹ thuật."
    ),
    "an toàn thông tin": (
        "An toàn thông tin (Information Security) trang bị kiến thức bảo vệ hệ thống số. "
        "Nội dung: mã hóa (symmetric/asymmetric/hash), xác thực, PKI, các loại tấn công "
        "(SQL injection, XSS, MITM), pentest cơ bản, bảo mật ứng dụng web. "
        "Kỹ năng: phân tích lỗ hổng, áp dụng các cơ chế bảo mật trong lập trình."
    ),
    "kiến trúc máy tính": (
        "Kiến trúc máy tính nghiên cứu tổ chức và hoạt động bên trong máy tính. "
        "Nội dung: hệ nhị phân/hexa, cổng logic, ALU, thanh ghi, bộ nhớ, "
        "pipeline, cache, kiến trúc Von Neumann, hợp ngữ (Assembly). "
        "Kỹ năng: hiểu cách CPU hoạt động, lập trình assembly cơ bản."
    ),
    "lập trình hướng đối tượng": (
        "Lập trình hướng đối tượng (OOP) là mô hình lập trình trung tâm trong phát triển phần mềm. "
        "Nội dung: class/object, encapsulation, inheritance, polymorphism, abstraction, "
        "design patterns (Singleton, Factory, Observer), UML class diagram. "
        "Kỹ năng: thiết kế hệ thống hướng đối tượng với Java/C++/Python."
    ),
    "giải tích": (
        "Giải tích (Calculus) là nền tảng toán học cho AI/Data Science. "
        "Nội dung: giới hạn, đạo hàm, tích phân, chuỗi số, hàm nhiều biến, "
        "gradient (dùng trong backpropagation ML). "
        "Kỹ năng: tư duy toán học, áp dụng trong tối ưu hóa và học máy."
    ),
    "đại số tuyến tính": (
        "Đại số tuyến tính là công cụ toán học cốt lõi cho AI và đồ họa máy tính. "
        "Nội dung: vector, ma trận, phép nhân ma trận, định thức, nghịch đảo, "
        "trị riêng/vector riêng, phân tích SVD/PCA. "
        "Ứng dụng: xử lý ảnh, compression, thuật toán ML (Linear Regression, PCA)."
    ),
    "xác suất thống kê": (
        "Xác suất và Thống kê cung cấp công cụ phân tích dữ liệu và xây dựng mô hình. "
        "Nội dung: xác suất, biến ngẫu nhiên, phân phối (normal, binomial), "
        "kiểm định giả thuyết, hồi quy, ước lượng. "
        "Ứng dụng: đánh giá mô hình ML, phân tích A/B testing, data science."
    ),
    "đồ họa máy tính": (
        "Đồ họa máy tính nghiên cứu kỹ thuật tạo và xử lý hình ảnh số. "
        "Nội dung: hệ tọa độ 2D/3D, biến đổi affine, rasterization, shading, "
        "OpenGL/WebGL, đồ họa vector, xử lý ảnh cơ bản. "
        "Kỹ năng: lập trình đồ họa, xây dựng ứng dụng render 2D/3D."
    ),
    "xử lý ảnh": (
        "Xử lý ảnh số (Image Processing/Computer Vision) dạy phân tích và hiểu nội dung ảnh. "
        "Nội dung: biểu diễn ảnh số, lọc ảnh, phát hiện cạnh, phân đoạn, "
        "nhận dạng đối tượng, CNN trong Computer Vision, OpenCV. "
        "Kỹ năng: xây dựng ứng dụng nhận dạng ảnh, phát hiện khuôn mặt."
    ),
    "lập trình": (
        "Môn lập trình cơ sở trang bị tư duy giải quyết vấn đề bằng lập trình máy tính. "
        "Nội dung: biến, kiểu dữ liệu, cấu trúc điều kiện/vòng lặp, hàm, mảng, "
        "con trỏ (C), nhập/xuất file. "
        "Kỹ năng: viết chương trình C/Python giải quyết bài toán cơ bản."
    ),
    "phân tích thiết kế hệ thống": (
        "Phân tích và Thiết kế Hệ thống dạy quy trình xây dựng hệ thống thông tin. "
        "Nội dung: phân tích yêu cầu, DFD, ERD, thiết kế hệ thống hướng đối tượng, "
        "UML (use case, sequence, activity diagram), prototype. "
        "Kỹ năng: làm tài liệu phân tích, thiết kế hệ thống phần mềm hoàn chỉnh."
    ),
}


def _norm_vn(t: str) -> str:
    """Normalize Vietnamese text — lowercase, strip diacritics, đ → d. Dùng cho fuzzy match."""
    import unicodedata as _ud
    t = (t or "").replace("đ", "d").replace("Đ", "d")
    return "".join(c for c in _ud.normalize("NFKD", t.lower()) if not _ud.combining(c))


def _resolve_course_from_message(
    message: str, db: Session, memory=None
) -> "models.Course | None":
    """Extract course từ message: ưu tiên course_code (7XXXXXX), fallback fuzzy name match.

    Args:
        message: tin nhắn user.
        db: session DB.
        memory: list ChatMessage gần nhất để lookup nếu user dùng đại từ ('môn đó', 'nó').

    Returns Course object hoặc None.
    """
    import re
    # 1. Course code regex (7 chữ số bắt đầu bằng 7)
    code_match = re.search(r"\b(7\d{6})\b", message or "")
    if code_match:
        c = db.query(models.Course).filter(
            models.Course.course_code == code_match.group(1)
        ).first()
        if c:
            return c

    # 2. Lookup memory cho course code (cho trường hợp user dùng "nó", "môn đó")
    if memory:
        for mem in reversed(memory[-6:]):
            try:
                m = re.search(r"\b(7\d{6})\b", mem.message or "")
            except Exception:
                continue
            if m:
                c = db.query(models.Course).filter(
                    models.Course.course_code == m.group(1)
                ).first()
                if c:
                    return c

    # 3. Fuzzy match course name (≥2 từ khớp, từ ≥3 chars để tránh stopwords)
    msg_norm = _norm_vn(message)
    if not msg_norm or len(msg_norm) < 4:
        return None
    best_course = None
    best_score = 0
    courses = db.query(models.Course).all()
    for c in courses:
        name_norm = _norm_vn(c.course_name or "")
        if not name_norm:
            continue
        words = [w for w in name_norm.split() if len(w) >= 3]
        if not words:
            continue
        score = sum(1 for w in words if w in msg_norm)
        if score > best_score:
            best_score = score
            best_course = c
    # Threshold: ≥2 từ khớp để tránh false positive ("toán" match cả "toán rời rạc" và "toán cao cấp")
    return best_course if best_score >= 2 else None


def _build_course_context(course, db: Session) -> str:
    """Build RAG context từ DB cho 1 môn — description + skills + tiên quyết."""
    parts = [
        f"Mã môn: {course.course_code}",
        f"Tên môn: {course.course_name}",
        f"Số tín chỉ: {course.credits or '?'} TC",
    ]
    if course.typical_semester:
        parts.append(f"Học kỳ điển hình: HK{course.typical_semester}")
    if course.required_specialization:
        parts.append(f"Chuyên ngành yêu cầu: {course.required_specialization}")
    if (course.description or "").strip():
        parts.append(f"\nMô tả chính thức từ CTĐT:\n{course.description.strip()}")

    # Skills join
    try:
        rows = (
            db.query(models.CourseSkill, models.Skill)
            .join(models.Skill, models.CourseSkill.skill_code == models.Skill.code)
            .filter(models.CourseSkill.course_code == course.course_code)
            .order_by(models.CourseSkill.weight.desc())
            .all()
        )
        if rows:
            skill_lines = []
            for cs, s in rows:
                w = float(cs.weight or 1.0)
                marker = "⭐" if w >= 0.8 else " •"
                skill_lines.append(f"{marker} {s.name} ({s.category})")
            parts.append("\nKỹ năng môn dạy (theo CTĐT):\n" + "\n".join(skill_lines))
    except Exception:
        pass

    return "\n".join(parts)


def _course_info_fallback(message: str) -> str:
    """Tra cứu thông tin môn học từ knowledge base nội bộ khi không có API.

    Chỉ dùng khi DB không có course (resolve fail) VÀ LLM không khả dụng.
    """
    msg_norm = _norm_vn(message)
    best_key = None
    best_score = 0
    for key in _COURSE_KB:
        key_norm = _norm_vn(key)
        words = key_norm.split()
        score = sum(1 for w in words if w in msg_norm)
        if score > best_score:
            best_score = score
            best_key = key

    if best_key and best_score >= 1:
        return _COURSE_KB[best_key]

    return (
        "Tôi chưa có thông tin chi tiết về môn học này trong cơ sở dữ liệu. "
        "Bạn có thể hỏi cụ thể hơn tên môn học (hoặc mã môn dạng 70xxxxx), "
        "hoặc hỏi về các môn phổ biến như: Trí tuệ nhân tạo, Học máy, Cơ sở dữ liệu, "
        "Mạng máy tính, Hệ điều hành, Cấu trúc dữ liệu, Công nghệ phần mềm."
    )


def _local_router(intent: str, db: Session, user_id: int, limit: int, message: str = "") -> ChatIntentResult:

    if intent == "graduation":
        p = build_progress_snapshot(db, user_id)
        if p["earned_credits"] == 0:
            return _no_data_reply(intent)
        earned = p["earned_credits"]
        threshold = _get_graduation_threshold(db)
        short = threshold - earned
        if p["graduation_ready"]:
            answer = f"Bạn đã đạt {earned} TC — đủ điều kiện tốt nghiệp ({threshold} TC yêu cầu). "
            if not p["thesis_done"]:
                answer += "Hãy hoàn thành Đồ án tốt nghiệp để chính thức ra trường!"
        else:
            answer = (
                f"Bạn hiện có {earned}/{threshold} TC. "
                f"Cần thêm {short:.0f} TC nữa để đủ điều kiện tốt nghiệp."
            )
            if p["thesis_eligible"]:
                answer += " Bạn đã đủ điều kiện làm Đồ án tốt nghiệp."
            elif p["internship_eligible"]:
                answer += " Bạn đủ điều kiện thực tập — hoàn thành thực tập rồi làm Đồ án."
            else:
                answer += " Cần hoàn thành thêm các môn học trước khi đủ điều kiện thực tập."
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "internship":
        p = build_progress_snapshot(db, user_id)
        if p["earned_credits"] == 0:
            return _no_data_reply(intent)
        if p["internship_done"]:
            answer = "Bạn đã hoàn thành thực tập tốt nghiệp."
            if p["thesis_eligible"]:
                answer += " Bạn đủ điều kiện làm Đồ án tốt nghiệp."
        elif p["internship_eligible"]:
            answer = (
                "Bạn đã đủ điều kiện học thực tập doanh nghiệp. "
                "Các môn bắt buộc đã hoàn thành, chỉ còn thực tập và Đồ án."
            )
        else:
            earned = p["earned_credits"]
            total = p["total_credits"]
            answer = (
                f"Chưa đủ điều kiện thực tập. Bạn cần hoàn thành gần hết các môn bắt buộc "
                f"(hiện tại {earned:.0f}/{total:.0f} TC, còn lại nhiều hơn 6 TC ngoài thực tập/đồ án)."
            )
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "thesis":
        p = build_progress_snapshot(db, user_id)
        if p["earned_credits"] == 0:
            return _no_data_reply(intent)
        if p["thesis_done"]:
            answer = "Bạn đã hoàn thành Đồ án tốt nghiệp."
        elif p["thesis_eligible"]:
            answer = (
                "Bạn đã đủ điều kiện làm Đồ án tốt nghiệp. "
                "Thực tập đã hoàn thành — hãy liên hệ giảng viên để bắt đầu."
            )
        elif p["internship_done"]:
            answer = "Thực tập đã xong nhưng điều kiện Đồ án chưa đủ. Kiểm tra lại các môn bắt buộc."
        else:
            answer = "Bạn cần hoàn thành thực tập doanh nghiệp trước khi làm Đồ án tốt nghiệp."
            if p["internship_eligible"]:
                answer = "Bạn đủ điều kiện thực tập — hãy đăng ký thực tập trước, rồi mới đến Đồ án."
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "prereq":
        p = build_progress_snapshot(db, user_id)
        issues = p.get("prereq_issues", [])
        if not issues:
            answer = "Không có môn nào bị thiếu điều kiện tiên quyết trong chương trình của bạn."
        else:
            lines = []
            for issue in issues[:5]:
                missing = ", ".join(issue["missing_prereq_codes"])
                lines.append(f"• {issue['course_name']} ({issue['course_code']}): cần hoàn thành {missing} trước")
            answer = "Các môn bạn chưa đủ điều kiện tiên quyết:\n" + "\n".join(lines)
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent in {"recommend", "explain", "general"}:
        rec = build_recommendations(db, user_id, limit=max(1, min(limit, 5)))
        items = rec.get("recommendations", [])
        if not items:
            if rec.get("thesis_eligible"):
                return ChatIntentResult(
                    intent=intent,
                    answer="Bạn đã hoàn thành tất cả môn cần thiết và đủ điều kiện làm Đồ án tốt nghiệp!",
                    suggestions=[],
                )
            if rec.get("graduation_ready"):
                return ChatIntentResult(
                    intent=intent,
                    answer="Bạn đã đủ tín chỉ tốt nghiệp. Chúc mừng!",
                    suggestions=[],
                )
            return ChatIntentResult(
                intent=intent,
                answer="Chưa có dữ liệu để gợi ý. Hãy upload bảng điểm trước nhé.",
                suggestions=[],
            )
        lines = []
        for i, x in enumerate(items):
            tag = f"[{x['category'].upper()}]" if x["category"] != "required" else ""
            lines.append(f"{i+1}. {tag} {x['course_name']} ({x['course_code']}) — {x['credits']} TC")
        answer = "Gợi ý môn học tiếp theo:\n" + "\n".join(lines)
        if intent == "explain" and items:
            answer += "\n\nLý do ưu tiên môn đầu: " + "; ".join(items[0].get("reasons", [])[:2])
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[x["course_code"] for x in items])

    if intent == "progress":
        p = build_progress_snapshot(db, user_id)
        if p["earned_credits"] == 0 and p["completed_courses"] == 0:
            return _no_data_reply(intent)
        earned = p["earned_credits"]
        total = p["total_credits"]
        pct = p["completion_percent"]
        answer = (
            f"Tiến độ: {pct}% ({earned}/{total} TC). "
            f"Đã hoàn thành {p['completed_courses']} môn, còn {p['remaining_courses']} môn."
        )
        grad_threshold = _get_graduation_threshold(db)
        if p["graduation_ready"]:
            answer += f" Đủ điều kiện tốt nghiệp ({grad_threshold:.0f} TC)."
        else:
            answer += f" Cần thêm {grad_threshold - earned:.0f} TC để đủ điều kiện tốt nghiệp."
        if p["thesis_eligible"]:
            answer += " Đủ điều kiện làm Đồ án tốt nghiệp."
        elif p["internship_eligible"]:
            answer += " Đủ điều kiện thực tập doanh nghiệp."
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "career":
        p = build_progress_snapshot(db, user_id)
        avg10 = p.get("avg_score10") or 0
        # Deprecated 2026-05-05: user.career_goal dropped
        current = "Chưa chọn"

        auto_career, conf, reasons = _career_from_progress(p)
        answer = (
            f"Định hướng hiện tại của bạn: **{current}**.\n"
            f"Dựa trên GPA {avg10:.1f}/10, hệ thống gợi ý hướng **{auto_career}** "
            f"(phù hợp {round(conf*100,1)}%) — lý do: {'; '.join(reasons)}.\n\n"
            "Các hướng bạn có thể tham khảo:\n"
            "• **Lập trình Web**: thị trường rộng, cần môn Lập trình web, CSDL, Mạng.\n"
            "• **AI / Dữ liệu**: cần GPA ≥7.5, giỏi toán, môn Trí tuệ nhân tạo, Học máy.\n"
            "• **An toàn mạng**: cần môn An toàn thông tin, Mạng máy tính, Hệ điều hành.\n"
            "Hỏi tôi 'Nếu tôi theo hướng X thì sao?' để được tư vấn cụ thể hơn."
        )
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "course_info":
        return ChatIntentResult(
            intent=intent,
            answer=_course_info_fallback(message),
            suggestions=[],
        )

    if intent == "greeting":
        return ChatIntentResult(
            intent=intent,
            answer="Xin chào! Tôi là trợ lý AI học tập. Tôi có thể giúp bạn gợi ý môn học, xem tiến độ, tư vấn lộ trình hay giải thích nội dung môn học. Bạn cần hỗ trợ gì?",
            suggestions=[],
        )

    return ChatIntentResult(
        intent="general",
        answer=(
            "Bạn có thể hỏi tôi:\n"
            "• 'Tôi nên học môn gì?' — gợi ý môn học\n"
            "• 'Tiến độ của tôi?' — xem % hoàn thành và tín chỉ\n"
            "• 'Tôi đủ điều kiện tốt nghiệp chưa?' — kiểm tra điều kiện ra trường\n"
            "• 'Tôi đủ điều kiện thực tập chưa?' — điều kiện thực tập doanh nghiệp\n"
            "• 'Tôi đủ điều kiện làm đồ án chưa?' — điều kiện đồ án tốt nghiệp\n"
            "• 'Tôi hợp định hướng nào?' — tư vấn nghề nghiệp"
        ),
        suggestions=[],
    )


# ── Memory helpers ────────────────────────────────────────────────────────────

def _recent_memory(db: Session, user_id: int, limit: int = 20, thread_id: str | None = None) -> list[models.ChatMessage]:
    """
    Smart memory: keep first 4 messages (topic anchors) + most recent messages.
    If thread_id is provided, only fetch messages from that thread.
    """
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.user_id == user_id)
        if thread_id:
            q = q.filter(models.ChatMessage.thread_id == thread_id)
        all_rows = q.order_by(models.ChatMessage.created_at.asc()).all()
        if len(all_rows) <= limit:
            return all_rows
        anchors = all_rows[:4]
        recent = all_rows[-(limit - 4):]
        seen = {m.id for m in anchors}
        combined = anchors + [m for m in recent if m.id not in seen]
        return combined
    except SQLAlchemyError:
        db.rollback()
        return []


def _save_memory(db: Session, user_id: int, role: str, message: str, intent: str | None = None, thread_id: str | None = None) -> None:
    try:
        db.add(models.ChatMessage(user_id=user_id, role=role, message=message, intent=intent, thread_id=thread_id))
        # Keep thread's updated_at current so the list stays sorted by activity
        if thread_id:
            from datetime import datetime, timezone
            thread = db.query(models.ChatThread).filter(
                models.ChatThread.id == thread_id,
                models.ChatThread.user_id == user_id,
            ).first()
            if thread:
                thread.updated_at = datetime.now(timezone.utc)
        db.commit()
    except SQLAlchemyError:
        db.rollback()


# ── Main chat entry point ─────────────────────────────────────────────────────

def chat_reply(
    message: str,
    db: Session,
    user_id: int,
    limit: int = 5,
    prefer_llm: bool = True,
    thread_id: str | None = None,
) -> ChatIntentResult:
    message = (message or "").strip()
    if not message:
        return ChatIntentResult(intent="general", answer="Bạn hãy nhập nội dung câu hỏi.", suggestions=[])

    memory = _recent_memory(db, user_id, limit=20, thread_id=thread_id)
    intent = detect_intent_rule(message)

    # Route by user role: advisor/admin get their own context + system prompt,
    # student keeps the original flow (with full grade/recommendation context).
    _user_obj = db.query(models.User).filter(models.User.id == user_id).first()
    _role = (_user_obj.role if _user_obj else "student") or "student"

    if _role in ("advisor", "admin"):
        ctx = _build_advisor_context_prompt(db, user_id) if _role == "advisor" else _build_admin_context_prompt(db)
        history_msgs: list[dict] = []
        for m in memory[-10:]:
            if m.role in ("user", "assistant"):
                history_msgs.append({"role": m.role, "content": m.message})
        role_label = "cố vấn học tập" if _role == "advisor" else "quản trị viên hệ thống"
        system_prompt = (
            f"Bạn là trợ lý AI cho {role_label} của hệ thống EduGuide (gợi ý môn học ngành CNTT).\n"
            f"Dưới đây là dữ liệu thật lấy từ DB — hãy dựa vào đó để trả lời, KHÔNG bịa số liệu.\n"
            "Nếu người dùng hỏi điều không có trong dữ liệu, nói rõ 'chưa có thông tin đó'.\n"
            "Ngôn ngữ: tiếng Việt, súc tích, có cấu trúc khi cần.\n\n"
            f"{ctx}"
        )
        llm_messages = [{"role": "system", "content": system_prompt}] + history_msgs + [
            {"role": "user", "content": message}
        ]
        answer: str | None = None
        try:
            answer = (
                _gemini_chat(llm_messages, temperature=0.3, max_tokens=500)
                or _groq_chat(llm_messages, temperature=0.3, max_tokens=500)
                or _claude_chat_with_history(llm_messages)
            )
        except Exception:
            answer = None
        if not answer:
            # Rule-based fallback: extract useful summary from context block
            answer = _role_fallback_answer(_role, message, ctx)
        _save_memory(db, user_id, "user", message, intent=f"{_role}_chat", thread_id=thread_id)
        _save_memory(db, user_id, "assistant", answer, intent=f"{_role}_chat", thread_id=thread_id)
        return ChatIntentResult(intent=f"{_role}_chat", answer=answer, suggestions=[])

    # Build student context and suggestion list
    try:
        student_ctx, suggestion_codes = _build_student_context_prompt(db, user_id)
    except Exception:
        student_ctx = ""
        suggestion_codes = []

    final_answer: str | None = None

    # course_info — hỏi về nội dung môn học. RAG: lấy mô tả + skills từ DB rồi pass vào LLM.
    if intent == "course_info":
        # 1. Resolve course từ message (code regex / fuzzy name / memory lookup)
        course = None
        try:
            course = _resolve_course_from_message(message, db, memory)
        except Exception:
            pass

        # 2. Build context từ DB (mô tả + skills) nếu resolve được
        course_ctx = ""
        if course is not None:
            try:
                course_ctx = "\n\n=== DỮ LIỆU CHƯƠNG TRÌNH ĐÀO TẠO ===\n" + \
                    _build_course_context(course, db) + \
                    "\n=== HẾT DỮ LIỆU CTĐT ===\n"
            except Exception:
                course_ctx = ""

        # 3. LLM call với RAG context. Nếu có course_ctx → ưu tiên dữ liệu CTĐT.
        #    Nếu không → fallback dùng kiến thức tổng quát.
        sys_prompt = (
            "Bạn là trợ lý AI cho sinh viên ngành Công nghệ thông tin Việt Nam.\n"
            "Trả lời câu hỏi về môn học. Yêu cầu:\n"
            "- Nếu có DỮ LIỆU CTĐT bên dưới: ưu tiên dùng mô tả + kỹ năng từ đó (đây là "
            "nội dung chính thức của trường, đáng tin cậy hơn kiến thức tổng quát).\n"
            "- Nếu không có DỮ LIỆU CTĐT hoặc dữ liệu không khớp câu hỏi: dùng kiến thức "
            "chuyên môn về chương trình CNTT đại học Việt Nam.\n"
            "- Diễn giải ngắn gọn, dễ hiểu — KHÔNG copy nguyên văn mô tả.\n"
            "- Nếu user dùng đại từ ('nó', 'môn đó'), suy ra từ ngữ cảnh.\n"
            "- Trả lời tiếng Việt, tối đa 150 từ.\n"
            f"{course_ctx}"
        )
        ci_messages: list[dict] = [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": message},
        ]
        try:
            final_answer = (_gemini_chat(ci_messages, temperature=0.3, max_tokens=400)
                or _groq_chat(ci_messages, temperature=0.3, max_tokens=400)
                or _openai_chat(ci_messages, temperature=0.3, max_tokens=400)
                or _claude_chat_with_history(ci_messages))
        except Exception:
            pass

        # 4. Nếu LLM fail VÀ có course → fallback dùng raw description từ DB.
        if not final_answer and course and (course.description or "").strip():
            final_answer = (
                f"**{course.course_name}** ({course.course_code} · {course.credits or '?'} TC)\n\n"
                f"{course.description.strip()}\n\n"
                f"_(Mô tả từ CTĐT — AI tạm thời không khả dụng để diễn giải sâu hơn.)_"
            )

    # Greeting — xử lý riêng, không cần student context, không ép thành tư vấn
    if intent == "greeting" and not final_answer:
        user_obj = db.query(models.User).filter(models.User.id == user_id).first()
        name = (user_obj.full_name or "bạn").split()[0] if user_obj else "bạn"
        greeting_messages = [
            {"role": "system", "content": (
                "Bạn là trợ lý AI học tập thân thiện cho sinh viên ngành CNTT. "
                "Hãy chào hỏi tự nhiên, ấm áp bằng tiếng Việt. "
                "Giới thiệu ngắn bạn có thể giúp gì (tư vấn môn học, tiến độ, lộ trình, hỏi đáp về môn học). "
                "Tối đa 3 câu."
            )},
            {"role": "user", "content": message},
        ]
        try:
            final_answer = (_gemini_chat(greeting_messages, temperature=0.7, max_tokens=150)
                or _groq_chat(greeting_messages, temperature=0.7, max_tokens=150)
                or _openai_chat(greeting_messages, temperature=0.7, max_tokens=150)
                or _claude_chat_with_history(greeting_messages))
        except Exception:
            pass
        if not final_answer:
            final_answer = f"Xin chào {name}! Tôi là trợ lý AI học tập. Bạn có thể hỏi tôi về gợi ý môn học, tiến độ tốt nghiệp, hay nội dung bất kỳ môn nào trong chương trình."

    if prefer_llm and student_ctx and not final_answer:
        system_prompt = (
            "Bạn là trợ lý học tập AI cho sinh viên ngành Công nghệ thông tin tại Việt Nam.\n"
            "Bạn có thể trò chuyện tự nhiên VÀ tư vấn học tập.\n\n"
            "Quy tắc:\n"
            "1. Với câu hỏi về TIẾN ĐỘ, GPA, GỢI Ý MÔN, TỐT NGHIỆP, THỰC TẬP, ĐỒ ÁN: "
            "CHỈ dùng dữ liệu sinh viên bên dưới. KHÔNG tự tạo ra số liệu.\n"
            "2. Với câu hỏi về ĐỊNH HƯỚNG NGHỀ NGHIỆP (kể cả hướng khác với hướng hiện tại): "
            "dùng mục 'CÁC ĐỊNH HƯỚNG NGHỀ NGHIỆP' trong dữ liệu bên dưới để phân tích. "
            "So sánh điểm số, môn đã học và môn còn lại của sinh viên với yêu cầu của từng hướng. "
            "Nếu sinh viên hỏi 'nếu tôi theo hướng X thì sao', hãy tư vấn cụ thể dựa trên tình hình của họ.\n"
            "3. Với câu hỏi về NỘI DUNG MÔN HỌC: dùng kiến thức chuyên môn để giải thích.\n"
            "4. Với câu hỏi THÔNG THƯỜNG: trả lời tự nhiên, thân thiện.\n"
            "5. Trả lời bằng tiếng Việt, ngắn gọn (tối đa 150 từ).\n"
            "6. Không liệt kê toàn bộ danh sách môn trừ khi được yêu cầu rõ ràng.\n"
            "7. **Cá nhân hóa**: nếu có 'Hướng nghề chính', 'Quiz Holland', hoặc 'Kỹ năng SV quan tâm' "
            "trong dữ liệu — tham chiếu chúng khi tư vấn (vd: \"Vì em đã chọn Backend Dev và quan tâm Java, "
            "nên môn Lập trình .NET phù hợp...\").\n"
            "8. Khi gợi ý hành động, link đến trang cụ thể trong hệ thống nếu phù hợp: "
            "Lộ trình tích hợp (integrated-roadmap.html), Bảng điểm (grades.html), "
            "Mục tiêu nghề (career-goal.html), Trợ lý AI (ai-chat.html), Hỏi cố vấn (messaging.html).\n\n"
            f"{student_ctx}"
        )

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for mem in memory[-16:]:
            role = "assistant" if mem.role == "assistant" else "user"
            messages.append({"role": role, "content": mem.message})
        messages.append({"role": "user", "content": message})

        # Gemini → Groq → OpenAI → Claude
        final_answer = (_gemini_chat(messages, temperature=0.5, max_tokens=500)
            or _groq_chat(messages, temperature=0.5, max_tokens=500)
            or _openai_chat(messages, temperature=0.5, max_tokens=500)
            or _claude_chat_with_history(messages))

    # Fallback: rule-based local router
    if not final_answer:
        local = _local_router(intent, db, user_id, limit, message)
        final_answer = local.answer
        suggestion_codes = local.suggestions

    _save_memory(db, user_id, "user", message, intent=intent, thread_id=thread_id)
    _save_memory(db, user_id, "assistant", final_answer, intent=intent, thread_id=thread_id)

    return ChatIntentResult(intent=intent, answer=final_answer, suggestions=suggestion_codes)


def get_chat_history(db: Session, user_id: int, limit: int = 30, thread_id: str | None = None) -> list[models.ChatMessage]:
    try:
        q = db.query(models.ChatMessage).filter(models.ChatMessage.user_id == user_id)
        if thread_id:
            q = q.filter(models.ChatMessage.thread_id == thread_id)
        return q.order_by(models.ChatMessage.created_at.desc()).limit(max(1, min(limit, 200))).all()
    except SQLAlchemyError:
        db.rollback()
        return []
