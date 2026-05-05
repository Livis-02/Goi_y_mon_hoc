"""Verify dashboard cảnh báo SV quá hạn — đo qua span năm học thực tế trong grades."""
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


def _make_sv(db, code, tc=None):
    sv = models.User(
        username=code, email=f'{code}@x.com',
        full_name='SV Test', role='student',
        password_hash=_hash_password('x'),
        official_earned_credits=tc,
    )
    db.add(sv); db.commit()
    return sv


def _add_grade_term(db, user_id, course_code, term):
    if not db.query(models.Course).filter(models.Course.course_code == course_code).first():
        db.add(models.Course(
            course_code=course_code, course_name=f'Mon {course_code}',
            credits=3, count_toward_credits=True,
        ))
        db.flush()
    db.add(models.UserGrade(
        user_id=user_id, course_code=course_code,
        term=term, score10=8.0, score4=3.0, letter='B', passed=True,
    ))
    db.commit()


def test_overdue_when_grade_span_more_than_5_years(client, admin_token, db):
    """SV có grades trải 6 năm (2020-2025) + TC<threshold → cảnh báo."""
    sv = _make_sv(db, '2000000099', tc=50.0)
    _add_grade_term(db, sv.id, '7010101', 'Học kỳ 1 - Năm học 2020-2021')
    _add_grade_term(db, sv.id, '7010102', 'Học kỳ 1 - Năm học 2025-2026')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/admin/dashboard/stats', headers=H)
    warnings = r.json()['warnings']
    assert any('quá hạn' in w['message'] for w in warnings), \
        f"Missing overdue warning for 6-year span SV: {warnings}"


def test_not_overdue_when_only_one_term(client, admin_token, db):
    """SV mã K14 nhưng chỉ 1 kỳ → KHÔNG bị flag overdue (cohort của mã không còn dùng)."""
    sv = _make_sv(db, '1400000099', tc=17.0)
    _add_grade_term(db, sv.id, '7010103', 'Học kỳ 1 - Năm học 2025-2026')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/admin/dashboard/stats', headers=H)
    warnings = r.json()['warnings']
    overdue = [w for w in warnings if 'quá hạn' in w['message']]
    # Không SV nào trong test này có span > 5 → 0 overdue
    assert not overdue, f"False positive: {overdue}"


def test_not_overdue_when_span_is_5_or_less(client, admin_token, db):
    """SV span đúng 5 năm (2021-2025) → KHÔNG cảnh báo (chưa quá hạn)."""
    sv = _make_sv(db, '2100000099', tc=80.0)
    _add_grade_term(db, sv.id, '7010104', 'Học kỳ 1 - Năm học 2021-2022')
    _add_grade_term(db, sv.id, '7010105', 'Học kỳ 1 - Năm học 2025-2026')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/admin/dashboard/stats', headers=H)
    warnings = r.json()['warnings']
    overdue = [w for w in warnings if 'quá hạn' in w['message']]
    assert not overdue, f"5-year span shouldn't flag: {overdue}"


def test_not_overdue_when_long_span_but_enough_credits(client, admin_token, db):
    """SV span 6 năm nhưng ĐỦ TC tốt nghiệp → KHÔNG cảnh báo."""
    sv = _make_sv(db, '2000000098', tc=160.0)  # >= 153
    _add_grade_term(db, sv.id, '7010106', 'Học kỳ 1 - Năm học 2020-2021')
    _add_grade_term(db, sv.id, '7010107', 'Học kỳ 1 - Năm học 2025-2026')

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/admin/dashboard/stats', headers=H)
    warnings = r.json()['warnings']
    overdue = [w for w in warnings if 'quá hạn' in w['message']]
    assert not overdue, f"Has enough credits, shouldn't flag: {overdue}"
