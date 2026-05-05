"""Tests for teacher_code + bulk assignment import."""
from __future__ import annotations
import io
import pytest
from backend.db import models


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin(client, db):
    import random
    uname = f"adm_tc_{random.randint(10000,99999)}"
    res = client.post("/auth/register", json={"username": uname, "password": "Admin@1234", "full_name": "Admin TC"})
    uid = res.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={"username": uname, "password": "Admin@1234"}).json()["access_token"]
    return {"token": token, "id": uid}


def _auth(token): return {"Authorization": f"Bearer {token}"}


def _create_advisor(client, admin, tc, full_name="Test Advisor", spec=None, is_head=False):
    return client.post("/admin/advisors", json={
        "teacher_code": tc, "full_name": full_name,
        "managed_specialization": spec, "is_head_of_department": is_head,
    }, headers={**_auth(admin["token"]), "Content-Type": "application/json"})


def _create_student(client, admin, username, full_name="Test Student"):
    return client.post("/admin/users", json={"username": username, "full_name": full_name},
                       headers={**_auth(admin["token"]), "Content-Type": "application/json"})


def _csv_file(content: str, filename: str = "assign.csv"):
    return ("file", (filename, io.BytesIO(content.encode("utf-8-sig")), "text/csv"))


# ── VIỆC A: teacher_code CRUD (format mới) ────────────────────────────────────

class TestTeacherCode:
    def test_create_advisor_valid_gv_code(self, client, admin):
        res = _create_advisor(client, admin, "GV001")
        assert res.status_code == 200
        data = res.json()
        assert data["teacher_code"] == "GV001"
        assert data["username"] == "GV001"

    def test_create_advisor_valid_khmt_code(self, client, admin):
        res = _create_advisor(client, admin, "KHMT001", spec="7480201_07")
        assert res.status_code == 200
        assert res.json()["teacher_code"] == "KHMT001"

    def test_create_advisor_lowercase_normalised(self, client, admin):
        """khmt002 sent lowercase → should be uppercased by backend."""
        res = _create_advisor(client, admin, "khmt002", "Lowercase Test", spec="7480201_07")
        assert res.status_code == 200
        assert res.json()["teacher_code"] == "KHMT002"

    def test_create_advisor_invalid_format_old_style(self, client, admin):
        """Old GV0001 format (4 digits) → 422."""
        res = _create_advisor(client, admin, "GV0001")
        assert res.status_code == 422

    def test_create_advisor_invalid_prefix(self, client, admin):
        """TC prefix không hợp lệ → 422."""
        res = _create_advisor(client, admin, "TC001")
        assert res.status_code == 422

    def test_create_advisor_invalid_too_few_digits(self, client, admin):
        """GV01 — chỉ 2 số → 422."""
        res = _create_advisor(client, admin, "GV01")
        assert res.status_code == 422

    def test_create_advisor_duplicate_code(self, client, admin):
        _create_advisor(client, admin, "GV010")
        res = _create_advisor(client, admin, "GV010", "Other")
        assert res.status_code == 400
        assert "đã tồn tại" in res.json()["detail"]

    def test_create_advisor_all_prefixes_valid(self, client, admin):
        """Tất cả prefix hợp lệ đều pass."""
        for prefix in ("KHMT", "MMT", "CNPM", "HTTT", "THKT", "CNTTDH", "GV"):
            res = _create_advisor(client, admin, f"{prefix}099", f"Adv {prefix}")
            assert res.status_code == 200, f"Prefix {prefix} failed: {res.json()}"

    def test_list_advisors_includes_teacher_code(self, client, admin):
        _create_advisor(client, admin, "MMT020")
        res = client.get("/admin/advisors", headers=_auth(admin["token"]))
        assert res.status_code == 200
        codes = [a["teacher_code"] for a in res.json()]
        assert "MMT020" in codes

    def test_me_advisor_includes_teacher_code(self, client, admin, db):
        _create_advisor(client, admin, "CNPM030")
        res = client.get("/admin/advisors", headers=_auth(admin["token"]))
        adv = next((a for a in res.json() if a["teacher_code"] == "CNPM030"), None)
        assert adv is not None


