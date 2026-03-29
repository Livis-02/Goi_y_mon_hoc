from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib import request

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend import models
from backend.academic_engine import (
    build_progress_snapshot,
    build_recommendations,
    GRADUATION_CREDIT_THRESHOLD,
)


ALLOWED_INTENTS = {
    "recommend", "progress", "career", "explain", "general",
    "graduation", "internship", "thesis", "prereq",
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

    if any(k in mn for k in ["tot nghiep", "co the ra truong", "du dieu kien ra truong", "bao gio ra truong"]):
        return "graduation"
    if any(k in mn for k in ["thuc tap", "thuc hanh doanh nghiep", "dieu kien thuc tap"]):
        return "internship"
    if any(k in mn for k in ["do an", "luan van", "dieu kien lam do an"]):
        return "thesis"
    if any(k in mn for k in ["tien quyet", "dieu kien hoc", "mon nao can hoc truoc", "prereq"]):
        return "prereq"
    if any(k in mn for k in ["goi y", "nen hoc", "mon nao", "recommend", "hoc gi", "hoc them gi"]):
        return "recommend"
    if any(k in mn for k in ["tien do", "%", "con thieu", "progress", "hoan thanh", "bao nhieu tin chi"]):
        return "progress"
    if any(k in mn for k in ["nghe nghiep", "career", "dinh huong", "hop nganh", "lam gi", "huong di"]):
        return "career"
    if any(k in mn for k in ["tai sao", "vi sao", "giai thich", "explain", "ly do"]):
        return "explain"
    return "general"


def _openai_chat(messages: list[dict], temperature: float = 0.2, max_tokens: int = 500) -> str | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
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
        with request.urlopen(req, timeout=25) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def detect_intent_llm(message: str) -> str | None:
    allowed = "|".join(sorted(ALLOWED_INTENTS))
    raw = _openai_chat(
        [
            {
                "role": "system",
                "content": f"Phan loai intent. Chi duoc tra ve duy nhat 1 tu: {allowed}",
            },
            {"role": "user", "content": message},
        ],
        temperature=0,
        max_tokens=10,
    )
    if not raw:
        return None
    intent = _normalize(raw).split()[0]
    return intent if intent in ALLOWED_INTENTS else None


def _career_from_progress(progress: dict) -> tuple[str, float, list[str]]:
    avg10 = progress.get("avg_score10") or 0
    if avg10 >= 8.0:
        return "Dữ liệu / AI", 0.82, ["Điểm trung bình cao", "Có thể theo các môn khó hơn về AI/Data"]
    if avg10 >= 7.0:
        return "Phát triển phần mềm", 0.74, ["Nền tảng ổn định", "Phù hợp lộ trình phát triển hệ thống"]
    return "Hỗ trợ hệ thống / QA", 0.61, ["Nên ưu tiên môn nền tảng", "Cần cải thiện điểm các môn cốt lõi"]


def _recent_memory(db: Session, user_id: int, limit: int = 8) -> list[models.ChatMessage]:
    try:
        rows = (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.user_id == user_id)
            .order_by(models.ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return list(reversed(rows))
    except SQLAlchemyError:
        db.rollback()
        return []


def _save_memory(db: Session, user_id: int, role: str, message: str, intent: str | None = None) -> None:
    try:
        db.add(models.ChatMessage(user_id=user_id, role=role, message=message, intent=intent))
        db.commit()
    except SQLAlchemyError:
        db.rollback()


def _no_data_reply(intent: str) -> ChatIntentResult:
    return ChatIntentResult(
        intent=intent,
        answer="Chưa có dữ liệu điểm. Hãy upload bảng điểm để tôi hỗ trợ bạn.",
        suggestions=[],
    )


def _local_router(intent: str, db: Session, user_id: int, limit: int) -> ChatIntentResult:

    if intent == "graduation":
        p = build_progress_snapshot(db, user_id)
        if p["earned_credits"] == 0:
            return _no_data_reply(intent)
        earned = p["earned_credits"]
        threshold = GRADUATION_CREDIT_THRESHOLD
        short = threshold - earned
        if p["graduation_ready"]:
            answer = (
                f"Bạn đã đạt {earned} TC — đủ điều kiện tốt nghiệp ({threshold} TC yêu cầu). "
            )
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
            elif not p["internship_done"]:
                remaining_non_special = (
                    p["total_credits"] - p["earned_credits"]
                    - (p.get("thesis_outstanding") or 8)
                    - (p.get("internship_outstanding") or 2)
                )
                answer += f" Cần hoàn thành thêm các môn học trước khi đủ điều kiện thực tập."
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
                "Bạn đủ điều kiện đăng ký thực tập doanh nghiệp! "
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
                "Bạn đủ điều kiện đăng ký Đồ án tốt nghiệp! "
                "Thực tập đã hoàn thành — hãy liên hệ giảng viên để bắt đầu."
            )
        elif p["internship_done"]:
            answer = "Thực tập đã xong nhưng điều kiện Đồ án chưa đủ. Kiểm tra lại các môn bắt buộc."
        else:
            answer = (
                "Bạn cần hoàn thành thực tập doanh nghiệp trước khi làm Đồ án tốt nghiệp."
            )
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
        if p["graduation_ready"]:
            answer += f" Đủ điều kiện tốt nghiệp ({GRADUATION_CREDIT_THRESHOLD:.0f} TC)."
        else:
            answer += f" Cần thêm {GRADUATION_CREDIT_THRESHOLD - earned:.0f} TC để đủ điều kiện tốt nghiệp."
        if p["thesis_eligible"]:
            answer += " Đủ điều kiện làm Đồ án tốt nghiệp."
        elif p["internship_eligible"]:
            answer += " Đủ điều kiện thực tập doanh nghiệp."
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

    if intent == "career":
        p = build_progress_snapshot(db, user_id)
        career, conf, reasons = _career_from_progress(p)
        answer = f"Định hướng phù hợp: **{career}** (độ phù hợp {round(conf*100,1)}%). Lý do: " + "; ".join(reasons)
        return ChatIntentResult(intent=intent, answer=answer, suggestions=[])

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


def _rewrite_with_llm(message: str, local: ChatIntentResult, memory: list[models.ChatMessage]) -> str | None:
    hist = "\n".join([f"{m.role}: {m.message}" for m in memory[-6:]])
    prompt = (
        f"Câu hỏi: {message}\n"
        f"Intent: {local.intent}\n"
        f"Kết quả hệ thống: {local.answer}\n"
        f"Lịch sử gần đây:\n{hist}\n\n"
        "Viết lại câu trả lời bằng tiếng Việt tự nhiên, thân thiện, ngắn gọn. "
        "Không được bịa thêm dữ liệu ngoài kết quả đã cho."
    )
    return _openai_chat(
        [
            {
                "role": "system",
                "content": (
                    "Bạn là trợ lý học tập CNTT. Trả lời ngắn gọn, rõ ràng, thân thiện bằng tiếng Việt. "
                    "Chỉ dùng dữ liệu từ kết quả hệ thống, không được sáng tạo số liệu."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        max_tokens=380,
    )


def chat_reply(
    message: str,
    db: Session,
    user_id: int,
    limit: int = 5,
    prefer_llm: bool = True,
) -> ChatIntentResult:
    message = (message or "").strip()
    if not message:
        return ChatIntentResult(intent="general", answer="Bạn hãy nhập nội dung câu hỏi.", suggestions=[])

    memory = _recent_memory(db, user_id, limit=8)

    llm_intent = detect_intent_llm(message) if prefer_llm else None
    intent = llm_intent or detect_intent_rule(message)
    if intent not in ALLOWED_INTENTS:
        intent = "general"

    local = _local_router(intent, db, user_id, limit)

    final_answer = local.answer
    if prefer_llm:
        rewritten = _rewrite_with_llm(message, local, memory)
        if rewritten:
            final_answer = rewritten

    _save_memory(db, user_id, "user", message, intent=intent)
    _save_memory(db, user_id, "assistant", final_answer, intent=intent)

    return ChatIntentResult(intent=intent, answer=final_answer, suggestions=local.suggestions)


def get_chat_history(db: Session, user_id: int, limit: int = 30) -> list[models.ChatMessage]:
    try:
        return (
            db.query(models.ChatMessage)
            .filter(models.ChatMessage.user_id == user_id)
            .order_by(models.ChatMessage.created_at.desc())
            .limit(max(1, min(limit, 100)))
            .all()
        )
    except SQLAlchemyError:
        db.rollback()
        return []
