"""Hybrid AI recommendation — rule-based filtering + LLM re-ranking & reasoning."""
from __future__ import annotations

import json
import os
import threading
from urllib import request as urllib_request

# Per-request timeout for each individual LLM call
_LLM_PER_CALL_TIMEOUT = 6   # seconds per provider
# Total budget across ALL providers — prevents 3×6 = 18s stall
_LLM_TOTAL_BUDGET = 8       # seconds max for entire LLM pipeline


def _groq_call(prompt: str, max_tokens: int = 1500) -> str | None:
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        return None
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": max_tokens,
    }
    req = urllib_request.Request(
        "https://api.groq.com/openai/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}", "User-Agent": "Mozilla/5.0 (compatible; AcademicAdvisor/1.0)"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=_LLM_PER_CALL_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def _llm_call(prompt: str, max_tokens: int = 1500) -> str | None:
    """Try Gemini → Groq → Claude with a hard total-budget timeout."""
    result: list[str | None] = [None]

    def _attempt():
        result[0] = (
            _gemini_chat(prompt, max_tokens)
            or _groq_call(prompt, max_tokens)
            or _claude_chat(prompt, max_tokens)
        )

    t = threading.Thread(target=_attempt, daemon=True)
    t.start()
    t.join(timeout=_LLM_TOTAL_BUDGET)
    return result[0]


def _gemini_chat(prompt: str, max_tokens: int = 1500) -> str | None:
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.2},
    }
    req = urllib_request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "python-requests/2.31.0"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=_LLM_PER_CALL_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except Exception:
        return None


def _claude_chat(prompt: str, max_tokens: int = 1500) -> str | None:
    # Đọc cả 2 tên env phổ biến: ANTHROPIC_API_KEY (chuẩn Anthropic SDK) +
    # CLAUDE_API_KEY (tên user thường đặt). Pick whichever is set.
    api_key = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    if not api_key:
        return None

    # Model: env CLAUDE_MODEL / ANTHROPIC_MODEL → fallback Haiku 4.5 (rẻ + nhanh)
    model = (os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL")
             or "claude-haiku-4-5-20251001").strip()
    payload = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib_request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "User-Agent": "python-requests/2.31.0",
        },
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=_LLM_PER_CALL_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["content"][0]["text"].strip()
    except Exception:
        return None


def _extract_json(raw: str) -> dict | list | None:
    try:
        start = raw.find("{") if "{" in raw else raw.find("[")
        if start == -1:
            return None
        end = raw.rfind("}") + 1 if "{" in raw else raw.rfind("]") + 1
        if end == 0:
            return None
        return json.loads(raw[start:end])
    except Exception:
        return None


