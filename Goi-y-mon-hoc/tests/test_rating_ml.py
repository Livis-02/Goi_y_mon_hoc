"""Verify peer rating ảnh hưởng đến recommendation."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    sv = models.User(username='sv_r', email='r@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    db.add(models.Course(course_code='7080111', course_name='Mã nguồn mở',
                         credits=2, count_toward_credits=True, typical_semester=5))
    db.commit()
    # 5 SV khác đã pass + rate cao
    for i in range(5):
        u = models.User(username=f'rater{i}', email=f'r{i}@x.c', full_name=f'R{i}',
                       role='student', password_hash=_hash_password('x'))
        db.add(u); db.flush()
        db.add(models.UserGrade(user_id=u.id, course_code='7080111',
                                term='HK1/2024', score10=8, score4=3, letter='B', passed=True))
        db.add(models.CourseRating(user_id=u.id, course_code='7080111', rating=5))
    db.commit()
    r = client.post('/auth/login', json={'username':'sv_r','password':'Test@1234'})
    return {'token': r.json()['access_token']}


def test_why_not_includes_peer_rating(client, db, setup):
    """why-not endpoint trả reason 'peer_rating' khi môn có rating cao."""
    H = {'Authorization': f'Bearer {setup["token"]}'}
    r = client.get('/recommendations/why-not/7080111', headers=H)
    d = r.json()
    peer_reasons = [x for x in d.get('reasons', []) if x.get('category') == 'peer_rating']
    if d['verdict'] == 'recommended':
        assert any(x['kind'] == 'positive' for x in peer_reasons), f"Expected positive peer rating: {d}"


def test_admin_courses_grouped_returns_avg_rating(client, db, setup):
    """Admin endpoint trả avg_rating + rating_count cho mỗi môn."""
    admin = models.User(username='at_r', email='a@x.c', full_name='A',
                       role='admin', password_hash=_hash_password('x'))
    db.add(admin); db.commit()
    rt = client.post('/auth/login', json={'username':'at_r','password':'x'}).json()['access_token']
    H = {'Authorization': f'Bearer {rt}'}
    r = client.get('/admin/courses/grouped?spec=common', headers=H)
    assert r.status_code == 200
    courses = r.json().get('compulsory', [])
    target = next((c for c in courses if c['course_code'] == '7080111'), None)
    if target:
        assert 'avg_rating' in target
        assert 'rating_count' in target
        assert target['avg_rating'] == 5.0
        assert target['rating_count'] == 5
