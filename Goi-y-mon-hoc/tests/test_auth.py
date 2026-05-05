"""Tests cho luồng xác thực: đăng ký, đăng nhập, token, rate limiting."""
from __future__ import annotations


def test_register_success(client):
    resp = client.post("/auth/register", json={
        "username": "new_user",
        "password": "Pass@1234",
        "full_name": "Người Dùng Mới",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["username"] == "new_user"
    assert data["role"] == "student"


def test_register_duplicate_username(client):
    payload = {"username": "dup_user", "password": "Pass@1234", "full_name": "A"}
    client.post("/auth/register", json=payload)
    resp = client.post("/auth/register", json=payload)
    assert resp.status_code == 400


def test_login_success(client):
    client.post("/auth/register", json={
        "username": "login_user", "password": "Pass@1234", "full_name": "A"
    })
    resp = client.post("/auth/login", json={
        "username": "login_user", "password": "Pass@1234"
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


def test_login_wrong_password(client):
    client.post("/auth/register", json={
        "username": "wrong_pw_user", "password": "Pass@1234", "full_name": "A"
    })
    resp = client.post("/auth/login", json={
        "username": "wrong_pw_user", "password": "WrongPass"
    })
    assert resp.status_code == 401


def test_login_rate_limit(client):
    """Sau 5 lần sai liên tiếp phải bị chặn (429)."""
    client.post("/auth/register", json={
        "username": "rate_user", "password": "Pass@1234", "full_name": "A"
    })
    for _ in range(5):
        client.post("/auth/login", json={"username": "rate_user", "password": "wrong"})
    resp = client.post("/auth/login", json={"username": "rate_user", "password": "wrong"})
    assert resp.status_code == 429


def test_get_me(client, auth_headers):
    resp = client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["username"] == "test_sv"


def test_logout(client, registered_user):
    token = registered_user["token"]
    headers = {"Authorization": f"Bearer {token}"}
    resp = client.post("/auth/logout", headers=headers)
    assert resp.status_code == 200
    # Token đã bị xóa — me phải trả 401
    resp2 = client.get("/auth/me", headers=headers)
    assert resp2.status_code == 401


def test_invalid_token(client):
    resp = client.get("/auth/me", headers={"Authorization": "Bearer fake_token_xyz"})
    assert resp.status_code == 401
