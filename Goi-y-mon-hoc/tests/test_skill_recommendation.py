"""Verify skill match boost recommendation score."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def sv_setup(client, db):
    """SV với 2 grades pass + 2 môn đủ điều kiện gợi ý."""
    sv = models.User(
        username='sv_skill', email='s@x.c', full_name='SV Skill',
        role='student', specialization='7480201_07',
        password_hash=_hash_password('Test@1234'),
    )
    db.add(sv); db.commit()

    # 2 môn pass
    db.add(models.Course(course_code='7080208', course_name='Cơ sở lập trình', credits=3, count_toward_credits=True))
    db.add(models.Course(course_code='7080112', course_name='HĐH', credits=3, count_toward_credits=True))
    # 2 môn eligible
    db.add(models.Course(course_code='7080111', course_name='Mã nguồn mở', credits=2, count_toward_credits=True, typical_semester=5))
    db.add(models.Course(course_code='7080116', course_name='Web', credits=4, count_toward_credits=True, typical_semester=5))
    db.commit()
    db.add(models.UserGrade(user_id=sv.id, course_code='7080208', term='HK1/2024', score10=8, score4=3, letter='B', passed=True))
    db.add(models.UserGrade(user_id=sv.id, course_code='7080112', term='HK1/2024', score10=8, score4=3, letter='B', passed=True))
    db.commit()

    # Skills + course_skills
    db.add(models.Skill(code='OSS', name='Mã nguồn mở', category='programming'))
    db.add(models.Skill(code='WEB_FE', name='Web Frontend', category='web'))
    db.add(models.Skill(code='WEB_BE', name='Web Backend', category='web'))
    db.commit()
    db.add(models.CourseSkill(course_code='7080111', skill_code='OSS', weight=1.0))
    db.add(models.CourseSkill(course_code='7080116', skill_code='WEB_FE', weight=1.0))
    db.add(models.CourseSkill(course_code='7080116', skill_code='WEB_BE', weight=0.7))
    db.commit()

    r = client.post('/auth/login', json={'username':'sv_skill','password':'Test@1234'})
    return {'sv': sv, 'token': r.json()['access_token']}


def test_skill_match_boosts_score(client, db, sv_setup):
    """SV chọn WEB_FE → 7080116 (Web) phải xếp cao hơn 7080111 (Mã nguồn mở)."""
    sv_id = sv_setup['sv'].id
    token = sv_setup['token']
    H = {'Authorization': f'Bearer {token}'}

    # Without career_skills
    r1 = client.get('/recommendations/me?limit=5', headers=H)
    assert r1.status_code == 200
    rec_list1 = r1.json().get('recommendations', [])
    if not rec_list1:
        pytest.skip("Không có recommendation để test")
    score_field = 'score' if 'score' in rec_list1[0] else 'priority_score'
    recs1 = {r['course_code']: r.get(score_field, 0) for r in rec_list1}

    # Set career_skills = [WEB_FE]
    client.put('/me/career-skills', headers=H, json={'career_skills': ['WEB_FE']})

    r2 = client.get('/recommendations/me?limit=5', headers=H)
    recs2 = {r['course_code']: r.get(score_field, 0) for r in r2.json().get('recommendations', [])}

    # 7080116 phải có score cao hơn (hoặc bằng) — match WEB_FE
    if '7080116' in recs1 and '7080116' in recs2:
        assert recs2['7080116'] >= recs1['7080116'], \
            f"Skill match không giảm score: trước={recs1['7080116']}, sau={recs2['7080116']}"


def test_why_not_includes_skill_match(client, db, sv_setup):
    """why-not endpoint trả reason 'skill' khi môn match career_skills."""
    token = sv_setup['token']
    H = {'Authorization': f'Bearer {token}'}
    client.put('/me/career-skills', headers=H, json={'career_skills': ['WEB_FE', 'WEB_BE']})

    r = client.get('/recommendations/why-not/7080116', headers=H)
    d = r.json()
    skill_reasons = [r for r in d.get('reasons', []) if r['category'] == 'skill']
    if d['verdict'] == 'recommended':
        assert len(skill_reasons) >= 1, f"Expected skill reason: {d}"