def llm_rerank_courses(
    student_context: dict,
    candidates: list[dict],
    final_limit: int = 5,
) -> list[dict] | None:
    """
    AI re-ranking: given up to 15 rule-filtered candidates, LLM selects and ranks
    the best `final_limit` courses for this specific student, with personalised reasons.

    Returns a list of dicts: [{ course_code, reasons: [str, str] }, ...] ordered by AI priority,
    or None if LLM unavailable (caller falls back to rule-based order).
    """
    if not candidates:
        return None

    gpa4 = student_context.get("avg_score4")
    gpa10 = student_context.get("avg_score10")
    earned = student_context.get("earned_credits", 0)
    total = student_context.get("total_credits", 0)
    specialization = student_context.get("specialization") or "chưa chọn"
    career_goal = student_context.get("career_goal") or "chưa chọn"
    track = student_context.get("preferred_track") or "Tổng hợp"

    gpa_str = f"{gpa10:.1f}/10 ({gpa4:.2f}/4.0)" if gpa10 is not None and gpa4 is not None else "chưa có"

    _career_label = {
        "web": "Phát triển Web",
        "ai_data": "AI / Khoa học dữ liệu",
        "network_security": "Mạng & An ninh mạng",
        "general": "Tổng hợp",
    }

    _cand_lines = []
    for i, c in enumerate(candidates):
        pr = c.get("pass_rate")
        pa = c.get("prereq_avg_score")
        pass_str = f" | Tỷ lệ qua: {pr*100:.0f}%" if pr is not None else " | Tỷ lệ qua: chưa có"
        prereq_str = f" | TB tiên quyết: {pa:.1f}/10" if pa is not None else ""
        avail_str = " | ⚠ Không mở kỳ này" if not c.get("available_this_term", True) else ""
        _cand_lines.append(
            f'{i+1}. [{c["course_code"]}] {c["course_name"]} — {c["credits"]:.0f} TC'
            f' | Loại: {c["category"]}'
            f' | Điểm hệ thống: {c["recommendation_score"]:.0f}/100'
            f'{pass_str}{prereq_str}{avail_str}'
        )
    candidates_text = "\n".join(_cand_lines)

    gpa_trend_dir = student_context.get("gpa_trend_direction", "stable")
    _trend_label = {
        "improving": "đang tăng ↑",
        "declining": "đang giảm ↓",
        "stable": "ổn định →",
    }.get(gpa_trend_dir, "ổn định →")

    prompt = f"""Bạn là cố vấn học tập AI cho sinh viên ngành Công nghệ thông tin tại Việt Nam.

THÔNG TIN SINH VIÊN:
- GPA: {gpa_str} (xu hướng: {_trend_label})
- Tín chỉ tích lũy: {earned:.0f}/{total:.0f} TC
- Chuyên ngành: {specialization}
- Định hướng nghề nghiệp: {_career_label.get(career_goal, career_goal)}
- Hướng học tập phù hợp: {track}

HỆ THỐNG ĐÃ LỌC {len(candidates)} MÔN HỌC HỢP LỆ (đã thỏa điều kiện tiên quyết):
{candidates_text}

NHIỆM VỤ: Chọn và xếp hạng đúng {final_limit} môn phù hợp NHẤT cho sinh viên này ngay học kỳ tới.

Tiêu chí ưu tiên (theo thứ tự):
1. Môn bắt buộc hoặc điều kiện tốt nghiệp (thesis/internship) nếu đủ điều kiện
2. Phù hợp định hướng nghề nghiệp và hướng học tập
3. Phù hợp năng lực (GPA) và sở thích độ khó
4. Ưu tiên môn đang mở trong học kỳ hiện tại
5. Cân bằng tín chỉ (không quá nhiều môn nặng cùng lúc)

Trả về JSON hợp lệ, không markdown, không giải thích ngoài JSON:
{{
  "ranked": [
    {{"course_code": "MÃ_MÔN", "reasons": ["lý do ngắn 1 (≤20 từ)", "lý do ngắn 2 (≤20 từ)"]}},
    ...
  ]
}}"""

    raw = _llm_call(prompt, max_tokens=1500)
    if not raw:
        return None

    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed, dict) or "ranked" not in parsed:
        return None

    ranked = parsed["ranked"]
    if not isinstance(ranked, list):
        return None

    # Build lookup for fast access
    candidates_by_code = {c["course_code"]: c for c in candidates}
    result: list[dict] = []
    seen: set[str] = set()

    for item in ranked:
        code = item.get("course_code", "")
        if code in seen or code not in candidates_by_code:
            continue
        seen.add(code)
        entry = dict(candidates_by_code[code])  # copy
        reasons = item.get("reasons", [])
        if isinstance(reasons, list) and reasons:
            entry["reasons"] = [str(r) for r in reasons[:2]]
        entry["ai_ranked"] = True
        result.append(entry)
        if len(result) >= final_limit:
            break

    return result if result else None


