"""Verify academic thresholds GET/PUT endpoints (Lớp 3)."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def admin_token(client, db):
    admin = models.User(
        username='admintest', email='at@example.com',
        full_name='Admin Test', role='admin',
        password_hash=_hash_password('Test@1234'),
    )
    db.add(admin); db.commit()
    r = client.post('/auth/login', json={'username':'admintest','password':'Test@1234'})
    assert r.status_code == 200
    return r.json()['access_token']


def test_academic_thresholds_get_default(client, admin_token):
    """Khi chưa có giá trị trong DB, trả default + source='default'."""
    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/admin/config/academic-thresholds', headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d['internship_min_credits'] == 90.0
    assert d['thesis_min_credits'] == 130.0
    assert d['thesis_min_gpa4'] == 2.0
    assert d['source'] == 'default'


def test_academic_thresholds_put_then_get(client, admin_token):
    """Sau khi PUT, GET phải trả giá trị mới + source='db'."""
    H = {'Authorization': f'Bearer {admin_token}'}
    new_vals = {'internship_min_credits': 100.0, 'thesis_min_credits': 140.0, 'thesis_min_gpa4': 2.5}
    r = client.put('/admin/config/academic-thresholds', headers=H, json=new_vals)
    assert r.status_code == 200, r.json()
    assert r.json()['source'] == 'db'

    r = client.get('/admin/config/academic-thresholds', headers=H)
    d = r.json()
    assert d['internship_min_credits'] == 100.0
    assert d['thesis_min_credits'] == 140.0
    assert d['thesis_min_gpa4'] == 2.5
    assert d['source'] == 'db'


def test_academic_thresholds_validate(client, admin_token):
    """Validate: các ngưỡng phải nằm trong range hợp lý."""
    H = {'Authorization': f'Bearer {admin_token}'}
    # GPA quá cao
    r = client.put('/admin/config/academic-thresholds', headers=H,
                   json={'internship_min_credits': 90, 'thesis_min_credits': 130, 'thesis_min_gpa4': 5.0})
    assert r.status_code == 422
    # GPA âm
    r = client.put('/admin/config/academic-thresholds', headers=H,
                   json={'internship_min_credits': 90, 'thesis_min_credits': 130, 'thesis_min_gpa4': -0.1})
    assert r.status_code == 422
    # TC âm
    r = client.put('/admin/config/academic-thresholds', headers=H,
                   json={'internship_min_credits': -10, 'thesis_min_credits': 130, 'thesis_min_gpa4': 2.0})
    assert r.status_code == 422


def test_academic_thresholds_audit_log(client, admin_token, db):
    """PUT phải tạo audit log."""
    H = {'Authorization': f'Bearer {admin_token}'}
    client.put('/admin/config/academic-thresholds', headers=H,
               json={'internship_min_credits': 95.0, 'thesis_min_credits': 135.0, 'thesis_min_gpa4': 2.2})
    log = db.query(models.AdminLog).filter(
        models.AdminLog.action == 'SET_ACADEMIC_THRESHOLDS'
    ).order_by(models.AdminLog.id.desc()).first()
    assert log is not None
    assert '95.0' in log.detail or '95' in log.detail


def test_thresholds_affect_internship_eligibility(client, admin_token, db):
    """Sau khi đổi ngưỡng TC TT DN, why-not endpoint phản ánh đúng."""
    H_admin = {'Authorization': f'Bearer {admin_token}'}
    # Set ngưỡng TT cao bất thường (250 TC)
    client.put('/admin/config/academic-thresholds', headers=H_admin,
               json={'internship_min_credits': 250.0, 'thesis_min_credits': 130.0, 'thesis_min_gpa4': 2.0})

    # Tạo SV + ngưỡng cao → SV chắc chắn không đủ
    sv = models.User(
        username='sv_test_thresh', email='sv@x.com', full_name='SV Test',
        role='student', specialization='7480201_07',
        password_hash=_hash_password('Test@1234'),
    )
    db.add(sv); db.commit()
    # Tạo môn TT DN cho KHMT
    intern = models.Course(
        course_code='7080519', course_name='Thực tập tốt nghiệp',
        credits=10, count_toward_credits=True, required_specialization='7480201_07',
    )
    db.add(intern); db.commit()
    r = client.post('/auth/login', json={'username':'sv_test_thresh','password':'Test@1234'})
    sv_tok = r.json()['access_token']
    H_sv = {'Authorization': f'Bearer {sv_tok}'}

    r = client.get('/recommendations/why-not/7080519', headers=H_sv)
    # Phải gate vì TC tích lũy < 250
    assert r.status_code == 200
    assert r.json()['reason_code'] in ('NOT_ELIGIBLE_INTERNSHIP_TC', 'MISSING_PREREQ', 'NOT_ELIGIBLE_INTERNSHIP'), \
        f"Got: {r.json()}"
