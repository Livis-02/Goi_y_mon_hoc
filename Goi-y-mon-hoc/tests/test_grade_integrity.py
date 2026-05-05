"""Verify SV không thể upload bảng điểm (Option A — disable hoàn toàn)."""
import io
import pytest
from backend.db import models
from backend.main import _hash_password


def _xlsx_bytes(rows):
    """Tạo file xlsx tối giản với mã SV + 1 môn."""
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    for r in rows:
        ws.append(r)
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def test_sv_cannot_upload_grades_at_all(client, db):
    """SV gọi /grades/upload luôn bị reject 403 — không có cách nào tự upload."""
    sv = models.User(
        username='2400000001', email='sv@x.c', full_name='SV Test',
        role='student', password_hash=_hash_password('Test@1234'),
    )
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'2400000001','password':'Test@1234'})
    H = {'Authorization': f'Bearer {r.json()["access_token"]}'}
    fake = _xlsx_bytes([['Mã sinh viên: 2400000001'], ['Tên'], ['x']])
    r2 = client.post('/grades/upload', headers=H,
                     files={'file': ('x.xlsx', fake, 'application/octet-stream')})
    assert r2.status_code == 403
    assert 'sinh viên' in r2.json()['detail'].lower() or 'không được' in r2.json()['detail'].lower()


def test_sv_cannot_upload_even_when_no_admin_grades(client, db):
    """Kể cả khi chưa có admin import → SV vẫn bị reject (Option A)."""
    sv = models.User(
        username='2400000002', email='sv2@x.c', full_name='SV2',
        role='student', password_hash=_hash_password('Test@1234'),
    )
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'2400000002','password':'Test@1234'})
    H = {'Authorization': f'Bearer {r.json()["access_token"]}'}
    fake = _xlsx_bytes([['x'], ['y']])
    r2 = client.post('/grades/upload', headers=H,
                     files={'file': ('x.xlsx', fake, 'application/octet-stream')})
    assert r2.status_code == 403


def test_grade_default_source_is_self(db):
    """Một grade insert mà không chỉ định source → mặc định 'self' (legacy compat)."""
    sv = models.User(
        username='2400000003_x', email='sv3@x.c', full_name='SV3',
        role='student', password_hash=_hash_password('x'),
    )
    db.add(sv)
    db.add(models.Course(course_code='7080208', course_name='CSLT', credits=3, count_toward_credits=True))
    db.flush()
    db.add(models.UserGrade(
        user_id=sv.id, course_code='7080208', term='HK1/2024',
        score10=8, score4=3, letter='B', passed=True,
    ))
    db.commit()
    g = db.query(models.UserGrade).filter(models.UserGrade.user_id == sv.id).first()
    assert g is not None
    assert g.source in ('self', None, 'admin')


def test_admin_upload_endpoint_returns_410_for_admin(client, db):
    """Admin gọi /grades/upload bị 410 (deprecated) — phải dùng /admin/grades/import."""
    admin = models.User(
        username='admin_test', email='a@x.c', full_name='Admin',
        role='admin', password_hash=_hash_password('Test@1234'),
    )
    db.add(admin); db.commit()
    r = client.post('/auth/login', json={'username':'admin_test','password':'Test@1234'})
    H = {'Authorization': f'Bearer {r.json()["access_token"]}'}
    fake = _xlsx_bytes([['x']])
    r2 = client.post('/grades/upload', headers=H,
                     files={'file': ('x.xlsx', fake, 'application/octet-stream')})
    assert r2.status_code == 410
    assert '/admin/grades/import' in r2.json()['detail']
