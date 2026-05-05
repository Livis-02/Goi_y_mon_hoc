"""Tests cho intent detection và chat fallback (không cần API key)."""
from __future__ import annotations

from backend.core.chat_assistant import detect_intent_rule


def test_intent_recommend():
    assert detect_intent_rule("Tôi nên học môn gì tiếp theo?") == "recommend"
    assert detect_intent_rule("Gợi ý môn học cho mình") == "recommend"


def test_intent_progress():
    assert detect_intent_rule("Tiến độ của tôi đến đâu rồi?") == "progress"
    assert detect_intent_rule("Tôi còn thiếu bao nhiêu tín chỉ?") == "progress"


def test_intent_graduation():
    assert detect_intent_rule("Tôi đủ điều kiện tốt nghiệp chưa?") == "graduation"
    assert detect_intent_rule("Bao giờ tôi ra trường được?") == "graduation"


def test_intent_internship():
    assert detect_intent_rule("Tôi đủ điều kiện thực tập chưa?") == "internship"


def test_intent_thesis():
    assert detect_intent_rule("Điều kiện làm đồ án tốt nghiệp là gì?") == "thesis"


def test_intent_prereq():
    assert detect_intent_rule("Môn nào cần học trước môn CSDL?") == "prereq"


def test_intent_career():
    assert detect_intent_rule("Tôi hợp định hướng nghề nghiệp nào?") == "career"


def test_intent_course_info():
    assert detect_intent_rule("Môn Trí tuệ nhân tạo dạy về gì?") == "course_info"
    assert detect_intent_rule("Môn Mạng máy tính học được gì?") == "course_info"


def test_intent_general_fallback():
    # Các câu không khớp bất kỳ intent nào → fallback "general"
    assert detect_intent_rule("Bạn tên là gì?") == "general"
    assert detect_intent_rule("Cho mình hỏi tí") == "general"


def test_chat_endpoint_no_data(client, auth_headers):
    """Chat phải trả 200 kể cả khi chưa có dữ liệu điểm."""
    resp = client.post("/chat/me", json={"message": "Tôi nên học gì?"}, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_chat_greeting(client, auth_headers):
    """Chat với lời chào phải trả lời, không crash."""
    resp = client.post("/chat/me", json={"message": "hello"}, headers=auth_headers)
    assert resp.status_code == 200


def test_chat_empty_message(client, auth_headers):
    """Tin nhắn rỗng phải bị từ chối (422)."""
    resp = client.post("/chat/me", json={"message": ""}, headers=auth_headers)
    assert resp.status_code == 422