def enrich_recommendation_reasons(
    student_context: dict,
    courses: list[dict],
) -> dict[str, list[str]]:
    """
    Fallback: enrich reasons for already-selected courses (used when re-ranking was skipped).
    Returns { course_code: [reason1, reason2] } or {} on failure.
    """
    if not courses:
        return {}

    gpa4 = student_context.get("avg_score4")
    earned = student_context.get("earned_credits", 0)
    total = student_context.get("total_credits", 0)
    specialization = student_context.get("specialization") or "chưa chọn"
    track = student_context.get("preferred_track") or "Tổng hợp"
    gpa_str = f"{gpa4:.2f}" if gpa4 is not None else "chưa có"

    courses_text = "\n".join(
        f'- {c["course_code"]}: {c["course_name"]} ({c["credits"]} TC, loại: {c["category"]})'
        for c in courses
    )

    prompt = f"""Bạn là cố vấn học tập AI cho sinh viên ngành CNTT Việt Nam.

Thông tin sinh viên: GPA {gpa_str}/4.0, tín chỉ {earned}/{total}, chuyên ngành {specialization}, hướng {track}.

Với mỗi môn dưới đây, viết đúng 2 câu giải thích ngắn (≤20 từ/câu) tại sao sinh viên NÀY nên học môn đó.
Đề cập cụ thể đến GPA, định hướng, tiến độ. Không dùng cụm chung chung.

Môn học:
{courses_text}

Trả về JSON, không markdown:
{{"COURSE_CODE": ["lý do 1", "lý do 2"], ...}}"""

    raw = _llm_call(prompt, max_tokens=1200)
    if not raw:
        return {}

    parsed = _extract_json(raw)
    return parsed if isinstance(parsed, dict) else {}


# ════════════════════════════════════════════════════════════════════════════
# Career Blueprint Generation — sinh "Bộ kỹ năng nghề" + tài liệu ngoài trường
# ════════════════════════════════════════════════════════════════════════════

# Budget cao hơn rerank vì prompt phức tạp + output JSON dài
_BLUEPRINT_TIMEOUT = 45  # seconds per provider (blueprint generation cần thời gian — output 4000 tokens)


