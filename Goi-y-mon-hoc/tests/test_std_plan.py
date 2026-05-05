"""Verify std plan với placeholder Tự chọn A/B/C."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def admin_token(client, db):
    admin = models.User(username='at', email='a@x.c', full_name='Admin',
                       role='admin', password_hash=_hash_password('Test@1234'))
    db.add(admin); db.commit()
    r = client.post('/auth/login', json={'username':'at','password':'Test@1234'})
    return r.json()['access_token']


def test_std_plan_khmt_has_placeholders(client, admin_token, db):
    """KHMT std plan phải có placeholder Tự chọn A/B/C khi spec có ElectiveRule."""
    # Seed: tạo môn cơ bản + ElectiveRule cho KHMT
    db.add(models.Course(course_code='7080508', course_name='Khai phá DL', credits=3, count_toward_credits=True))
    db.add(models.ElectiveRule(program_code='7480201', specialization='7480201_07', group_type='B', min_credits_required=9.0))
    db.add(models.ElectiveRule(program_code='7480201', specialization='7480201_07', group_type='C', min_credits_required=9.0))
    db.add(models.ElectiveRule(program_code='7480201', specialization='7480201_07', group_type='A', min_credits_required=6.0))
    db.commit()

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/courses/standard-plan?spec=7480201_07', headers=H)
    assert r.status_code == 200
    data = r.json()
    
    # Collect all placeholder courses
    placeholders = []
    for sem in data['semesters']:
        for c in sem['courses']:
            if 'POOL' in c['course_code']:
                placeholders.append((sem['semester_number'], c['course_name'], c['credits'], c.get('group')))
    
    # Pool A: 2 slots HK4,5
    a_slots = [p for p in placeholders if 'A' in p[1]]
    assert len(a_slots) == 2, f"Pool A expected 2 slots: {a_slots}"
    assert sorted(p[0] for p in a_slots) == [4, 5]
    
    # Pool B: 3 slots HK7
    b_slots = [p for p in placeholders if 'B' in p[1]]
    assert len(b_slots) == 3, f"Pool B expected 3 slots: {b_slots}"
    assert all(p[0] == 7 for p in b_slots)
    
    # Pool C: 3 slots HK8
    c_slots = [p for p in placeholders if 'C' in p[1]]
    assert len(c_slots) == 3, f"Pool C expected 3 slots: {c_slots}"
    assert all(p[0] == 8 for p in c_slots)
    
    # Verify pool_min_credits trả về
    assert data['pool_min_credits']['A'] == 6.0
    assert data['pool_min_credits']['B'] == 9.0
    assert data['pool_min_credits']['C'] == 9.0


def test_std_plan_no_placeholder_when_no_rules(client, admin_token, db):
    """Spec không có ElectiveRule → không có placeholder."""
    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/courses/standard-plan?spec=7480201_07', headers=H)
    placeholders = [c for sem in r.json()['semesters'] for c in sem['courses'] if 'POOL' in c['course_code']]
    assert placeholders == []


def test_std_plan_excludes_pool_members(client, admin_token, db):
    """Môn pool_b (alternatives) KHÔNG xuất hiện trong std plan."""
    db.add(models.Course(course_code='7080107', course_name='Kiểm thử', credits=3, count_toward_credits=True))
    db.add(models.CourseElectiveGroup(
        course_code='7080107', program_code='7480201',
        specialization='7480201_07', group_type='B'
    ))
    db.add(models.ElectiveRule(program_code='7480201', specialization='7480201_07', group_type='B', min_credits_required=9.0))
    db.commit()

    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.get('/courses/standard-plan?spec=7480201_07', headers=H)
    all_codes = [c['course_code'] for sem in r.json()['semesters'] for c in sem['courses']]
    assert '7080107' not in all_codes, "Pool member course không được xuất hiện trong std plan"
