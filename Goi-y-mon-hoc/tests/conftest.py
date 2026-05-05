"""
Test fixtures — SQLite in-memory với StaticPool để tránh file persistence.
Transaction isolation: mỗi test wrap trong outer transaction bị rollback ở cuối,
đảm bảo db.commit() bên trong route không làm ô nhiễm test kế tiếp.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from backend.db.models import Base
from backend.db.db import get_db
from backend.main import app

# ── In-memory SQLite — không còn file test_temp.db tồn tại giữa các run ────────
TEST_DB_URL = "sqlite:///:memory:"

engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,   # tất cả session dùng chung 1 connection vật lý
)

# ── SQLite compat: BigInteger → INTEGER để SQLite tự autoincrement ──────────────
from sqlalchemy.dialects.sqlite import dialect as _sqlite_dialect  # noqa: E402

def _visit_big_integer_as_integer(self, type_, **kw):
    return "INTEGER"

_sqlite_dialect.type_compiler_cls.visit_big_integer = _visit_big_integer_as_integer

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Tạo schema một lần cho toàn bộ test session."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _flush_ref_caches():
    """Reference-data caches in academic_engine (Course, ElectiveGroup, Prereq,
    CourseSkill) are module-level with a TTL. They must be invalidated between
    tests so test N doesn't see seed data from test N-1's transaction."""
    try:
        from backend.core import academic_engine as _ae
        _ae._invalidate_ref_cache()
        if hasattr(_ae, "_invalidate_academic_thresholds_cache"):
            _ae._invalidate_academic_thresholds_cache()
        # Also reset the difficulty stats cache
        _ae._difficulty_stats_cache = None
        _ae._difficulty_stats_ts = 0.0
    except Exception:
        pass
    yield


@pytest.fixture()
def db():
    """
    Mỗi test chạy trong một outer transaction bị rollback ở cuối.
    Savepoint được restart sau mỗi session.commit() của route
    để commit không thoát ra outer transaction.
    """
    connection = engine.connect()
    outer_trans = connection.begin()

    # Session gắn với connection này để rollback outer_trans bao phủ toàn bộ
    session = Session(bind=connection)  # noqa: deprecated but still works in 2.0.x
    nested = connection.begin_nested()  # savepoint — route commit chỉ commit đến đây

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session, transaction):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        outer_trans.rollback()   # hoàn tác mọi thứ đã commit trong test
        connection.close()


@pytest.fixture()
def client(db):
    app.dependency_overrides[get_db] = lambda: db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def registered_user(client):
    """Tạo user test và trả về token."""
    resp = client.post("/auth/register", json={
        "username": "test_sv",
        "password": "Test@1234",
        "full_name": "Sinh Viên Test",
        "specialization": "Kỹ thuật phần mềm",
        "career_goal": "web",
    })
    assert resp.status_code == 200
    resp2 = client.post("/auth/login", json={
        "username": "test_sv",
        "password": "Test@1234",
    })
    assert resp2.status_code == 200
    token = resp2.json()["access_token"]
    return {"token": token, "username": "test_sv"}


@pytest.fixture()
def auth_headers(registered_user):
    return {"Authorization": f"Bearer {registered_user['token']}"}