def _llm_call_long(prompt: str, max_tokens: int = 4000) -> tuple[str | None, str | None]:
    """Try Gemini → Groq → Claude with longer budget for blueprint generation.
    Returns (raw_text, provider_used).

    On failure, prints the underlying error per provider so server logs reveal the
    actual cause (429 quota, network timeout, JSON shape mismatch, ...). Without this
    visibility, the endpoint silently returns 503 "AI không phản hồi".
    """
    api_key_gemini = os.getenv("GEMINI_API_KEY", "").strip()
    api_key_groq = os.getenv("GROQ_API_KEY", "").strip()
    api_key_claude = (os.getenv("ANTHROPIC_API_KEY") or os.getenv("CLAUDE_API_KEY") or "").strip()
    errors: list[str] = []  # collected for caller-side logging

    # Try sequentially with longer per-call timeout
    if api_key_gemini:
        result: list[str | None] = [None]
        err_box: list[str | None] = [None]
        def _try():
            try:
                model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key_gemini}"
                payload = {
                    "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                    "generationConfig": {"maxOutputTokens": max_tokens, "temperature": 0.3},
                }
                req = urllib_request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "User-Agent": "python-requests/2.31.0"},
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=_BLUEPRINT_TIMEOUT) as resp:
                    body = resp.read().decode("utf-8")
                data = json.loads(body)
                # Gemini có thể trả candidate rỗng nếu safety filter / quota → trả lỗi rõ
                cand = (data.get("candidates") or [{}])[0]
                if not cand.get("content"):
                    finish = cand.get("finishReason") or "no_content"
                    err_box[0] = f"gemini empty candidate (finish={finish})"
                    return
                result[0] = cand["content"]["parts"][0]["text"].strip()
            except Exception as e:
                err_box[0] = f"gemini {type(e).__name__}: {e}"
        t = threading.Thread(target=_try, daemon=True)
        t.start()
        t.join(timeout=_BLUEPRINT_TIMEOUT)
        if result[0]:
            return result[0], "gemini"
        if t.is_alive():
            errors.append(f"gemini timeout >{_BLUEPRINT_TIMEOUT}s")
        elif err_box[0]:
            errors.append(err_box[0])

    if api_key_groq:
        result = [None]
        err_box = [None]
        def _try_groq():
            try:
                model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "max_tokens": max_tokens,
                }
                req = urllib_request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key_groq}", "User-Agent": "python-requests/2.31.0"},
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=_BLUEPRINT_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                result[0] = data["choices"][0]["message"]["content"].strip()
            except Exception as e:
                err_box[0] = f"groq {type(e).__name__}: {e}"
        t = threading.Thread(target=_try_groq, daemon=True)
        t.start()
        t.join(timeout=_BLUEPRINT_TIMEOUT)
        if result[0]:
            return result[0], "groq"
        if t.is_alive():
            errors.append(f"groq timeout >{_BLUEPRINT_TIMEOUT}s")
        elif err_box[0]:
            errors.append(err_box[0])

    if api_key_claude:
        result = [None]
        err_box = [None]
        def _try_claude():
            try:
                payload = {
                    "model": (os.getenv("CLAUDE_MODEL") or os.getenv("ANTHROPIC_MODEL")
                              or "claude-haiku-4-5-20251001").strip(),
                    "max_tokens": max_tokens,
                    "messages": [{"role": "user", "content": prompt}],
                }
                req = urllib_request.Request(
                    "https://api.anthropic.com/v1/messages",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "x-api-key": api_key_claude,
                        "anthropic-version": "2023-06-01",
                        "User-Agent": "python-requests/2.31.0",
                    },
                    method="POST",
                )
                with urllib_request.urlopen(req, timeout=_BLUEPRINT_TIMEOUT) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                result[0] = data["content"][0]["text"].strip()
            except Exception as e:
                err_box[0] = f"claude {type(e).__name__}: {e}"
        t = threading.Thread(target=_try_claude, daemon=True)
        t.start()
        t.join(timeout=_BLUEPRINT_TIMEOUT)
        if result[0]:
            return result[0], "claude"
        if t.is_alive():
            errors.append(f"claude timeout >{_BLUEPRINT_TIMEOUT}s")
        elif err_box[0]:
            errors.append(err_box[0])

    # Tất cả providers fail — log để admin biết lý do, expose errors qua module-level
    # var để caller có thể inspect (vd seed script detect 429 → retry)
    if errors:
        print(f"[blueprint] all LLM providers failed: {' | '.join(errors)}", flush=True)
    else:
        print("[blueprint] no LLM API keys configured (set GEMINI_API_KEY or GROQ_API_KEY)", flush=True)
    # Expose last errors for callers (read-only, mutated trên mỗi call)
    global _last_llm_errors
    _last_llm_errors = errors
    return None, None


# Module-level var lưu errors của _llm_call_long gần nhất
# (cho phép caller như seed script inspect: "Gặp 429 không, có nên retry không?")
_last_llm_errors: list[str] = []


def get_last_llm_errors() -> list[str]:
    """Return errors string list từ lần gọi _llm_call_long gần nhất."""
    return list(_last_llm_errors)


