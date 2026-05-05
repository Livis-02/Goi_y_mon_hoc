"""Test /me/compare-scenarios endpoint."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    sv = models.User(username='svcs', email='c@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'),
                    official_earned_credits=80.0)
    db.add(sv); db.commit()
    # Skills + paths
    db.add(models.Skill(code='PYTHON', name='Python', category='programming'))
    db.add(models.Skill(code='ML', name='ML', category='ai'))
    db.add(models.Skill(code='WEB_FE', name='Web Frontend', category='web'))
    db.commit()
    p1 = models.CareerPath(code='ml_test', name='ML Test', icon='psychology', color='violet')
    p2 = models.CareerPath(code='fe_test', name='FE Test', icon='web', color='emerald')
    db.add(p1); db.add(p2); db.commit()
    db.add(models.CareerPathSkill(path_id=p1.id, skill_code='PYTHON', importance=1.0))
    db.add(models.CareerPathSkill(path_id=p1.id, skill_code='ML', importance=1.0))
    db.add(models.CareerPathSkill(path_id=p2.id, skill_code='WEB_FE', importance=1.0))
    db.commit()
    db.add(models.Course(course_code='CP1', course_name='Python', credits=3, count_toward_credits=True))
    db.commit()
    db.add(models.CourseSkill(course_code='CP1', skill_code='PYTHON', weight=1.0))
    db.commit()
    db.add(models.UserGrade(user_id=sv.id, course_code='CP1', term='HK1/2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.commit()
    r = client.post('/auth/login', json={'username':'svcs','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token']}


def test_compare_basic(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.post('/me/compare-scenarios', headers=H, json={
        'scenario_a': {'career_code': 'ml_test', 'credits_per_term': 18},
        'scenario_b': {'career_code': 'fe_test', 'credits_per_term': 22},
    })
    assert r.status_code == 200
    d = r.json()
    assert 'scenario_a' in d
    assert 'scenario_b' in d
    assert d['scenario_a']['career_path']['code'] == 'ml_test'
    assert d['scenario_b']['career_path']['code'] == 'fe_test'
    assert d['scenario_a']['credits_per_term'] == 18
    assert d['scenario_b']['credits_per_term'] == 22
    # SV has PYTHON → ml_test fit higher than fe_test
    assert d['scenario_a']['fit_score'] >= d['scenario_b']['fit_score']
    # Winner advice
    assert d['winner'] in ('A', 'B', 'tie')


def test_compare_difficulty_assessment(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.post('/me/compare-scenarios', headers=H, json={
        'scenario_a': {'career_code': 'ml_test', 'credits_per_term': 16},
        'scenario_b': {'career_code': 'ml_test', 'credits_per_term': 24},
    })
    d = r.json()
    assert d['scenario_a']['difficulty']['label'] == 'Nhẹ nhàng'
    assert d['scenario_b']['difficulty']['label'] in ('Áp lực cao', 'Quá tải')


def test_compare_admin_403(client, db):
    a = models.User(username='acs', email='a@x.c', full_name='A',
                   role='admin', password_hash=_hash_password('x'))
    db.add(a); db.commit()
    rt = client.post('/auth/login', json={'username':'acs','password':'x'}).json()['access_token']
    r = client.post('/me/compare-scenarios', headers={'Authorization': f'Bearer {rt}'},
                    json={'scenario_a': {}, 'scenario_b': {}})
    assert r.status_code == 403
