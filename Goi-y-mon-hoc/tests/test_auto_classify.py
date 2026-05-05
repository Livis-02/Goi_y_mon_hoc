"""Verify auto-classify SV không gán bừa CN."""
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
    return r.json()['access_token']


def _make_sv(db, code='2100000001', spec=None):
    sv = models.User(
        username=code, email=f'{code}@x.com',
        full_name='Sinh Viên', role='student',
        specialization=spec, password_hash=_hash_password('x'),
    )
    db.add(sv); db.commit()
    return sv


def _add_grade(db, user_id, code):
    db.add(models.UserGrade(
        user_id=user_id, course_code=code,
        term='HK1/2024', score10=8.0, score4=3.0, letter='B', passed=True,
    ))
    db.commit()


def test_dai_cuong_only_no_classify(client, admin_token, db):
    """SV chỉ học đại cương HK1-6 (vd ĐSTT bị tag spec sai do data pollution) → KHÔNG bị gán CN."""
    sv = _make_sv(db, '2400000001', spec=None)
    # Tạo môn đại cương HK1, BỊ TAG SAI required_specialization='7480201_07'
    db.add(models.Course(
        course_code='7010102', course_name='Đại số tuyến tính',
        credits=4, count_toward_credits=True, typical_semester=1,
        required_specialization='7480201_07',  # tag sai (test pollution)
    ))
    db.commit()
    _add_grade(db, sv.id, '7010102')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.post('/admin/students/auto-classify', headers=H)
    assert r.status_code == 200, r.json()

    db.refresh(sv)
    assert sv.specialization is None, f"SV bị classify nhầm: {sv.specialization}"


def test_classify_when_takes_cn_specific(client, admin_token, db):
    """SV học môn HK7+ thuộc 1 CN cụ thể → được classify đúng CN đó."""
    sv = _make_sv(db, '2200000002', spec=None)
    # Môn KHMT bắt buộc HK7
    db.add(models.Course(
        course_code='7080508', course_name='Khai phá dữ liệu',
        credits=3, count_toward_credits=True, typical_semester=7,
        required_specialization='7480201_07',
    ))
    db.commit()
    _add_grade(db, sv.id, '7080508')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.post('/admin/students/auto-classify', headers=H)
    assert r.status_code == 200

    db.refresh(sv)
    assert sv.specialization == '7480201_07', f"Should classify KHMT but got: {sv.specialization}"


def test_multi_spec_course_does_not_classify(client, admin_token, db):
    """SV học môn pool_c có ở nhiều CN → KHÔNG dùng môn này để classify (ambiguous)."""
    sv = _make_sv(db, '2200000003', spec=None)
    # Môn pool_c thuộc cả KHMT, MMT, CNTTDH (multi-CN qua M2M)
    db.add(models.Course(
        course_code='7080507', course_name='Dữ liệu lớn và ứng dụng',
        credits=3, count_toward_credits=True, typical_semester=8,
        required_specialization=None,
    ))
    db.commit()
    db.add(models.CourseSpecialization(course_code='7080507', specialization='7480201_07'))
    db.add(models.CourseSpecialization(course_code='7080507', specialization='7480201_06'))
    db.add(models.CourseSpecialization(course_code='7080507', specialization='7480201_08'))
    db.commit()
    _add_grade(db, sv.id, '7080507')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.post('/admin/students/auto-classify', headers=H)
    db.refresh(sv)
    assert sv.specialization is None, f"Multi-spec course KHÔNG được classify, got: {sv.specialization}"


def test_no_grades_stays_general(client, admin_token, db):
    """SV mới chưa có điểm → stays NULL (đại cương)."""
    sv = _make_sv(db, '2400000004', spec=None)
    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.post('/admin/students/auto-classify', headers=H)
    db.refresh(sv)
    assert sv.specialization is None