def generate_career_detail(
    career_name: str,
    short_description: str,
) -> tuple[dict | None, str | None]:
    """Sinh chi tiết nghề (mô tả công việc, kỹ năng, tố chất, lương, cơ hội).

    Khác với generate_career_blueprint (sinh skill blueprint cụ thể). Function này
    dùng cho UI "Chi tiết nghề" trong picker — giúp SV quyết định trước khi chọn.

    Returns:
        ({overview, responsibilities[], required_hard_skills[], required_soft_skills[],
          personality_traits[], salary_vn{junior,mid,senior}, growth_paths[],
          is_suitable_for}, provider) hoặc (None, None) nếu LLM fail.
    """
    prompt = f"""Bạn là cố vấn nghề nghiệp CNTT cho sinh viên Việt Nam.

Nghề: **{career_name}** — {short_description}

Hãy trả về JSON HỢP LỆ giúp sinh viên hiểu rõ trước khi chọn nghề:
{{
  "overview": "2-3 câu mô tả tổng quan công việc thường ngày",
  "responsibilities": ["5-7 đầu việc cụ thể hàng ngày/hàng tuần"],
  "required_hard_skills": ["5-8 kỹ năng kỹ thuật bắt buộc, ngắn gọn"],
  "required_soft_skills": ["3-5 kỹ năng mềm cần thiết"],
  "personality_traits": ["3-5 tố chất/tính cách phù hợp với nghề"],
  "salary_vn": {{
    "junior": "X-Y triệu/tháng (0-2 năm KN)",
    "mid": "X-Y triệu/tháng (3-5 năm KN)",
    "senior": "X-Y triệu/tháng (5+ năm KN)"
  }},
  "growth_paths": ["3-5 cơ hội phát triển sự nghiệp"],
  "is_suitable_for": "1-2 câu mô tả sinh viên thế nào sẽ hợp với nghề này"
}}

YÊU CẦU:
- Mức lương theo thị trường VN 2025, ước lượng hợp lý.
- Văn phong tiếng Việt thân thiện, ngắn gọn, dễ hiểu cho sinh viên năm 2-3.
- Personality traits cụ thể (vd: "tỉ mỉ với chi tiết", "thích giải đố logic"), không generic.
- CHỈ trả JSON, KHÔNG markdown ```json, KHÔNG giải thích."""

    raw, provider = _llm_call_long(prompt, max_tokens=1800)
    if not raw:
        return None, None
    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed, dict):
        return None, None

    # Validate có ít nhất các field chính
    if not parsed.get("overview") or not isinstance(parsed.get("responsibilities"), list):
        return None, None
    return parsed, provider


