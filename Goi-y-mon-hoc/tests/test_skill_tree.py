"""Test /me/skill-tree endpoint."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    sv = models.User(username='svst', email='st@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    # Skills
    db.add(models.Skill(code='PYTHON', name='Python', category='programming'))
    db.add(models.Skill(code='ML', name='Machine Learning', category='ai'))
    db.add(models.Skill(code='SQL', name='SQL', category='db'))
    db.commit()
    # Career path + required skills
    p = models.CareerPath(code='ml_eng_test', name='ML Eng Test',
                          short_description='Test', icon='psychology', color='violet')
    db.add(p); db.commit()
    db.add(models.CareerPathSkill(path_id=p.id, skill_code='PYTHON', importance=1.0))
    db.add(models.CareerPathSkill(path_id=p.id, skill_code='ML', importance=1.0))
    db.add(models.CareerPathSkill(path_id=p.id, skill_code='SQL', importance=0.7))
    db.commit()
    # Course teaching PYTHON (SV passed) + course teaching ML (SV chưa pass)
    db.add(models.Course(course_code='C001', course_name='Python Course',
                         credits=3, count_toward_credits=True))
    db.add(models.Course(course_code='C002', course_name='ML Course',
                         credits=3, count_toward_credits=True))
    db.commit()
    db.add(models.CourseSkill(course_code='C001', skill_code='PYTHON', weight=1.0))
    db.add(models.CourseSkill(course_code='C002', skill_code='ML', weight=1.0))
    db.commit()
    # SV pass C001
    db.add(models.UserGrade(user_id=sv.id, course_code='C001', term='HK1/2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.commit()
    r = client.post('/auth/login', json={'username':'svst','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token'], 'path': p}


def test_skill_tree_with_career(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.get('/me/skill-tree?career_code=ml_eng_test', headers=H)
    assert r.status_code == 200
    d = r.json()
    # Career resolved
    assert d['career_path']['code'] == 'ml_eng_test'
    # Summary (evidence-based — no %)
    assert d['summary']['total_required'] == 3  # PYTHON, ML, SQL
    assert d['summary']['evidenced'] == 1  # PYTHON (passed C001)
    assert d['summary']['no_evidence'] == 2  # ML, SQL
    # Skills list
    skills_by_code = {s['code']: s for s in d['skills']}
    # PYTHON: evidenced via course pass
    assert skills_by_code['PYTHON']['status'] == 'evidenced'
    assert skills_by_code['PYTHON']['tag'] == 'core'  # importance 1.0 >= 0.7
    assert skills_by_code['PYTHON']['required'] is True
    assert len(skills_by_code['PYTHON']['evidence_courses']) == 1
    assert skills_by_code['PYTHON']['evidence_courses'][0]['course_code'] == 'C001'
    assert skills_by_code['PYTHON']['evidence_personal'] == []
    # ML: no evidence
    assert skills_by_code['ML']['status'] == 'no_evidence'
    assert skills_by_code['ML']['evidence_courses'] == []
    # SQL: importance 0.7 → core (0.7 >= 0.7)
    assert skills_by_code['SQL']['tag'] == 'core'
    # Recommended courses to fill gap
    rec_codes = [c['course_code'] for c in d['recommended_courses']]
    assert 'C002' in rec_codes  # course teaches ML which is missing
    rec_c002 = next(c for c in d['recommended_courses'] if c['course_code'] == 'C002')
    assert rec_c002['skills_unlocked'] == 1  # unlocks ML


def test_skill_tree_no_career(client, db):
    """SV chưa chọn career → trả empty required + skills owned"""
    sv = models.User(username='svst2', email='st2@x.c', full_name='SV2',
                    role='student', password_hash=_hash_password('x'))
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'svst2','password':'x'})
    H = {'Authorization': f'Bearer {r.json()["access_token"]}'}
    rr = client.get('/me/skill-tree', headers=H)
    assert rr.status_code == 200
    d = rr.json()
    assert d['career_path'] is None
    assert d['summary']['total_required'] == 0


def test_skill_tree_with_personal_evidence(client, db, setup):
    """SV thêm evidence cá nhân → skill thành 'evidenced'."""
    H = {'Authorization': f'Bearer {setup["token"]}'}
    # SQL ban đầu chưa có evidence
    r1 = client.get('/me/skill-tree?career_code=ml_eng_test', headers=H)
    skills1 = {s['code']: s for s in r1.json()['skills']}
    assert skills1['SQL']['status'] == 'no_evidence'

    # SV thêm GitHub project cho SQL
    add = client.post('/skills/SQL/evidence', headers=H, json={
        'type': 'github',
        'url': 'https://github.com/em/sql-project',
        'label': 'SQL portfolio project',
    })
    assert add.status_code == 201

    # Refetch — SQL phải thành evidenced
    r2 = client.get('/me/skill-tree?career_code=ml_eng_test', headers=H)
    skills2 = {s['code']: s for s in r2.json()['skills']}
    assert skills2['SQL']['status'] == 'evidenced'
    assert len(skills2['SQL']['evidence_personal']) == 1
    assert skills2['SQL']['evidence_personal'][0]['type'] == 'github'


def test_skill_tree_admin_403(client, db):
    admin = models.User(username='ast', email='a@x.c', full_name='A',
                       role='admin', password_hash=_hash_password('x'))
    db.add(admin); db.commit()
    rt = client.post('/auth/login', json={'username':'ast','password':'x'}).json()['access_token']
    r = client.get('/me/skill-tree', headers={'Authorization': f'Bearer {rt}'})
    assert r.status_code == 403
