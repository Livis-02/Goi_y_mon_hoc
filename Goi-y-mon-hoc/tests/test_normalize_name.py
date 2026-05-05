"""
Tests for normalize_vietnamese_name() helper.
"""
import pytest
from backend.main import normalize_vietnamese_name


# ── Unit tests ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("inp, expected", [
    # Already correct
    ("Nguyễn Văn A",        "Nguyễn Văn A"),
    # All uppercase
    ("NGUYỄN VĂN A",        "Nguyễn Văn A"),
    # All lowercase
    ("nguyễn văn a",        "Nguyễn Văn A"),
    # Mixed case
    ("nGUyỄn vĂN a",        "Nguyễn Văn A"),
    # Extra whitespace between words
    ("Trần  Thị   Bình",    "Trần Thị Bình"),
    # Leading/trailing whitespace
    ("  Lê Thành Nam  ",    "Lê Thành Nam"),
    # Single word
    ("hoàng",               "Hoàng"),
    # Empty string
    ("",                    ""),
    # Whitespace only
    ("   ",                 ""),
    # Diacritics preserved
    ("đỗ thị ước mơ",       "Đỗ Thị Ước Mơ"),
    # Common Vietnamese names
    ("phạm thị lan anh",    "Phạm Thị Lan Anh"),
    ("VÕ HOÀNG ANH",        "Võ Hoàng Anh"),
    ("bùi thị XUÂN",        "Bùi Thị Xuân"),
    # Tabs / multiple space types normalised to single space
    ("Lê\t\tVăn",           "Lê Văn"),
])
def test_normalize_vietnamese_name(inp, expected):
    assert normalize_vietnamese_name(inp) == expected


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def _student(client):
    """Registered student user + token."""
    import random
    uname = f"sv_norm_{random.randint(10000, 99999)}"
    client.post("/auth/register", json={"username": uname, "password": "Test@1234", "full_name": "Test User"})
    token = client.post("/auth/login", json={"username": uname, "password": "Test@1234"}).json()["access_token"]
    return {"token": token, "username": uname}


@pytest.fixture()
def _admin(client, db):
    """Admin user + token."""
    import random
    from backend.db import models
    uname = f"adm_norm_{random.randint(10000, 99999)}"
    res = client.post("/auth/register", json={"username": uname, "password": "Admin@1234", "full_name": "Admin Norm"})
    uid = res.json()["id"]
    db.query(models.User).filter(models.User.id == uid).update({"role": "admin"})
    db.commit()
    token = client.post("/auth/login", json={"username": uname, "password": "Admin@1234"}).json()["access_token"]
    return {"token": token}


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


# ── Integration: name normalised when saving via API ─────────────────────────

def test_update_full_name_normalised(client, _student):
    """PATCH /auth/me/full-name stores title-cased name."""
    res = client.patch(
        "/auth/me/full-name",
        json={"full_name": "TRẦN VĂN BÌNH"},
        headers=_auth(_student["token"]),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Trần Văn Bình"


def test_update_full_name_trims_whitespace(client, _student):
    res = client.patch(
        "/auth/me/full-name",
        json={"full_name": "  nguyễn  thị  hoa  "},
        headers=_auth(_student["token"]),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Nguyễn Thị Hoa"


def test_admin_create_user_normalised_name(client, _admin):
    """Admin tạo SV — họ tên được title-case."""
    import random
    code = str(random.randint(2100000100, 2199999999))
    res = client.post(
        "/admin/users",
        json={"username": code, "full_name": "PHẠM THỊ LAN ANH"},
        headers=_auth(_admin["token"]),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Phạm Thị Lan Anh"


def test_admin_create_advisor_normalised_name(client, _admin):
    """Admin tạo cố vấn — họ tên được title-case."""
    import random
    tc = f"GV{random.randint(500, 599):03d}"
    res = client.post(
        "/admin/advisors",
        json={"teacher_code": tc, "full_name": "lê VĂN cường"},
        headers=_auth(_admin["token"]),
    )
    assert res.status_code == 200
    assert res.json()["full_name"] == "Lê Văn Cường"
