"""Tests cho GET /admin/dashboard và GET+PUT /admin/config/graduation-threshold."""
from __future__ import annotations
import pytest
from backend.db import models


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_user(client, db):
    resp = client.post("/auth/register", json={
        "username": "admin_dash", "password": "Admin@123", "full_name": "Admin Dash",
    })
    assert resp.status_code == 200
    uid = resp.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={
        "username": "admin_dash", "password": "Admin@123",
    }).json()["access_token"]
    return {"token": token, "id": uid}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── GET /admin/dashboard ───────────────────────────────────────────────────────

class TestAdminDashboard:
    def test_dashboard_returns_expected_fields(self, client, admin_user):
        resp = client.get("/admin/dashboard", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert "total_students" in data
        assert "total_advisors" in data
        assert "total_courses" in data
        assert "at_risk_students" in data
        assert "active_users_this_week" in data
        assert "graduation_threshold" in data

    def test_dashboard_counts_students(self, client, admin_user, db):
        # Tạo 2 SV
        for i in range(2):
            db.add(models.User(username=f"sv_dash_{i}", password_hash="x", role="student"))
        db.commit()

        resp = client.get("/admin/dashboard", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_students"] >= 2

    def test_dashboard_counts_advisors(self, client, admin_user, db):
        db.add(models.User(username="adv_dash_1", password_hash="x", role="advisor"))
        db.commit()

        resp = client.get("/admin/dashboard", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        assert resp.json()["total_advisors"] >= 1

    def test_dashboard_graduation_threshold_default(self, client, admin_user):
        resp = client.get("/admin/dashboard", headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        # Default = 153.0 hoặc giá trị đã được set trong DB test
        assert resp.json()["graduation_threshold"] > 0

    def test_dashboard_non_admin_rejected(self, client, registered_user):
        resp = client.get("/admin/dashboard", headers=_auth(registered_user["token"]))
        assert resp.status_code == 403

    def test_dashboard_unauthenticated_rejected(self, client):
        resp = client.get("/admin/dashboard")
        assert resp.status_code == 401


# ── GET /admin/config/graduation-threshold ────────────────────────────────────

class TestGraduationThreshold:
    def test_get_default_threshold(self, client, admin_user):
        resp = client.get("/admin/config/graduation-threshold",
                          headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["threshold"] == 153.0
        assert data["source"] == "default"

    def test_set_threshold(self, client, admin_user):
        resp = client.put("/admin/config/graduation-threshold",
                          json={"threshold": 140.0},
                          headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["threshold"] == 140.0
        assert data["source"] == "db"

    def test_get_after_set(self, client, admin_user):
        client.put("/admin/config/graduation-threshold",
                   json={"threshold": 128.0},
                   headers=_auth(admin_user["token"]))
        resp = client.get("/admin/config/graduation-threshold",
                          headers=_auth(admin_user["token"]))
        assert resp.status_code == 200
        data = resp.json()
        assert data["threshold"] == 128.0
        assert data["source"] == "db"

    def test_overwrite_threshold(self, client, admin_user):
        client.put("/admin/config/graduation-threshold",
                   json={"threshold": 140.0},
                   headers=_auth(admin_user["token"]))
        client.put("/admin/config/graduation-threshold",
                   json={"threshold": 160.0},
                   headers=_auth(admin_user["token"]))
        resp = client.get("/admin/config/graduation-threshold",
                          headers=_auth(admin_user["token"]))
        assert resp.json()["threshold"] == 160.0

    def test_invalid_threshold_rejected(self, client, admin_user):
        # Quá thấp
        r1 = client.put("/admin/config/graduation-threshold",
                        json={"threshold": 10.0},
                        headers=_auth(admin_user["token"]))
        assert r1.status_code == 422
        # Quá cao
        r2 = client.put("/admin/config/graduation-threshold",
                        json={"threshold": 999.0},
                        headers=_auth(admin_user["token"]))
        assert r2.status_code == 422

    def test_non_admin_cannot_set_threshold(self, client, registered_user):
        resp = client.put("/admin/config/graduation-threshold",
                          json={"threshold": 100.0},
                          headers=_auth(registered_user["token"]))
        assert resp.status_code == 403

    def test_non_admin_cannot_get_threshold(self, client, registered_user):
        resp = client.get("/admin/config/graduation-threshold",
                          headers=_auth(registered_user["token"]))
        assert resp.status_code == 403
