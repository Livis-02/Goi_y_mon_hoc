"""Tests cho hệ thống thông báo v2 — target groups + mark-read + unread-count."""
from __future__ import annotations
import pytest
from backend.db import models


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture()
def admin_token(client, db):
    resp = client.post("/auth/register", json={
        "username": "adm_notif_test", "password": "Admin@1234", "full_name": "Admin Notif",
    })
    uid = resp.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={
        "username": "adm_notif_test", "password": "Admin@1234",
    }).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def sv_k22(client):
    client.post("/auth/register", json={
        "username": "2200001001", "password": "Pass@1234",
        "full_name": "SV K22 A", "specialization": "7480201_07",
    })
    token = client.post("/auth/login", json={
        "username": "2200001001", "password": "Pass@1234",
    }).json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "username": "2200001001"}


@pytest.fixture()
def sv_k23(client):
    client.post("/auth/register", json={
        "username": "2300001002", "password": "Pass@1234",
        "full_name": "SV K23 B", "specialization": "7480201_06",
    })
    token = client.post("/auth/login", json={
        "username": "2300001002", "password": "Pass@1234",
    }).json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}, "username": "2300001002"}


def _notif(client, headers, **kwargs):
    payload = {"title": "Test notif", "content": "x", "severity": "info",
               "target_type": "all", **kwargs}
    return client.post("/admin/notifications", headers=headers, json=payload)


# ── Tạo thông báo với từng target_type ────────────────────────────────────────

def test_create_notification_all(client, admin_token):
    resp = _notif(client, admin_token, title="TB toàn hệ thống", target_type="all")
    assert resp.status_code == 200
    d = resp.json()
    assert d["title"] == "TB toàn hệ thống"
    assert d["severity"] == "info"
    assert d["target_type"] == "all"


def test_create_notification_all_students(client, admin_token):
    resp = _notif(client, admin_token, target_type="all_students", severity="warning")
    assert resp.status_code == 200
    assert resp.json()["target_type"] == "all_students"
    assert resp.json()["severity"] == "warning"


def test_create_notification_all_advisors(client, admin_token):
    resp = _notif(client, admin_token, target_type="all_advisors")
    assert resp.status_code == 200
    assert resp.json()["target_type"] == "all_advisors"


def test_create_notification_cohort(client, admin_token):
    resp = _notif(client, admin_token, target_type="cohort", target_value="K22,K23")
    assert resp.status_code == 200
    assert resp.json()["target_value"] == "K22,K23"


def test_create_notification_specialization(client, admin_token):
    resp = _notif(client, admin_token, target_type="specialization",
                  target_value="7480201_07", severity="urgent")
    assert resp.status_code == 200
    assert resp.json()["severity"] == "urgent"


def test_create_notification_students_specific(client, admin_token, sv_k22):
    resp = _notif(client, admin_token, target_type="students",
                  target_value=sv_k22["username"])
    assert resp.status_code == 200


def test_create_notification_department(client, admin_token):
    resp = _notif(client, admin_token, target_type="department",
                  target_value="7480201_07")
    assert resp.status_code == 200


# ── Validate target_value ──────────────────────────────────────────────────────

def test_invalid_severity(client, admin_token):
    resp = _notif(client, admin_token, severity="critical")
    assert resp.status_code == 400


def test_invalid_target_type(client, admin_token):
    resp = _notif(client, admin_token, target_type="unknown_type")
    assert resp.status_code == 400


def test_title_too_short(client, admin_token):
    resp = _notif(client, admin_token, title="ab")
    assert resp.status_code == 400


def test_empty_content(client, admin_token):
    resp = _notif(client, admin_token, content="   ")
    assert resp.status_code == 400


def test_students_target_nonexistent_user(client, admin_token):
    resp = _notif(client, admin_token, target_type="students",
                  target_value="sv_does_not_exist_xyz")
    assert resp.status_code == 400


# ── Đúng đối tượng mới thấy ───────────────────────────────────────────────────

def test_all_visible_to_student(client, admin_token, sv_k22):
    _notif(client, admin_token, title="Toàn hệ thống V", target_type="all")
    resp = client.get("/notifications/me", headers=sv_k22["headers"])
    assert resp.status_code == 200
    assert any(n["title"] == "Toàn hệ thống V" for n in resp.json())


