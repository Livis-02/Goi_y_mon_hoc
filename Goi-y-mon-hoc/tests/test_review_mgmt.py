"""Test DELETE rate + GET /me/reviews."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    sv = models.User(username='svrm', email='m@x.c', full_name='SV',
                    role='student', password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    db.add(models.Course(course_code='C001', course_name='Course 1',
                         credits=3, count_toward_credits=True))
    db.add(models.Course(course_code='C002', course_name='Course 2',
                         credits=3, count_toward_credits=True))
    db.commit()
    # SV pass cả 2
    db.add(models.UserGrade(user_id=sv.id, course_code='C001', term='HK1/2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.add(models.UserGrade(user_id=sv.id, course_code='C002', term='HK1/2024',
                            score10=9, score4=4, letter='A', passed=True))
    db.commit()
    # SV rate 2 môn
    db.add(models.CourseRating(user_id=sv.id, course_code='C001', rating=4, review='Khá hay'))
    db.add(models.CourseRating(user_id=sv.id, course_code='C002', rating=5, review=None))
    db.commit()
    r = client.post('/auth/login', json={'username':'svrm','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token']}


def test_delete_own_rating(client, db, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.delete('/courses/C001/rate', headers=H)
    assert r.status_code == 200
    assert 'Đã xóa' in r.json()['message']
    # Verify gone
    rem = db.query(models.CourseRating).filter(
        models.CourseRating.user_id == setup['sv'].id,
        models.CourseRating.course_code == 'C001',
    ).first()
    assert rem is None


def test_delete_nonexistent_rating(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.delete('/courses/C999/rate', headers=H)
    assert r.status_code == 404


def test_list_my_reviews(client, setup):
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.get('/me/reviews', headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d['total'] == 2
    by_code = {item['course_code']: item for item in d['items']}
    assert by_code['C001']['rating'] == 4
    assert by_code['C001']['has_review'] is True
    assert by_code['C001']['review'] == 'Khá hay'
    assert by_code['C002']['rating'] == 5
    assert by_code['C002']['has_review'] is False


def test_list_my_reviews_empty(client, db):
    sv = models.User(username='svrm2', email='m2@x.c', full_name='SV2',
                    role='student', password_hash=_hash_password('x'))
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'svrm2','password':'x'})
    rr = client.get('/me/reviews', headers={'Authorization': f'Bearer {r.json()["access_token"]}'})
    assert rr.status_code == 200
    assert rr.json()['total'] == 0


def test_my_reviews_admin_403(client, db):
    a = models.User(username='arm', email='a@x.c', full_name='A',
                   role='admin', password_hash=_hash_password('x'))
    db.add(a); db.commit()
    rt = client.post('/auth/login', json={'username':'arm','password':'x'}).json()['access_token']
    r = client.get('/me/reviews', headers={'Authorization': f'Bearer {rt}'})
    assert r.status_code == 403