# ── VIỆC B: bulk import assignments ──────────────────────────────────────────

class TestBulkImportAssignments:

    def test_import_with_existing_advisor(self, client, admin):
        _create_advisor(client, admin, "GV040", "Advisor Forty")
        _create_student(client, admin, "sv_bulk01")
        _create_student(client, admin, "sv_bulk02")

        csv = "Mã SV,Mã GV\nsv_bulk01,GV040\nsv_bulk02,GV040\n"
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv)],
                          data={"dry_run": "false", "auto_create": "false", "new_teachers_json": "[]"},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["created"] == 2
        assert data["updated"] == 0
        assert data["missing_teachers"] == []

    def test_import_missing_advisor_no_auto_create(self, client, admin):
        _create_student(client, admin, "sv_miss01")
        csv = "Mã SV,Mã GV\nsv_miss01,GV999\n"
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv)],
                          data={"dry_run": "false", "auto_create": "false", "new_teachers_json": "[]"},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["created"] == 0
        assert len(data["missing_teachers"]) == 1
        assert data["missing_teachers"][0]["teacher_code"] == "GV999"
        assert "sv_miss01" in data["missing_teachers"][0]["affected_students"]

    def test_import_missing_advisor_with_auto_create(self, client, admin):
        _create_student(client, admin, "sv_auto01")
        csv = "Mã SV,Mã GV\nsv_auto01,GV050\n"
        new_teachers = [{"teacher_code": "GV050", "full_name": "New Advisor", "managed_specialization": None, "is_head_of_department": False}]
        import json
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv)],
                          data={"dry_run": "false", "auto_create": "true",
                                "new_teachers_json": json.dumps(new_teachers)},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["created"] == 1
        assert len(data["created_teachers"]) == 1
        assert data["created_teachers"][0]["teacher_code"] == "GV050"
        assert len(data["created_teachers"][0]["password_plain"]) == 6

    def test_import_nonexistent_student_skipped(self, client, admin):
        _create_advisor(client, admin, "GV060", "Advisor Sixty")
        csv = "Mã SV,Mã GV\nNOTEXIST,GV060\n"
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv)],
                          data={"dry_run": "false", "auto_create": "false", "new_teachers_json": "[]"},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["created"] == 0
        assert len(data["errors"]) == 1
        assert "chưa tồn tại" in data["errors"][0]["reason"]

    def test_dry_run_does_not_commit(self, client, admin, db):
        _create_advisor(client, admin, "GV070", "Advisor Dry")
        _create_student(client, admin, "sv_dry01")
        csv = "Mã SV,Mã GV\nsv_dry01,GV070\n"
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv)],
                          data={"dry_run": "true", "auto_create": "false", "new_teachers_json": "[]"},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["dry_run"] is True
        assert data["created"] == 1  # preview shows 1 would be created
        # Verify nothing was actually written
        sv = db.query(models.User).filter(models.User.username == "sv_dry01").first()
        count = db.query(models.AdvisorAssignment).filter(
            models.AdvisorAssignment.student_id == sv.id
        ).count()
        assert count == 0

    def test_import_updates_existing_assignment(self, client, admin):
        _create_advisor(client, admin, "GV080", "Advisor Old")
        _create_advisor(client, admin, "GV081", "Advisor New")
        _create_student(client, admin, "sv_upd01")
        # First import → assign to GV080
        csv1 = "Mã SV,Mã GV\nsv_upd01,GV080\n"
        client.post("/admin/assignments/bulk-import",
                    files=[_csv_file(csv1)],
                    data={"dry_run": "false", "auto_create": "false", "new_teachers_json": "[]"},
                    headers=_auth(admin["token"]))
        # Second import → reassign to GV081
        csv2 = "Mã SV,Mã GV\nsv_upd01,GV081\n"
        res = client.post("/admin/assignments/bulk-import",
                          files=[_csv_file(csv2)],
                          data={"dry_run": "false", "auto_create": "false", "new_teachers_json": "[]"},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["updated"] == 1
        assert data["created"] == 0


# ── VIỆC C: trưởng bộ môn bắt buộc ──────────────────────────────────────────

class TestHeadProtection:

    def test_can_uncheck_head(self, client, admin):
        """PATCH is_head_of_department=False được phép (admin tự quản lý)."""
        _create_advisor(client, admin, "KHMT100", "Head Advisor", spec="7480201_07")
        adv = next(a for a in client.get("/admin/advisors", headers=_auth(admin["token"])).json() if a["teacher_code"] == "KHMT100")
        res = client.patch(f"/admin/advisors/{adv['id']}",
                           json={"is_head_of_department": False},
                           headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["is_head_of_department"] is False

    def test_can_change_spec_of_head(self, client, admin):
        """Đổi bộ môn của trưởng bộ môn được phép."""
        _create_advisor(client, admin, "KHMT101", "Head Spec", spec="7480201_07")
        adv = next(a for a in client.get("/admin/advisors", headers=_auth(admin["token"])).json() if a["teacher_code"] == "KHMT101")
        res = client.patch(f"/admin/advisors/{adv['id']}",
                           json={"managed_specialization": "7480201_05"},
                           headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["managed_specialization"] == "7480201_05"

    def test_can_delete_sole_head(self, client, admin):
        """Xóa trưởng bộ môn duy nhất → OK (không ai khác trong bộ môn)."""
        _create_advisor(client, admin, "MMT102", "Head Delete", spec="7480201_06")
        adv = next(a for a in client.get("/admin/advisors", headers=_auth(admin["token"])).json() if a["teacher_code"] == "MMT102")
        res = client.delete(f"/admin/advisors/{adv['id']}", headers=_auth(admin["token"]))
        assert res.status_code == 200

    def test_cannot_delete_head_with_other_advisors(self, client, admin):
        """Xóa trưởng bộ môn khi còn advisor khác cùng bộ môn → 400."""
        _create_advisor(client, admin, "MMT103", "Head Keep", spec="7480201_06")
        _create_advisor(client, admin, "MMT104", "Member", spec="7480201_06")
        all_advs = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        head = next(a for a in all_advs if a["teacher_code"] == "MMT103")
        res = client.delete(f"/admin/advisors/{head['id']}", headers=_auth(admin["token"]))
        assert res.status_code == 400
        assert "Không thể xóa" in res.json()["detail"]

    def test_can_update_fullname_of_head(self, client, admin):
        """Sửa tên của trưởng bộ môn vẫn OK."""
        _create_advisor(client, admin, "HTTT103", "Head Name Old", spec="7480201_09", is_head=True)
        adv = next(a for a in client.get("/admin/advisors", headers=_auth(admin["token"])).json() if a["teacher_code"] == "HTTT103")
        res = client.patch(f"/admin/advisors/{adv['id']}",
                           json={"full_name": "Head Name New"},
                           headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["full_name"] == "Head Name New"

    def test_transfer_head_ok(self, client, admin):
        """Chuyển chức trưởng bộ môn thành công."""
        _create_advisor(client, admin, "THKT110", "Head Transfer", spec="7480201_04", is_head=True)
        _create_advisor(client, admin, "THKT111", "New Head", spec="7480201_04", is_head=False)
        all_advs = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        old_id = next(a["id"] for a in all_advs if a["teacher_code"] == "THKT110")
        new_id = next(a["id"] for a in all_advs if a["teacher_code"] == "THKT111")
        res = client.post(f"/admin/advisors/{old_id}/transfer-head",
                          json={"new_head_advisor_id": new_id},
                          headers=_auth(admin["token"]))
        assert res.status_code == 200
        updated = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        old_adv = next(a for a in updated if a["id"] == old_id)
        new_adv = next(a for a in updated if a["id"] == new_id)
        assert old_adv["is_head_of_department"] is False
        assert new_adv["is_head_of_department"] is True

    def test_transfer_head_different_spec_fails(self, client, admin):
        """Chuyển chức sang advisor khác bộ môn → 400."""
        _create_advisor(client, admin, "KHMT120", "Head Spec A", spec="7480201_07", is_head=True)
        _create_advisor(client, admin, "CNTTDH121", "Other Spec B", spec="7480201_08", is_head=False)
        all_advs = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        head_id = next(a["id"] for a in all_advs if a["teacher_code"] == "KHMT120")
        other_id = next(a["id"] for a in all_advs if a["teacher_code"] == "CNTTDH121")
        res = client.post(f"/admin/advisors/{head_id}/transfer-head",
                          json={"new_head_advisor_id": other_id},
                          headers=_auth(admin["token"]))
        assert res.status_code == 400
        assert "cùng bộ môn" in res.json()["detail"]

    def test_transfer_head_non_head_fails(self, client, admin):
        """Transfer từ advisor không phải trưởng → 400."""
        _create_advisor(client, admin, "CNPM130", "Auto Head", spec="7480201_05")   # first → auto-head
        _create_advisor(client, admin, "CNPM131", "Non Head", spec="7480201_05")    # second → not head
        all_advs = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        head_id = next(a["id"] for a in all_advs if a["teacher_code"] == "CNPM130")
        non_head_id = next(a["id"] for a in all_advs if a["teacher_code"] == "CNPM131")
        res = client.post(f"/admin/advisors/{non_head_id}/transfer-head",
                          json={"new_head_advisor_id": head_id},
                          headers=_auth(admin["token"]))
        assert res.status_code == 400
        assert "không phải trưởng" in res.json()["detail"]

    def test_after_transfer_old_head_can_be_deleted(self, client, admin):
        """Sau khi chuyển chức, cố vấn cũ không còn là trưởng → có thể xóa."""
        _create_advisor(client, admin, "CNTTDH140", "Head To Delete", spec="7480201_08", is_head=True)
        _create_advisor(client, admin, "CNTTDH141", "Takes Over", spec="7480201_08", is_head=False)
        all_advs = client.get("/admin/advisors", headers=_auth(admin["token"])).json()
        old_id = next(a["id"] for a in all_advs if a["teacher_code"] == "CNTTDH140")
        new_id = next(a["id"] for a in all_advs if a["teacher_code"] == "CNTTDH141")
        client.post(f"/admin/advisors/{old_id}/transfer-head",
                    json={"new_head_advisor_id": new_id},
                    headers=_auth(admin["token"]))
        res = client.delete(f"/admin/advisors/{old_id}", headers=_auth(admin["token"]))
        assert res.status_code == 200


# ── VIỆC D: auto-suggest mã SV ───────────────────────────────────────────────

class TestNextStudentCode:

    def test_next_code_first_in_cohort(self, client, admin):
        """Khóa chưa có SV → trả về {cohort}00000001."""
        res = client.get("/admin/students/next-code?cohort=99", headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["next_code"] == "9900000001"
        assert res.json()["cohort"] == "99"

    def test_next_code_increments(self, client, admin):
        """Đã có SV → trả về max + 1."""
        _create_student(client, admin, "2800000001")
        _create_student(client, admin, "2800000002")
        res = client.get("/admin/students/next-code?cohort=28", headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["next_code"] == "2800000003"

    def test_next_code_invalid_cohort(self, client, admin):
        """cohort không phải 2 chữ số → 422."""
        res = client.get("/admin/students/next-code?cohort=abc", headers=_auth(admin["token"]))
        assert res.status_code == 422

    def test_next_code_requires_auth(self, client):
        res = client.get("/admin/students/next-code?cohort=25")
        assert res.status_code == 401


# ── VIỆC E: auto-suggest mã GV theo bộ môn ───────────────────────────────────

class TestNextAdvisorCode:

    def test_next_code_no_advisors_gv(self, client, admin):
        """Bộ môn null → prefix GV, chưa có advisor → GV001."""
        res = client.get("/admin/advisors/next-code", headers=_auth(admin["token"]))
        assert res.status_code == 200
        data = res.json()
        assert data["prefix"] == "GV"
        code = data["next_code"]
        assert code.startswith("GV")
        assert len(code) == 5  # GV + 3 digits

    def test_next_code_khmt(self, client, admin):
        """Bộ môn KHMT (7480201_07) → prefix KHMT."""
        res = client.get("/admin/advisors/next-code?specialization=7480201_07", headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["prefix"] == "KHMT"
        assert res.json()["next_code"].startswith("KHMT")

    def test_next_code_increments_after_create(self, client, admin):
        """Tạo KHMT001 → next-code trả về KHMT002."""
        _create_advisor(client, admin, "KHMT001", spec="7480201_07")
        res = client.get("/admin/advisors/next-code?specialization=7480201_07", headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["next_code"] == "KHMT002"

    def test_next_code_mmt(self, client, admin):
        _create_advisor(client, admin, "MMT001", spec="7480201_06")
        _create_advisor(client, admin, "MMT002", spec="7480201_06")
        res = client.get("/admin/advisors/next-code?specialization=7480201_06", headers=_auth(admin["token"]))
        assert res.status_code == 200
        assert res.json()["next_code"] == "MMT003"

    def test_next_code_requires_auth(self, client):
        res = client.get("/admin/advisors/next-code")
        assert res.status_code == 401


# ── VIỆC F: xem/reset mật khẩu advisor ──────────────────────────────────────

class TestAdvisorPassword:

    def test_default_password_visible_after_create(self, client, admin):
        """Advisor mới tạo → has_default=True, password là 6 chữ số."""
        res = _create_advisor(client, admin, "GV200", "Pw Advisor")
        assert res.status_code == 200
        adv_id = res.json()["id"]
        r = client.get(f"/admin/advisors/{adv_id}/default-password", headers=_auth(admin["token"]))
        assert r.status_code == 200
        data = r.json()
        assert data["has_default"] is True
        assert data["password"] is not None
        assert len(data["password"]) == 6

    def test_reset_password_generates_new(self, client, admin, db):
        """POST reset-password → trả về mật khẩu 6 số mới."""
        res = _create_advisor(client, admin, "GV201", "Reset Advisor")
        adv_id = res.json()["id"]
        r = client.post(f"/admin/advisors/{adv_id}/reset-password", headers=_auth(admin["token"]))
        assert r.status_code == 200
        new_pw = r.json()["password"]
        assert len(new_pw) == 6
        # Verify default-password endpoint returns the new pw
        r2 = client.get(f"/admin/advisors/{adv_id}/default-password", headers=_auth(admin["token"]))
        assert r2.status_code == 200
        assert r2.json()["has_default"] is True
        assert r2.json()["password"] == new_pw

    def test_reset_password_on_student_user_fails(self, client, admin):
        """POST /admin/advisors/{student_id}/reset-password → 404 (không phải advisor)."""
        sv = _create_student(client, admin, "sv_pw_test")
        sv_id = sv.json()["id"]
        r = client.post(f"/admin/advisors/{sv_id}/reset-password", headers=_auth(admin["token"]))
        assert r.status_code == 404

    def test_default_password_on_nonexistent_advisor(self, client, admin):
        r = client.get("/admin/advisors/999999/default-password", headers=_auth(admin["token"]))
        assert r.status_code == 404
