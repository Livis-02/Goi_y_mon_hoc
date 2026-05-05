"""Test endpoint /courses/{code}/details."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup_course(client, db):
    sv = models.User(username='svdt', email='s@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    db.add(models.Course(course_code='7080208', course_name='Cơ sở lập trình',
                         credits=3, count_toward_credits=True, typical_semester=2,
                         description='Môn nhập môn lập trình Python'))
    db.add(models.Course(course_code='7080206', course_name='Cấu trúc dữ liệu',
                         credits=3, count_toward_credits=True, typical_semester=4))
    db.commit()
    db.add(models.CoursePrerequisite(course_code='7080206', prerequisite_code='7080208'))
    db.add(models.Skill(code='PYTHON', name='Python', category='programming'))
    db.add(models.Skill(code='ALGO', name='Algorithm', category='programming'))
    db.commit()
    db.add(models.CourseSkill(course_code='7080208', skill_code='PYTHON', weight=1.0))
    db.add(models.CourseSkill(course_code='7080208', skill_code='ALGO', weight=0.5))
    db.commit()
    r = client.post('/auth/login', json={'username':'svdt','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token']}


def test_course_details_full_response(client, setup_course):
    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    r = client.get('/courses/7080208/details', headers=H)
    assert r.status_code == 200
    d = r.json()
    # Course info
    assert d['course_code'] == '7080208'
    assert d['course_name'] == 'Cơ sở lập trình'
    assert d['credits'] == 3.0
    assert d['typical_semester'] == 2
    assert d['description'] == 'Môn nhập môn lập trình Python'
    # Skills (2 cái, sorted by weight desc)
    assert len(d['skills']) == 2
    assert d['skills'][0]['skill_code'] == 'PYTHON'
    assert d['skills'][0]['weight'] == 1.0
    assert d['skills'][1]['skill_code'] == 'ALGO'
    # Prereqs (môn này không có tiên quyết)
    assert d['prereqs'] == []
    # Downstream — 7080206 cần 7080208
    assert len(d['downstream']) == 1
    assert d['downstream'][0]['course_code'] == '7080206'
    # Rating empty
    assert d['rating']['count'] == 0
    assert d['rating']['avg'] is None
    # SV chưa pass → can_rate=False, status=not_taken
    assert d['can_rate'] is False
    assert d['student_status']['status'] == 'not_taken'


def test_course_details_with_passed_grade(client, db, setup_course):
    sv = setup_course['sv']
    db.add(models.UserGrade(user_id=sv.id, course_code='7080208', term='HK1/2024',
                            score10=8.5, score4=3.7, letter='A', passed=True))
    db.commit()
    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    r = client.get('/courses/7080208/details', headers=H)
    d = r.json()
    assert d['student_status']['status'] == 'passed'
    assert d['student_status']['score10'] == 8.5
    assert d['can_rate'] is True


def test_course_details_prereq_status(client, db, setup_course):
    sv = setup_course['sv']
    db.add(models.UserGrade(user_id=sv.id, course_code='7080208', term='HK1/2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.commit()
    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    r = client.get('/courses/7080206/details', headers=H)
    d = r.json()
    # Môn 7080206 có tiên quyết 7080208 (đã pass)
    assert len(d['prereqs']) == 1
    assert d['prereqs'][0]['course_code'] == '7080208'
    assert d['prereqs'][0]['status'] == 'passed'
    assert d['prereqs'][0]['score10'] == 8.0


def test_course_details_404_for_unknown(client, setup_course):
    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    r = client.get('/courses/9999999/details', headers=H)
    assert r.status_code == 404


def test_reviews_endpoint_basic(client, db, setup_course):
    """Reviews endpoint trả paginated + anonymized."""
    sv = setup_course['sv']
    # SV này pass + rate có review
    db.add(models.UserGrade(user_id=sv.id, course_code='7080208', term='HK1/2024',
                            score10=8, score4=3, letter='B', passed=True))
    db.add(models.CourseRating(user_id=sv.id, course_code='7080208',
                               rating=5, review='Môn rất hay, GV chấm chặt'))
    # 2 SV khác rate có review
    for i in range(2):
        u = models.User(username=f'2400000{i:03d}', email=f's{i}@x.c',
                       full_name=f'Nguyễn Văn {chr(65+i)}',
                       role='student', password_hash=_hash_password('x'))
        db.add(u); db.flush()
        db.add(models.CourseRating(user_id=u.id, course_code='7080208',
                                   rating=4, review=f'Review #{i+1}'))
    # 1 SV chỉ rate stars (không có review text) — không hiện
    u3 = models.User(username='2400000099', email='s99@x.c', full_name='X',
                    role='student', password_hash=_hash_password('x'))
    db.add(u3); db.flush()
    db.add(models.CourseRating(user_id=u3.id, course_code='7080208', rating=3))
    db.commit()

    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    r = client.get('/courses/7080208/reviews', headers=H)
    assert r.status_code == 200
    d = r.json()
    assert d['total'] == 3  # 3 review có text (loại bỏ 1 stars-only)
    assert len(d['items']) == 3
    # Có 1 review của mình
    mine = [it for it in d['items'] if it['is_mine']]
    assert len(mine) == 1
    assert mine[0]['display_name'] == 'Bạn'
    assert mine[0]['rating'] == 5
    # Reviews khác bị anonymize
    others = [it for it in d['items'] if not it['is_mine']]
    for it in others:
        assert it['display_name'].endswith('***')
        assert it.get('cohort')  # K24


def test_reviews_pagination(client, db, setup_course):
    H = {'Authorization': f'Bearer {setup_course["token"]}'}
    # Seed 5 reviews
    for i in range(5):
        u = models.User(username=f'2400001{i:03d}', email=f'p{i}@x.c',
                       full_name=f'P{i}', role='student',
                       password_hash=_hash_password('x'))
        db.add(u); db.flush()
        db.add(models.CourseRating(user_id=u.id, course_code='7080208',
                                   rating=3 + (i % 3),
                                   review=f'Review pagination {i}'))
    db.commit()
    r = client.get('/courses/7080208/reviews?limit=2&offset=0', headers=H)
    d = r.json()
    assert d['total'] == 5
    assert len(d['items']) == 2
    r2 = client.get('/courses/7080208/reviews?limit=2&offset=2', headers=H)
    assert len(r2.json()['items']) == 2