def test_all_students_visible_to_student(client, admin_token, sv_k22):
    _notif(client, admin_token, title="Chỉ SV V", target_type="all_students")
    resp = client.get("/notifications/me", headers=sv_k22["headers"])
    assert any(n["title"] == "Chỉ SV V" for n in resp.json())


def test_cohort_filter_correct(client, admin_token, sv_k22, sv_k23):
    _notif(client, admin_token, title="Chỉ K22 X", target_type="cohort",
           target_value="K22")
    r22 = client.get("/notifications/me", headers=sv_k22["headers"])
    r23 = client.get("/notifications/me", headers=sv_k23["headers"])
    assert any(n["title"] == "Chỉ K22 X" for n in r22.json())
    assert not any(n["title"] == "Chỉ K22 X" for n in r23.json())


def test_specialization_filter(client, admin_token, sv_k22, sv_k23):
    # sv_k22 has spec 7480201_07, sv_k23 has spec 7480201_06
    _notif(client, admin_token, title="Chỉ KHMT Z", target_type="specialization",
           target_value="7480201_07")
    r22 = client.get("/notifications/me", headers=sv_k22["headers"])
    r23 = client.get("/notifications/me", headers=sv_k23["headers"])
    assert any(n["title"] == "Chỉ KHMT Z" for n in r22.json())
    assert not any(n["title"] == "Chỉ KHMT Z" for n in r23.json())


# ── Mark as read ───────────────────────────────────────────────────────────────

def test_mark_as_read(client, admin_token, sv_k22):
    r = _notif(client, admin_token, title="Mark Read")
    nid = r.json()["id"]

    # Chưa đọc
    notifs = client.get("/notifications/me", headers=sv_k22["headers"]).json()
    target = next((n for n in notifs if n["id"] == nid), None)
    assert target is not None
    assert target["is_read"] is False

    # Mark read
    assert client.post(f"/notifications/{nid}/mark-read",
                       headers=sv_k22["headers"]).status_code == 200

    # Đã đọc
    notifs2 = client.get("/notifications/me", headers=sv_k22["headers"]).json()
    assert any(n["id"] == nid and n["is_read"] for n in notifs2)

    # Idempotent
    assert client.post(f"/notifications/{nid}/mark-read",
                       headers=sv_k22["headers"]).status_code == 200


# ── Unread count ───────────────────────────────────────────────────────────────

def test_unread_count(client, admin_token, sv_k22):
    r0 = client.get("/notifications/me/unread-count", headers=sv_k22["headers"])
    assert r0.status_code == 200
    before = r0.json()["count"]

    # Tạo 2 thông báo
    for i in range(2):
        _notif(client, admin_token, title=f"Unread {i} UC")

    r1 = client.get("/notifications/me/unread-count", headers=sv_k22["headers"])
    assert r1.json()["count"] == before + 2

    # Mark all read
    assert client.post("/notifications/mark-all-read",
                       headers=sv_k22["headers"]).status_code == 200
    r2 = client.get("/notifications/me/unread-count", headers=sv_k22["headers"])
    assert r2.json()["count"] == 0


# ── Delete notification ────────────────────────────────────────────────────────

def test_delete_notification(client, admin_token):
    nid = _notif(client, admin_token, title="To Delete").json()["id"]
    assert client.delete(f"/admin/notifications/{nid}",
                         headers=admin_token).status_code == 200
    lst = client.get("/admin/notifications", headers=admin_token).json()
    assert not any(n["id"] == nid for n in lst)


def test_delete_nonexistent(client, admin_token):
    assert client.delete("/admin/notifications/999999",
                         headers=admin_token).status_code == 404


# ── Estimate reach ─────────────────────────────────────────────────────────────

def test_estimate_reach_all(client, admin_token):
    resp = client.get("/admin/notifications/estimate-reach?target_type=all",
                      headers=admin_token)
    assert resp.status_code == 200
    assert resp.json()["count"] >= 0


def test_estimate_reach_cohort(client, admin_token, sv_k22):
    resp = client.get(
        "/admin/notifications/estimate-reach?target_type=cohort&target_value=K22",
        headers=admin_token,
    )
    assert resp.status_code == 200
    assert resp.json()["count"] >= 1


def test_estimate_reach_invalid(client, admin_token):
    resp = client.get("/admin/notifications/estimate-reach?target_type=bad",
                      headers=admin_token)
    assert resp.status_code == 400
