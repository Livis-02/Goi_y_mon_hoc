"""Tests cho 7 Advisor API routes."""
from __future__ import annotations
import pytest
from backend.db import models


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def advisor_user(client, db):
    """Tạo tài khoản advisor và trả về token."""
    resp = client.post("/auth/register", json={
        "username": "advisor01",
        "password": "Advisor@1",
        "full_name": "Cố Vấn Test",
    })
    assert resp.status_code == 200
    user_id = resp.json()["id"]
    # Set role thành advisor trực tiếp trong DB
    db.query(models.User).filter(models.User.id == user_id).update({"role": "advisor"})
    db.commit()

    token = client.post("/auth/login", json={
        "username": "advisor01", "password": "Advisor@1",
    }).json()["access_token"]
    return {"token": token, "id": user_id}


@pytest.fixture()
def student_user(client):
    """Tạo tài khoản sinh viên và trả về id + token."""
    resp = client.post("/auth/register", json={
        "username": "sv_test01",
        "password": "Student@1",
        "full_name": "Sinh Viên Được Phân Công",
    })
    assert resp.status_code == 200
    return {"id": resp.json()["id"], "username": "sv_test01"}


@pytest.fixture()
def assigned(advisor_user, student_user, db):
    """Phân công student_user cho advisor_user."""
    existing = db.query(models.AdvisorAssignment).filter_by(
        advisor_id=advisor_user["id"],
        student_id=student_user["id"],
    ).first()
    if not existing:
        db.add(models.AdvisorAssignment(
            advisor_id=advisor_user["id"],
            student_id=student_user["id"],
        ))
        db.commit()
    return {"advisor": advisor_user, "student": student_user}


def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestAdvisorAccess:
    def test_student_cannot_access_advisor_routes(self, client, registered_user):
        """Student role bị từ chối 403."""
        h = {"Authorization": f"Bearer {registered_user['token']}"}
        assert client.get("/advisor/students", headers=h).status_code == 403

    def test_unauthenticated_rejected(self, client):
        assert client.get("/advisor/students").status_code == 401

    def test_advisor_can_list_students(self, client, advisor_user):
        resp = client.get("/advisor/students", headers=_headers(advisor_user["token"]))
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


