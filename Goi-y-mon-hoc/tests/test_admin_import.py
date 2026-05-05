"""Tests cho POST /admin/users/import và POST /admin/grades/import."""
from __future__ import annotations
import io
import pytest
from backend.db import models


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_user(client, db):
    resp = client.post("/auth/register", json={
        "username": "admin_imp", "password": "Admin@123", "full_name": "Admin Import",
    })
    assert resp.status_code == 200
    uid = resp.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={"username": "admin_imp", "password": "Admin@123"}).json()["access_token"]
    return {"token": token, "id": uid}


def _auth(token): return {"Authorization": f"Bearer {token}"}


def _csv_file(content: str, filename: str = "students.csv"):
    return ("file", (filename, io.BytesIO(content.encode("utf-8-sig")), "text/csv"))


# ── POST /admin/users/import ──────────────────────────────────────────────────

class TestAdminUsersImport:
    def test_import_creates_students(self, client, admin_user):
        csv = "username,password,full_name\nsv001,Pass@1,Nguyen Van A\nsv002,Pass@2,Tran Thi B\n"
        resp = client.post("/admin/users/import",
                           files=[_csv_file(csv)],
                           headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 2
        assert data["skipped_count"] == 0
        assert data["errors"] == []

    def test_duplicate_skipped(self, client, admin_user):
        csv = "username,password,full_name\nsv_dup,Pass@1,SV Dup\n"
        # First import
        client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        # Second import with same username
        resp = client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 0
        assert data["skipped_count"] == 1

    def test_autogen_password_when_missing(self, client, admin_user):
        csv = "username,full_name\nsv_nopass,SV No Pass\n"
        resp = client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 1
        # Auto-gen password should be returned
        assert "sv_nopass" in data["generated_passwords"]
        pw = data["generated_passwords"]["sv_nopass"]
        assert len(pw) == 6 and pw.isdigit()

    def test_created_user_can_login(self, client, admin_user):
        csv = "username,password\nsv_login_test,SecurePass@9\n"
        client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        resp = client.post("/auth/login", json={"username": "sv_login_test", "password": "SecurePass@9"})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_empty_file_rejected(self, client, admin_user):
        resp = client.post("/admin/users/import",
                           files=[_csv_file("username,password\n")],
                           headers=_auth(admin_user["token"]))
        assert resp.status_code == 400

    def test_non_admin_rejected(self, client, registered_user):
        csv = "username,password\nsv_x,Pass@1\n"
        resp = client.post("/admin/users/import",
                           files=[_csv_file(csv)],
                           headers=_auth(registered_user["token"]))
        assert resp.status_code == 403

    def test_unauthenticated_rejected(self, client):
        csv = "username,password\nsv_y,Pass@1\n"
        resp = client.post("/admin/users/import", files=[_csv_file(csv)])
        assert resp.status_code == 401

    def test_import_with_specialization(self, client, admin_user):
        csv = "username,password,full_name,specialization\nsv_spec,Pass@1,SV Spec,Kỹ thuật phần mềm\n"
        resp = client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.json()["created_count"] == 1

    def test_invalid_specialization_ignored(self, client, admin_user, db):
        csv = "username,password,specialization\nsv_badspec,Pass@1,Chuyên ngành ảo\n"
        resp = client.post("/admin/users/import", files=[_csv_file(csv)], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        # User still created, specialization just set to NULL
        assert resp.json()["created_count"] == 1
        u = db.query(models.User).filter(models.User.username == "sv_badspec").first()
        assert u is not None
        assert u.specialization is None

    def test_mixed_valid_and_duplicate(self, client, admin_user):
        csv1 = "username,password\nsv_mix1,Pass@1\nsv_mix2,Pass@2\n"
        client.post("/admin/users/import", files=[_csv_file(csv1)], headers=_auth(admin_user["token"]))
        csv2 = "username,password\nsv_mix1,Pass@1\nsv_mix3,Pass@3\n"
        resp = client.post("/admin/users/import", files=[_csv_file(csv2)], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["created_count"] == 1
        assert data["skipped_count"] == 1


# ── POST /admin/grades/import ─────────────────────────────────────────────────

# File điểm tối thiểu hợp lệ — header khớp với extract_grades()
# Dòng đầu "Ma sinh vien: sv_grade_imp" để endpoint tự detect student
_GRADES_CSV = (
    "Ma sinh vien: sv_grade_imp\n"
    "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
    "INT1234,Lap trinh can ban,3,8.5,3.5,B+,Dat\n"
    "INT5678,Co so du lieu,3,5.0,2.0,D,Dat\n"
)

_GRADES_CSV_UNKNOWN = (
    "Ma sinh vien: sv_grade_imp\n"
    "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
    "ZZZUNKNOWN,Mon khong co,3,8.0,3.5,B+,Dat\n"
)

# File với student không tồn tại → endpoint tự tạo tài khoản mới
_GRADES_CSV_NEW_STUDENT = (
    "Ma sinh vien: sv_autocreated\n"
    "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
    "INT1234,Lap trinh can ban,3,8.5,3.5,B+,Dat\n"
)


def _grade_file(content: str = _GRADES_CSV):
    return ("file", ("grades.csv", io.BytesIO(content.encode("utf-8-sig")), "text/csv"))


@pytest.fixture()
def student_for_import(client, admin_user):
    """Tạo SV để test grades import."""
    csv = "username,password,full_name\nsv_grade_imp,Pass@123,SV Grade Import\n"
    client.post("/admin/users/import",
                files=[_csv_file(csv)],
                headers=_auth(admin_user["token"]))
    u = client.get("/admin/users", headers=_auth(admin_user["token"])).json()
    sv = next(x for x in u["users"] if x["username"] == "sv_grade_imp")
    return sv


@pytest.fixture()
def course_in_db(db):
    """Thêm 2 môn học vào DB để grades có thể match."""
    db.add(models.Course(
        course_code="INT1234", course_name="Lap trinh can ban",
        credits=3, count_toward_credits=True,
    ))
    db.add(models.Course(
        course_code="INT5678", course_name="Co so du lieu",
        credits=3, count_toward_credits=True,
    ))
    db.commit()


class TestAdminGradesImport:
    def test_import_grades_basic(self, client, admin_user, student_for_import, course_in_db):
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file()],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["grades_imported"] == 2
        assert data["student_code"] == "sv_grade_imp"
        assert data["account_created"] is False

    def test_unknown_course_skipped(self, client, admin_user, student_for_import, course_in_db):
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file(_GRADES_CSV_UNKNOWN)],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["grades_imported"] == 0
        assert data["student_code"] == "sv_grade_imp"

    def test_grades_replace_on_reimport(self, client, admin_user, student_for_import, course_in_db):
        # First import: 2 rows
        client.post("/admin/grades/import",
                    files=[_grade_file()], headers=_auth(admin_user["token"]))
        # Second import: same file — should replace, not duplicate
        resp = client.post("/admin/grades/import",
                           files=[_grade_file()], headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.json()["grades_imported"] == 2

    def test_autocreate_account_for_new_student(self, client, admin_user, course_in_db):
        """Sinh viên chưa có tài khoản → tự động tạo mới."""
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file(_GRADES_CSV_NEW_STUDENT)],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_created"] is True
        assert data["student_code"] == "sv_autocreated"
        assert data["password_plain"] is not None
        assert len(data["password_plain"]) == 6
        assert data["grades_imported"] == 1

    def test_non_admin_rejected(self, client, registered_user):
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file()],
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 403

    def test_empty_grades_file_rejected(self, client, admin_user):
        empty = "Ma mon,Ten mon hoc,So tin chi\n"
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file(empty)],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 400

    def test_no_zombie_account_when_grades_empty(self, client, db, admin_user):
        """VIỆC 6: khi file không có điểm, không có tài khoản zombie được tạo."""
        no_grades = (
            "Ma sinh vien: sv_zombie_test\n"
            "Ma mon,Ten mon hoc,So tin chi\n"
        )
        resp = client.post(
            "/admin/grades/import",
            files=[_grade_file(no_grades)],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 400
        # No zombie user should exist
        u = db.query(models.User).filter(models.User.username == "sv_zombie_test").first()
        assert u is None

    def test_rollback_on_grade_insert_error(self, client, db, admin_user, course_in_db, monkeypatch):
        """V6: nếu lưu grade raise exception sau khi tạo student, transaction phải rollback toàn bộ."""
        student_code = "sv_rback_grade_err"
        assert db.query(models.User).filter(models.User.username == student_code).first() is None

        # Patch UserGrade.__init__ to raise — simulates a DB constraint violation during grade insert
        def _failing_grade_init(self_inner, **kwargs):
            raise Exception("Simulated constraint error on grade insert")

        monkeypatch.setattr(models.UserGrade, "__init__", _failing_grade_init)

        content = (
            f"Ma sinh vien: {student_code}\n"
            "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
            "INT1234,Lap trinh can ban,3,8.5,3.5,B+,Dat\n"
        )
        resp = client.post(
            "/admin/grades/import",
            files=[("file", ("g.csv", io.BytesIO(content.encode("utf-8-sig")), "text/csv"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 500

        # Savepoint must have rolled back: no zombie student in DB
        db.expire_all()
        u = db.query(models.User).filter(models.User.username == student_code).first()
        assert u is None, f"Zombie student was not rolled back: {u}"

    def test_success_commits_student_and_grades(self, client, db, admin_user, course_in_db):
        """V6: import thành công → student + grades đều có trong DB."""
        student_code = "sv_rback_success"
        content = (
            f"Ma sinh vien: {student_code}\n"
            "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
            "INT1234,Lap trinh can ban,3,8.5,3.5,B+,Dat\n"
            "INT5678,Co so du lieu,3,7.0,3.0,B,Dat\n"
        )
        resp = client.post(
            "/admin/grades/import",
            files=[("file", ("g.csv", io.BytesIO(content.encode("utf-8-sig")), "text/csv"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        d = resp.json()
        assert d["grades_imported"] == 2
        assert d["account_created"] is True

        db.expire_all()
        user = db.query(models.User).filter(models.User.username == student_code).first()
        assert user is not None, "Student was not committed to DB"
        grades = db.query(models.UserGrade).filter(models.UserGrade.user_id == user.id).all()
        assert len(grades) == 2, f"Expected 2 grades in DB, got {len(grades)}"


# ── GET /grades/preview enrichment (VIỆC 5) ──────────────────────────────────

class TestPreviewEnrichment:
    def test_preview_shows_account_created_true_for_new_student(self, client, admin_user, course_in_db):
        """Admin preview của SV chưa tồn tại → account_created = True."""
        new_sv = (
            "Ma sinh vien: sv_preview_new\n"
            "Ma mon,Ten mon hoc,So tin chi,Diem TK (10),Diem TK (4),Diem TK (C),Ket qua\n"
            "INT1234,Lap trinh can ban,3,8.5,3.5,B+,Dat\n"
        )
        resp = client.post(
            "/grades/preview",
            files=[("file", ("grades.csv", new_sv.encode("utf-8-sig"), "text/csv"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_created"] is True
        assert data["student_code"] == "sv_preview_new"

    def test_preview_shows_account_created_false_for_existing(self, client, admin_user, student_for_import, course_in_db):
        """Admin preview của SV đã có tài khoản → account_created = False."""
        resp = client.post(
            "/grades/preview",
            files=[("file", ("grades.csv", _GRADES_CSV.encode("utf-8-sig"), "text/csv"))],
            headers=_auth(admin_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_created"] is False

    def test_preview_account_created_none_for_student_role(self, client, registered_user, course_in_db):
        """Sinh viên thường gọi preview → account_created = None (không trả về)."""
        resp = client.post(
            "/grades/preview",
            files=[("file", ("grades.csv", _GRADES_CSV.encode("utf-8-sig"), "text/csv"))],
            headers=_auth(registered_user["token"]),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["account_created"] is None
