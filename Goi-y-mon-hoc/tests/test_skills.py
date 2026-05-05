"""Test skills CRUD + course_skills + career_skills."""
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


@pytest.fixture()
def sv_token(client, db):
    sv = models.User(username='sv1', email='s@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'sv1','password':'Test@1234'})
    return r.json()['access_token']


def test_skill_crud(client, admin_token):
    H = {'Authorization': f'Bearer {admin_token}'}
    r = client.post('/admin/skills', headers=H, json={
        'code':'python', 'name':'Python', 'category':'programming',
        'description':'Ngôn ngữ lập trình Python'
    })
    assert r.status_code == 200
    assert r.json()['code'] == 'PYTHON'  # auto-uppercase

    r = client.get('/skills')
    assert r.status_code == 200
    codes = [s['code'] for s in r.json()]
    assert 'PYTHON' in codes

    r = client.put('/admin/skills/PYTHON', headers=H, json={
        'code':'PYTHON', 'name':'Python 3', 'category':'programming'
    })
    assert r.json()['name'] == 'Python 3'

    r = client.delete('/admin/skills/PYTHON', headers=H)
    assert r.status_code == 200


def test_course_skills_replace(client, admin_token, db):
    H = {'Authorization': f'Bearer {admin_token}'}
    db.add(models.Course(course_code='7080111', course_name='Mã nguồn mở',
                         credits=2, count_toward_credits=True))
    db.add(models.Skill(code='LINUX', name='Linux', category='network'))
    db.add(models.Skill(code='OSS', name='Mã nguồn mở', category='programming'))
    db.commit()

    r = client.put('/admin/courses/7080111/skills', headers=H, json={
        'skills': [
            {'skill_code':'LINUX', 'weight': 0.8},
            {'skill_code':'OSS', 'weight': 1.0},
        ]
    })
    assert r.status_code == 200
    skills = r.json()
    assert len(skills) == 2
    assert {s['skill_code'] for s in skills} == {'LINUX', 'OSS'}

    # Replace với 1 skill khác
    r = client.put('/admin/courses/7080111/skills', headers=H, json={
        'skills': [{'skill_code':'LINUX', 'weight': 1.0}]
    })
    skills = r.json()
    assert len(skills) == 1
    assert skills[0]['skill_code'] == 'LINUX'

    # GET public
    r = client.get('/courses/7080111/skills')
    assert len(r.json()) == 1


def test_invalid_skill_rejected(client, admin_token, db):
    H = {'Authorization': f'Bearer {admin_token}'}
    db.add(models.Course(course_code='7080112', course_name='X', credits=2, count_toward_credits=True))
    db.commit()
    r = client.put('/admin/courses/7080112/skills', headers=H, json={
        'skills': [{'skill_code':'NOEXIST', 'weight': 1.0}]
    })
    assert r.status_code == 400


def test_career_skills_set_get(client, sv_token, db):
    H = {'Authorization': f'Bearer {sv_token}'}
    db.add(models.Skill(code='PYTHON', name='Python', category='programming'))
    db.add(models.Skill(code='WEB', name='Web Dev', category='web'))
    db.commit()

    r = client.put('/me/career-skills', headers=H, json={
        'career_skills':['PYTHON', 'WEB', 'INVALID']
    })
    assert r.status_code == 200
    assert sorted(r.json()['career_skills']) == ['PYTHON', 'WEB']  # INVALID lọc bỏ

    r = client.get('/me/career-skills', headers=H)
    assert sorted(r.json()['career_skills']) == ['PYTHON', 'WEB']