class TestAdvisorStudentList:
    def test_empty_list_when_no_assignments(self, client, advisor_user):
        resp = client.get("/advisor/students", headers=_headers(advisor_user["token"]))
        assert resp.status_code == 200
        assert resp.json() == []

    def test_assigned_student_appears(self, client, assigned):
        resp = client.get(
            "/advisor/students",
            headers=_headers(assigned["advisor"]["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        item = data[0]
        assert item["id"] == assigned["student"]["id"]
        assert item["username"] == "sv_test01"
        assert item["status"] in ("normal", "needs_attention", "high_risk")
        assert "assigned_at" in item

    def test_status_fields_present(self, client, assigned):
        resp = client.get(
            "/advisor/students",
            headers=_headers(assigned["advisor"]["token"]),
        )
        item = resp.json()[0]
        assert "earned_credits" in item
        assert "avg_score4" in item
        assert "status" in item


class TestAdvisorStudentDetail:
    def test_student_detail_returns_progress(self, client, assigned):
        sid = assigned["student"]["id"]
        resp = client.get(
            f"/advisor/students/{sid}",
            headers=_headers(assigned["advisor"]["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        # ProgressOut fields
        assert "earned_credits" in data
        assert "graduation_threshold" in data
        assert "completion_percent" in data

    def test_cannot_view_unassigned_student(self, client, advisor_user, db):
        # Tạo SV không được phân công
        other = models.User(username="other_sv", password_hash="x", role="student")
        db.add(other)
        db.commit()
        db.refresh(other)

        resp = client.get(
            f"/advisor/students/{other.id}",
            headers=_headers(advisor_user["token"]),
        )
        assert resp.status_code == 403

    def test_nonexistent_student_returns_404(self, client, assigned):
        resp = client.get(
            "/advisor/students/999999",
            headers=_headers(assigned["advisor"]["token"]),
        )
        # admin bypass qua check → 404; advisor không assigned → 403
        assert resp.status_code in (403, 404)


class TestAdvisorRecommendations:
    def test_recommendations_returns_list(self, client, assigned):
        sid = assigned["student"]["id"]
        resp = client.get(
            f"/advisor/students/{sid}/recommendations",
            headers=_headers(assigned["advisor"]["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "recommendations" in data
        assert isinstance(data["recommendations"], list)

    def test_unassigned_student_rejected(self, client, advisor_user, db):
        other = models.User(username="unreachable_sv", password_hash="x", role="student")
        db.add(other)
        db.commit()
        db.refresh(other)
        resp = client.get(
            f"/advisor/students/{other.id}/recommendations",
            headers=_headers(advisor_user["token"]),
        )
        assert resp.status_code == 403


class TestAdvisorStats:
    def test_stats_empty(self, client, advisor_user):
        resp = client.get("/advisor/stats", headers=_headers(advisor_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_students"] == 0
        assert data["high_risk_count"] == 0

    def test_stats_with_student(self, client, assigned):
        resp = client.get(
            "/advisor/stats",
            headers=_headers(assigned["advisor"]["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_students"] == 1
        assert "avg_gpa4" in data
        assert "avg_completion_percent" in data
        assert data["high_risk_count"] + data["needs_attention_count"] + data["normal_count"] == 1


class TestAdvisorNotes:
    def test_create_note(self, client, assigned):
        sid = assigned["student"]["id"]
        resp = client.post("/advisor/notes", json={
            "student_id": sid,
            "content": "SV có biểu hiện tốt, tiếp tục theo dõi.",
        }, headers=_headers(assigned["advisor"]["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "SV có biểu hiện tốt, tiếp tục theo dõi."
        assert data["student_id"] == sid
        assert data["advisor_id"] == assigned["advisor"]["id"]

    def test_get_notes_returns_list(self, client, assigned):
        sid = assigned["student"]["id"]
        token = assigned["advisor"]["token"]
        # Tạo 2 ghi chú
        client.post("/advisor/notes", json={"student_id": sid, "content": "Ghi chú 1"},
                    headers=_headers(token))
        client.post("/advisor/notes", json={"student_id": sid, "content": "Ghi chú 2"},
                    headers=_headers(token))

        resp = client.get(f"/advisor/notes/{sid}", headers=_headers(token))
        assert resp.status_code == 200
        notes = resp.json()
        assert len(notes) == 2
        # Mới nhất lên trên
        assert notes[0]["content"] == "Ghi chú 2"

    def test_update_note(self, client, assigned):
        sid = assigned["student"]["id"]
        token = assigned["advisor"]["token"]

        create_resp = client.post("/advisor/notes", json={
            "student_id": sid, "content": "Nội dung cũ",
        }, headers=_headers(token))
        note_id = create_resp.json()["id"]

        update_resp = client.put(f"/advisor/notes/{note_id}", json={
            "content": "Nội dung đã sửa",
        }, headers=_headers(token))
        assert update_resp.status_code == 200
        assert update_resp.json()["content"] == "Nội dung đã sửa"

    def test_empty_note_rejected(self, client, assigned):
        sid = assigned["student"]["id"]
        resp = client.post("/advisor/notes", json={
            "student_id": sid, "content": "",
        }, headers=_headers(assigned["advisor"]["token"]))
        assert resp.status_code == 422

    def test_cannot_create_note_for_unassigned_student(self, client, advisor_user, db):
        other = models.User(username="unassigned_sv2", password_hash="x", role="student")
        db.add(other)
        db.commit()
        db.refresh(other)
        resp = client.post("/advisor/notes", json={
            "student_id": other.id, "content": "Ghi chú không hợp lệ",
        }, headers=_headers(advisor_user["token"]))
        assert resp.status_code == 403

    def test_cannot_update_other_advisors_note(self, client, assigned, db):
        """Advisor khác không được sửa ghi chú."""
        sid = assigned["student"]["id"]
        token = assigned["advisor"]["token"]

        # Tạo ghi chú
        note_id = client.post("/advisor/notes", json={
            "student_id": sid, "content": "Ghi chú gốc",
        }, headers=_headers(token)).json()["id"]

        # Tạo advisor thứ hai (1 SV chỉ thuộc 1 GV nên advisor2 không có assignment với SV này;
        # quyền sửa note đã giới hạn ở chính advisor tạo, không liên quan đến assignment)
        client.post("/auth/register", json={
            "username": "advisor02", "password": "Advisor@2", "full_name": "CV2",
        })
        user2 = db.query(models.User).filter(models.User.username == "advisor02").first()
        user2.role = "advisor"
        db.commit()
        token2 = client.post("/auth/login", json={
            "username": "advisor02", "password": "Advisor@2",
        }).json()["access_token"]

        resp = client.put(f"/advisor/notes/{note_id}", json={"content": "Thay đổi trái phép"},
                          headers=_headers(token2))
        assert resp.status_code == 403


class TestStudentCourseNotes:
    """SV xem note theo môn từ cố vấn của mình (Phase 9.B1)."""

    def test_student_sees_advisor_course_notes(self, client, assigned, db):
        sid = assigned["student"]["id"]
        adv_token = assigned["advisor"]["token"]
        # Login as student
        student_token = client.post("/auth/login", json={
            "username": assigned["student"]["username"], "password": "Student@1",
        }).json()["access_token"]

        # Advisor creates 2 course-scoped notes + 1 general note
        client.post("/advisor/notes", json={
            "student_id": sid, "content": "Môn này hơi nặng, học sau",
            "course_code": "7080111",
        }, headers=_headers(adv_token))
        client.post("/advisor/notes", json={
            "student_id": sid, "content": "Đăng ký song song với 7080207",
            "course_code": "7080111",
        }, headers=_headers(adv_token))
        client.post("/advisor/notes", json={
            "student_id": sid, "content": "Note chung không gắn môn",
        }, headers=_headers(adv_token))

        # Student fetches own course-notes
        resp = client.get("/me/course-notes", headers=_headers(student_token))
        assert resp.status_code == 200
        data = resp.json()
        assert "7080111" in data
        assert len(data["7080111"]) == 2
        assert all("content" in n and "advisor_name" in n for n in data["7080111"])
        # General note (no course_code) must NOT appear here
        assert all(code != "" for code in data.keys())

    def test_advisor_role_blocked_from_me_course_notes(self, client, assigned):
        adv_token = assigned["advisor"]["token"]
        resp = client.get("/me/course-notes", headers=_headers(adv_token))
        assert resp.status_code == 403
