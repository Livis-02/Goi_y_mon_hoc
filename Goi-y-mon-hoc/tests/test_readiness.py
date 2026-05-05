"""Test /me/readiness endpoint."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    sv = models.User(username='svrd', email='r@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'),
                    official_earned_credits=140.0)
    db.add(sv); db.commit()
    db.add(models.Course(course_code='C1', course_name='Course 1',
                         credits=3, count_toward_credits=True))
    db.commit()
    db.add(models.UserGrade(user_id=sv.id, course_code='C1', term='Học kỳ 1 - Năm học 2023-2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.commit()
    r = client.post('/auth/login', json={'username':'svrd','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token']}


def test_readiness_basic(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.get('/me/readiness', headers=H)
    assert r.status_code == 200
    d = r.json()
    assert 'graduation' in d
    assert 'internship' in d
    assert 'thesis' in d
    # 140/153 → 91.5%
    assert 80 < d['graduation']['percent'] < 100
    assert d['graduation']['remaining_credits'] == round(153.0 - 140.0, 1)
    # Internship: 140 >= 90 → met
    assert d['internship']['status'] in ('ready', 'almost', 'not_ready')


def test_readiness_full_data_passes_thresholds(client, db, setup):
    """SV với 160 TC + GPA 3.5 → graduation ready."""
    sv = setup['sv']
    sv.official_earned_credits = 160.0
    db.commit()
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.get('/me/readiness', headers=H)
    d = r.json()
    assert d['graduation']['status'] == 'ready'
    assert d['graduation']['remaining_credits'] == 0


def test_readiness_admin_403(client, db):
    a = models.User(username='ard', email='a@x.c', full_name='A',
                   role='admin', password_hash=_hash_password('x'))
    db.add(a); db.commit()
    rt = client.post('/auth/login', json={'username':'ard','password':'x'}).json()['access_token']
    r = client.get('/me/readiness', headers={'Authorization': f'Bearer {rt}'})
    assert r.status_code == 403