def generate_career_blueprint(
    career_name: str,
    career_description: str,
    school_courses: list[dict],
) -> tuple[list[dict] | None, str | None]:
    """Sinh bộ kỹ năng cốt lõi cho 1 nghề + tài liệu học ngoài trường.

    Args:
        career_name: VD "Backend Developer"
        career_description: mô tả ngắn nghề
        school_courses: list[{"code","name","credits","semester"}] — toàn bộ môn CTĐT

    Returns:
        (skills_list, provider) hoặc (None, None) nếu LLM fail.
        skills_list = [{
            "skill_group": str,
            "skill_name": str,
            "skill_type": str,
            "level": str,
            "priority": int,
            "school_covered": bool,
            "school_courses": [str],
            "source_type": str,
            "source_name": str,
            "source_url": str,
            "description": str,
            "estimated_hours": int,
        }, ...]
    """
    # Limit course list để giảm prompt size
    course_lines = []
    for c in school_courses[:120]:
        sem = c.get("semester")
        sem_str = f"HK{sem}" if sem else "?"
        course_lines.append(f'- {c["code"]} | {c["name"]} ({c.get("credits", 0):.0f} TC, {sem_str})')
    course_text = "\n".join(course_lines)

    prompt = f"""Bạn là cố vấn nghề nghiệp CNTT cho sinh viên Việt Nam.

NHIỆM VỤ: Xây dựng "Bộ kỹ năng" cho nghề **{career_name}** ({career_description}).

YÊU CẦU OUTPUT:
1. Chia 4-6 NHÓM kỹ năng (skill_group) theo độ ưu tiên — VD "Lập trình cơ bản", "Backend Frameworks", "Database", "DevOps & Cloud", "Soft Skills".
2. Mỗi nhóm có 2-5 skill cốt lõi.
3. MỖI skill cần xác định:
   - school_covered: TRUE nếu CTĐT bên dưới có môn dạy skill này, kèm school_courses=[mã môn].
   - school_covered: FALSE nếu KHÔNG có môn nào trong CTĐT dạy → BẮT BUỘC kèm 1 tài liệu học ngoài trường (source_type, source_name, source_url, estimated_hours).
4. Đa dạng nguồn: course (Coursera/Udemy/freeCodeCamp), book, project (tự build), practice (LeetCode/HackerRank), video (YouTube), docs (official).
5. Ưu tiên tài liệu MIỄN PHÍ.

CTĐT NGÀNH CNTT (tham chiếu để xác định school_covered):
{course_text}

Trả về JSON HỢP LỆ, KHÔNG markdown, KHÔNG giải thích:
{{
  "skills": [
    {{
      "skill_group": "Lập trình cơ bản",
      "skill_name": "Cấu trúc dữ liệu & Thuật toán",
      "skill_type": "language",
      "level": "intermediate",
      "priority": 1,
      "school_covered": true,
      "school_courses": ["7080216"],
      "source_type": "practice",
      "source_name": "LeetCode 100 bài Easy",
      "source_url": "https://leetcode.com/",
      "description": "Luyện tư duy thuật toán qua bài tập",
      "estimated_hours": 50
    }},
    ...
  ]
}}

skill_type ∈ {{"language","framework","tool","database","cloud","soft","theory","cert"}}
level ∈ {{"basic","intermediate","advanced"}}
priority: 1=must (cốt lõi), 2=should, 3=nice
source_type ∈ {{"course","book","project","practice","video","docs","cert"}}

Tổng số skill 15-25. CHỈ trả về JSON."""

    raw, provider = _llm_call_long(prompt, max_tokens=4000)
    if not raw:
        return None, None

    parsed = _extract_json(raw)
    if not parsed or not isinstance(parsed, dict):
        return None, None
    skills = parsed.get("skills")
    if not isinstance(skills, list) or not skills:
        return None, None

    # Validate + sanitize
    valid_types = {"language", "framework", "tool", "database", "cloud", "soft", "theory", "cert"}
    valid_levels = {"basic", "intermediate", "advanced"}
    valid_sources = {"course", "book", "project", "practice", "video", "docs", "cert"}

    cleaned: list[dict] = []
    for s in skills:
        if not isinstance(s, dict):
            continue
        name = str(s.get("skill_name", "")).strip()
        group = str(s.get("skill_group", "Khác")).strip() or "Khác"
        if not name:
            continue
        skill_type = str(s.get("skill_type", "tool")).strip().lower()
        if skill_type not in valid_types:
            skill_type = "tool"
        level = str(s.get("level", "")).strip().lower()
        level = level if level in valid_levels else None
        priority = s.get("priority", 2)
        try:
            priority = max(1, min(3, int(priority)))
        except Exception:
            priority = 2
        school_covered = bool(s.get("school_covered", False))
        school_courses_list = s.get("school_courses") or []
        if not isinstance(school_courses_list, list):
            school_courses_list = []
        school_courses_list = [str(c).strip() for c in school_courses_list if str(c).strip()]
        source_type = str(s.get("source_type", "")).strip().lower() or None
        if source_type and source_type not in valid_sources:
            source_type = None
        try:
            est_hours = int(s.get("estimated_hours") or 0) or None
        except Exception:
            est_hours = None
        cleaned.append({
            "skill_group": group,
            "skill_name": name,
            "skill_type": skill_type,
            "level": level,
            "priority": priority,
            "school_covered": school_covered,
            "school_courses": school_courses_list or None,
            "source_type": source_type,
            "source_name": (str(s.get("source_name", "")).strip() or None),
            "source_url": (str(s.get("source_url", "")).strip() or None),
            "description": (str(s.get("description", "")).strip() or None),
            "estimated_hours": est_hours,
        })

    return (cleaned if cleaned else None), provider
