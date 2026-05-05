"""Verify why-not endpoint trả structured response (verdict + reasons array)."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def sv_token(client, db):
    sv = models.User(
        username='sv_why', email='sv@x.c', full_name='SV',
        role='student', specialization='7480201_07',
        password_hash=_hash_password('Test@1234'),
    )
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'sv_why','password':'Test@1234'})
    return r.json()['access_token']


def test_why_not_returns_structured_format(client, sv_token, db):
    """Response phải có verdict + reasons array."""
    db.add(models.Course(
        course_code='7080501', course_name='Test môn',
        credits=3, count_toward_credits=True,
        required_specialization='7480201_07',
    ))
    db.commit()
    H = {'Authorization': f'Bearer {sv_token}'}
    r = client.get('/recommendations/why-not/7080501', headers=H)
    assert r.status_code == 200
    d = r.json()
    assert 'verdict' in d
    assert 'reasons' in d
    assert isinstance(d['reasons'], list)
    assert len(d['reasons']) >= 1
    for reason in d['reasons']:
        assert 'kind' in reason
        assert 'category' in reason
        assert 'title' in reason
        assert 'detail' in reason


def test_why_not_wrong_spec(client, sv_token, db):
    """SV KHMT hỏi về môn MMT → blocker spec."""
    db.add(models.Course(
        course_code='7080502', course_name='Môn MMT',
        credits=3, count_toward_credits=True,
        required_specialization='7480201_06',  # MMT
    ))
    db.commit()
    H = {'Authorization': f'Bearer {sv_token}'}
    r = client.get('/recommendations/why-not/7080502', headers=H)
    d = r.json()
    assert d['verdict'] == 'blocked'
    assert any(r['category'] == 'spec' and r['kind'] == 'blocker' for r in d['reasons'])


def test_why_not_missing_prereq(client, sv_token, db):
    """SV chưa pass tiên quyết → blocker prereq."""
    db.add(models.Course(course_code='7080503', course_name='Môn cơ sở', credits=3, count_toward_credits=True))
    db.add(models.Course(course_code='7080504', course_name='Môn nâng cao', credits=3, count_toward_credits=True))
    db.add(models.CoursePrerequisite(course_code='7080504', prerequisite_code='7080503'))
    db.commit()
    H = {'Authorization': f'Bearer {sv_token}'}
    r = client.get('/recommendations/why-not/7080504', headers=H)
    d = r.json()
    assert d['verdict'] == 'blocked'
    prereq_reasons = [r for r in d['reasons'] if r['category'] == 'prereq']
    assert len(prereq_reasons) >= 1
    # data structure
    assert 'data' in prereq_reasons[0]
    assert 'missing' in prereq_reasons[0]['data']


def test_why_not_completed(client, sv_token, db):
    """SV đã pass môn → verdict completed."""
    db.add(models.Course(course_code='7080505', course_name='Đã pass', credits=3, count_toward_credits=True))
    db.commit()
    sv = db.query(models.User).filter(models.User.username == 'sv_why').first()
    db.add(models.UserGrade(
        user_id=sv.id, course_code='7080505',
        term='HK1/2024', score10=8.5, score4=3.7, letter='A', passed=True,
    ))
    db.commit()
    H = {'Authorization': f'Bearer {sv_token}'}
    r = client.get('/recommendations/why-not/7080505', headers=H)
    d = r.json()
    assert d['verdict'] == 'completed'
    assert any(r['category'] == 'completed' for r in d['reasons'])


def test_why_not_legacy_fields_preserved(client, sv_token, db):
    """Legacy reason_code + explanation + missing_prerequisites vẫn còn."""
    db.add(models.Course(course_code='7080506', course_name='Môn 1', credits=3, count_toward_credits=True))
    db.add(models.Course(course_code='7080507', course_name='Môn 2', credits=3, count_toward_credits=True))
    db.add(models.CoursePrerequisite(course_code='7080507', prerequisite_code='7080506'))
    db.commit()
    H = {'Authorization': f'Bearer {sv_token}'}
    r = client.get('/recommendations/why-not/7080507', headers=H)
    d = r.json()
    assert d.get('reason_code')
    assert d.get('explanation')
    assert d.get('missing_prerequisites') == ['7080506']
