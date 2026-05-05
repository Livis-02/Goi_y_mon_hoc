"""Tests cho luồng quản lý mật khẩu — VIỆC 1-6."""
from __future__ import annotations
import pytest
from backend.db import models


# ── Fixtures ────────────────────────────────────���──────────────────────────────

@pytest.fixture()
def admin_token(client, db):
    resp = client.post("/auth/register", json={
        "username": "adm_pw_test", "password": "Admin@1234", "full_name": "Admin PW",
    })
    uid = resp.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={
        "username": "adm_pw_test", "password": "Admin@1234",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def student(client, db):
    """Tạo SV với mật khẩu mặc định (trạng thái vừa tạo/reset)."""
    resp = client.post("/auth/register", json={
        "username": "2200099001", "password": "Init@1234", "full_name": "SV Test PW",
    })
    uid = resp.json()["id"]
    # Simulate: admin vừa reset → default_password được ghi vào DB
    db.query(models.User).filter(models.User.id == uid).update({"default_password": "123456"})
    db.commit()
    token = client.post("/auth/login", json={
        "username": "2200099001", "password": "Init@1234",
    }).json()["access_token"]
    return {"id": uid, "username": "2200099001", "token": token}


# ── VIỆC 3: change-password clears default_password ───────────────────────────

def test_change_password_clears_default(client, db, student):
    """Sau khi user đổi MK, default_password = NULL."""
    tok = {"Authorization": f"Bearer {student['token']}"}
    r = client.post("/auth/me/change-password", headers=tok, json={
        "current_password": "Init@1234",
        "new_password": "NewPass@123",
    })
    assert r.status_code == 200

    db.expire_all()
    u = db.query(models.User).filter(models.User.id == student["id"]).first()
    assert u.default_password is None
    assert u.is_first_login is False


# ── Admin reset → default_password set ────────────────────────────────────────

def test_admin_reset_sets_default_password(client, db, admin_token, student):
    r = client.post(f"/admin/users/{student['id']}/reset-password", headers=admin_token)
    assert r.status_code == 200
    pw = r.json()["password"]
    assert pw  # non-empty 6-digit string

    db.expire_all()
    u = db.query(models.User).filter(models.User.id == student["id"]).first()
    assert u.default_password == pw
    assert u.is_first_login is True


# ── VIỆC 2: GET /admin/passwords-pending ─────────────────────────────────��────

def test_passwords_pending_includes_user_with_default(client, admin_token, student):
    """Users với default_password != NULL xuất hiện trong danh sách."""
    r = client.get("/admin/passwords-pending", headers=admin_token)
    assert r.status_code == 200
    ids = [u["id"] for u in r.json()]
    assert student["id"] in ids


def test_passwords_pending_excludes_changed_user(client, db, admin_token, student):
    """Sau khi user đổi MK, không còn trong danh sách pending."""
    tok = {"Authorization": f"Bearer {student['token']}"}
    client.post("/auth/me/change-password", headers=tok, json={
        "current_password": "Init@1234",
        "new_password": "Changed@999",
    })
    r = client.get("/admin/passwords-pending", headers=admin_token)
    assert r.status_code == 200
    ids = [u["id"] for u in r.json()]
    assert student["id"] not in ids


def test_passwords_pending_requires_admin(client, student):
    tok = {"Authorization": f"Bearer {student['token']}"}
    r = client.get("/admin/passwords-pending", headers=tok)
    assert r.status_code == 403


# ── VIỆC 2: POST /admin/users/{id}/view-password ──────────────────────────────

def test_view_password_returns_default(client, admin_token, student):
    r = client.post(f"/admin/users/{student['id']}/view-password", headers=admin_token)
    assert r.status_code == 200
    assert r.json()["password"] == "123456"


def test_view_password_logs_action(client, db, admin_token, student):
    client.post(f"/admin/users/{student['id']}/view-password", headers=admin_token)
    log = db.query(models.AdminLog).filter(
        models.AdminLog.action == "VIEW_PASSWORD",
        models.AdminLog.target_id == "2200099001",
    ).first()
    assert log is not None


def test_view_password_after_change_returns_404(client, db, admin_token, student):
    """Sau khi user đổi MK, admin không còn xem được nữa."""
    tok = {"Authorization": f"Bearer {student['token']}"}
    client.post("/auth/me/change-password", headers=tok, json={
        "current_password": "Init@1234",
        "new_password": "Changed@999",
    })
    r = client.post(f"/admin/users/{student['id']}/view-password", headers=admin_token)
    assert r.status_code == 404


# ── Admin reset → response có password field ─────────────────────────────────

def test_reset_response_has_password(client, admin_token, student):
    r = client.post(f"/admin/users/{student['id']}/reset-password", headers=admin_token)
    assert r.status_code == 200
    d = r.json()
    assert "password" in d
    assert len(d["password"]) == 6
    assert d["password"].isdigit()


# ── setup-account also clears default_password ──────────────────────────���─────

def test_setup_account_clears_default(client, db, student):
    """PATCH /auth/me/setup-account cũng xóa default_password."""
    tok = {"Authorization": f"Bearer {student['token']}"}
    # Mark first login
    db.query(models.User).filter(models.User.id == student["id"]).update({"is_first_login": True})
    db.commit()
    r = client.patch("/auth/me/setup-account", headers=tok, json={
        "email": "svtest@example.com",
        "new_password": "Setup@999",
        "confirm_password": "Setup@999",
    })
    assert r.status_code == 200

    db.expire_all()
    u = db.query(models.User).filter(models.User.id == student["id"]).first()
    assert u.default_password is None
    assert u.is_first_login is False
