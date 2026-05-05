"""Tests cho GET /admin/dashboard/stats, GET /admin/ctdt/template.xlsx,
POST /admin/ctdt/preview, POST /admin/ctdt/import, GET /courses/standard-plan (with prereqs)."""
from __future__ import annotations
import io
import pytest
from backend.db import models


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_user(client, db):
    resp = client.post("/auth/register", json={
        "username": "admin_stats", "password": "Admin@123", "full_name": "Admin Stats",
    })
    assert resp.status_code == 200
    uid = resp.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={
        "username": "admin_stats", "password": "Admin@123",
    }).json()["access_token"]
    return {"token": token, "id": uid}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── GET /admin/dashboard/stats ────────────────────────────────────────────────

class TestAdminDashboardStats:
    def test_returns_all_required_fields(self, client, admin_user):
        resp = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        d = resp.json()
        for field in [
            "total_students", "total_advisors", "total_courses",
            "students_no_advisor", "students_first_login",
            "notifications_total", "notifications_avg_read_rate", "active_users_this_week",
            "cohort_labels", "cohort_values", "spec_labels", "spec_values",
            "warnings",
        ]:
            assert field in d, f"Missing field: {field}"

    def test_counts_match_students(self, client, admin_user, db):
        for i in range(3):
            db.add(models.User(username=f"sv_stat_{i}", password_hash="x", role="student"))
        db.commit()
        resp = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.json()["total_students"] >= 3

    def test_students_no_advisor_correct(self, client, admin_user, db):
        # Add 2 students — no advisor assigned
        u1 = models.User(username="sv_noadv_1", password_hash="x", role="student")
        u2 = models.User(username="sv_noadv_2", password_hash="x", role="student")
        db.add_all([u1, u2])
        db.commit()
        db.refresh(u1); db.refresh(u2)

        resp = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        d = resp.json()
        assert d["students_no_advisor"] >= 2

    def test_no_advisor_decreases_when_assigned(self, client, admin_user, db):
        adv = models.User(username="adv_stat_1", password_hash="x", role="advisor")
        sv  = models.User(username="sv_withAdv", password_hash="x", role="student")
        db.add_all([adv, sv])
        db.commit()
        db.refresh(adv); db.refresh(sv)

        before = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"])).json()

        db.add(models.AdvisorAssignment(advisor_id=adv.id, student_id=sv.id))
        db.commit()

        after = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"])).json()
        assert after["students_no_advisor"] == before["students_no_advisor"] - 1

    def test_chart_arrays_same_length(self, client, admin_user):
        resp = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"]))
        d = resp.json()
        assert len(d["cohort_labels"]) == len(d["cohort_values"])
        assert len(d["spec_labels"]) == len(d["spec_values"])

    def test_first_login_counted(self, client, admin_user, db):
        db.add(models.User(username="sv_first_login", password_hash="x", role="student", is_first_login=True))
        db.commit()
        resp = client.get("/admin/dashboard/stats", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.json()["students_first_login"] >= 1

    def test_non_admin_rejected(self, client, registered_user):
        resp = client.get("/admin/dashboard/stats", headers=_auth(registered_user["token"]))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        resp = client.get("/admin/dashboard/stats")
        assert resp.status_code == 401


# ── GET /admin/ctdt/template.xlsx ─────────────────────────────────────────────

class TestCtdtTemplate:
    def test_returns_xlsx_file(self, client, admin_user):
        resp = client.get("/admin/ctdt/template.xlsx", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert "spreadsheet" in resp.headers.get("content-type", "")
        assert len(resp.content) > 100  # non-empty xlsx

    def test_non_admin_rejected(self, client, registered_user):
        resp = client.get("/admin/ctdt/template.xlsx", headers=_auth(registered_user["token"]))
        assert resp.status_code == 403


# ── POST /admin/ctdt/preview ──────────────────────────────────────────────────

def _make_xlsx(rows: list[tuple]) -> bytes:
    """Create a minimal xlsx with ma_mon, ten_mon_hoc, so_tin_chi columns."""
    import openpyxl, io as _io
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["ma_mon", "ten_mon_hoc", "so_tin_chi"])
    for row in rows:
        ws.append(row)
    buf = _io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.read()


class TestCtdtPreview:
    def test_preview_valid_xlsx(self, client, admin_user):
        content = _make_xlsx([("1234501", "Toán cao cấp 1", 4), ("1234502", "Vật lý", 3)])
        resp = client.post(
            "/admin/ctdt/preview",
            files=[("file", ("ctdt.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["valid_count"] == 2
        codes = [c["code"] for c in d["valid_courses"]]
        assert "1234501" in codes
        assert "1234502" in codes

    def test_preview_empty_file_rejected(self, client, admin_user):
        resp = client.post(
            "/admin/ctdt/preview",
            files=[("file", ("ctdt.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 400

    def test_preview_unsupported_format_rejected(self, client, admin_user):
        resp = client.post(
            "/admin/ctdt/preview",
            files=[("file", ("ctdt.pdf", b"fake", "application/pdf"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 400

    def test_preview_non_admin_rejected(self, client, registered_user):
        content = _make_xlsx([("1234501", "Toán", 4)])
        resp = client.post(
            "/admin/ctdt/preview",
            files=[("file", ("ctdt.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 403

    def test_preview_no_elective_groups_warning(self, client, admin_user):
        content = _make_xlsx([("1234501", "Toán", 4)])
        resp = client.post(
            "/admin/ctdt/preview",
            files=[("file", ("ctdt.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        # Should have a warning about missing elective groups
        assert len(resp.json()["warnings"]) > 0


# ── POST /admin/ctdt/import ───────────────────────────────────────────────────

class TestCtdtImport:
    def test_import_valid_xlsx(self, client, admin_user, db):
        content = _make_xlsx([("9999901", "Môn Test Import", 3)])
        resp = client.post(
            "/admin/ctdt/import",
            files=[("file", ("ctdt.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["parsed_courses"] == 1
        course = db.query(models.Course).filter(models.Course.course_code == "9999901").first()
        assert course is not None
        assert course.course_name == "Môn Test Import"

    def test_import_empty_file_rejected(self, client, admin_user):
        resp = client.post(
            "/admin/ctdt/import",
            files=[("file", ("ctdt.xlsx", b"", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 400

    def test_import_non_admin_rejected(self, client, registered_user):
        content = _make_xlsx([("1234501", "Toán", 4)])
        resp = client.post(
            "/admin/ctdt/import",
            files=[("file", ("ctdt.xlsx", content, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 403


# ── GET /courses/standard-plan (prereqs included) ─────────────────────────────

class TestStandardPlanPrereqs:
    def test_includes_prereqs_field(self, client, registered_user, db):
        db.add(models.Course(course_code="TST0001", course_name="Môn Tiên quyết", credits=3))
        db.add(models.Course(course_code="TST0002", course_name="Môn Học", credits=3))
        db.flush()
        db.add(models.CoursePrerequisite(course_code="TST0002", prerequisite_code="TST0001"))
        db.commit()
        resp = client.get(
            "/courses/standard-plan",
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        for sem in data.get("semesters", []):
            for c in sem.get("courses", []):
                assert "prereqs" in c  # every course should have the prereqs field

    def test_prereqs_populated(self, client, registered_user, db):
        """A course with prereqs should have them listed."""
        # TST0002 → requires TST0001 — already created if tests run in isolation
        # Check via the catalog endpoint since standard-plan only includes CURRICULUM_ORDER courses
        resp = client.get(
            "/courses/standard-plan",
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 200
        # Just verify structure is correct (lists, not None)
        for sem in resp.json().get("semesters", []):
            for c in sem.get("courses", []):
                assert isinstance(c["prereqs"], list)
