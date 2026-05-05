"""Tests cho Luồng 2: Career Discovery Journey 12 tuần."""
from __future__ import annotations
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def career_paths(db):
    """Tạo career paths để test."""
    paths = []
    for code, name in [
        ('se', 'Software Engineer'),
        ('data', 'Data Engineer'),
        ('mmt', 'Network Engineer'),
    ]:
        p = db.query(models.CareerPath).filter(models.CareerPath.code == code).first()
        if not p:
            p = models.CareerPath(code=code, name=name, icon='work', color='indigo')
            db.add(p); db.flush()
        paths.append(p)
    db.commit()
    return paths


@pytest.fixture()
def student_token(client, db):
    sv = models.User(
        username='sv_j01', email='svj@x.com', full_name='SV J',
        role='student', specialization='7480201_07',
        password_hash=_hash_password('Test@1234'), is_first_login=False,
    )
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'sv_j01','password':'Test@1234'})
    return {'token': r.json()['access_token'], 'id': sv.id}


@pytest.fixture()
def advisor_user(client, db):
    adv = models.User(
        username='adv_j01', email='advj@x.com', full_name='GV J',
        role='advisor', password_hash=_hash_password('Test@1234'),
    )
    db.add(adv); db.commit()
    r = client.post('/auth/login', json={'username':'adv_j01','password':'Test@1234'})
    return {'token': r.json()['access_token'], 'id': adv.id}


def H(t): return {'Authorization': f'Bearer {t}'}


# ── Start journey ──────────────────────────────────────────────────────────

def test_start_journey_with_2_careers_creates_4_milestones(client, student_token, career_paths):
    r = client.post('/journeys/me', headers=H(student_token['token']), json={
        'candidate_careers': ['se', 'data'],
        'primary_riasec': 'RIA',
    })
    assert r.status_code == 201
    data = r.json()
    assert data['state'] == 'active'
    assert data['candidate_careers'] == ['se', 'data']
    assert len(data['milestones']) == 4
    sequences = [m['sequence'] for m in data['milestones']]
    assert sequences == [1, 2, 3, 4]
    # Milestone 4 là Reflection
    assert 'Reflection' in data['milestones'][3]['title']


def test_start_journey_filters_invalid_careers(client, student_token, career_paths):
    r = client.post('/journeys/me', headers=H(student_token['token']), json={
        'candidate_careers': ['se', 'totally_fake_career'],
    })
    assert r.status_code == 201
    data = r.json()
    assert data['candidate_careers'] == ['se']


def test_start_journey_rejects_empty_careers(client, student_token):
    r = client.post('/journeys/me', headers=H(student_token['token']), json={
        'candidate_careers': [],
    })
    assert r.status_code == 400


def test_start_journey_rejects_all_invalid_careers(client, student_token):
    r = client.post('/journeys/me', headers=H(student_token['token']), json={
        'candidate_careers': ['fake1', 'fake2'],
    })
    assert r.status_code == 400


def test_cannot_start_two_active_journeys(client, student_token, career_paths):
    client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']})
    r2 = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['data']})
    assert r2.status_code == 409


def test_advisor_cannot_start_journey(client, advisor_user, career_paths):
    r = client.post('/journeys/me', headers=H(advisor_user['token']), json={'candidate_careers': ['se']})
    assert r.status_code == 403


# ── Get active ────────────────────────────────────────────────────────────

def test_get_active_returns_null_when_none(client, student_token):
    r = client.get('/journeys/me/active', headers=H(student_token['token']))
    assert r.status_code == 200
    assert r.json()['active_journey'] is None


def test_get_active_includes_milestones(client, student_token, career_paths):
    client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']})
    r = client.get('/journeys/me/active', headers=H(student_token['token']))
    j = r.json()['active_journey']
    assert j is not None
    assert len(j['milestones']) == 4


# ── Milestone lifecycle ───────────────────────────────────────────────────

def test_complete_milestone_with_evidence_and_rating(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    ms_id = sign['milestones'][0]['id']
    r = client.patch(f'/journeys/me/milestones/{ms_id}/done', headers=H(student_token['token']), json={
        'evidence': 'Đã đọc 3 bài viết về SE trên TopDev + xem video roadmap.sh',
        'rating': 4,
    })
    assert r.status_code == 200
    assert r.json()['state'] == 'done'
    assert r.json()['completion_rating'] == 4


def test_skip_milestone_with_reason(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    ms_id = sign['milestones'][1]['id']
    r = client.patch(f'/journeys/me/milestones/{ms_id}/skip', headers=H(student_token['token']), json={
        'reason': 'Không có thời gian, ưu tiên môn khác',
    })
    assert r.status_code == 200
    assert r.json()['state'] == 'skipped'


def test_complete_count_updates(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    ms_ids = [m['id'] for m in sign['milestones']]
    client.patch(f'/journeys/me/milestones/{ms_ids[0]}/done', headers=H(student_token['token']), json={'rating': 5})
    client.patch(f'/journeys/me/milestones/{ms_ids[1]}/done', headers=H(student_token['token']), json={'rating': 3})

    r = client.get('/journeys/me/active', headers=H(student_token['token']))
    j = r.json()['active_journey']
    assert j['completed_count'] == 2
    assert j['total_milestones'] == 4


def test_other_student_cannot_complete_my_milestone(client, student_token, career_paths, db):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    ms_id = sign['milestones'][0]['id']

    sv_b = models.User(
        username='sv_j02', email='svj2@x.com', full_name='SV B',
        role='student', password_hash=_hash_password('Test@1234'), is_first_login=False,
    )
    db.add(sv_b); db.commit()
    tok_b = client.post('/auth/login', json={'username':'sv_j02','password':'Test@1234'}).json()['access_token']

    r = client.patch(f'/journeys/me/milestones/{ms_id}/done', headers=H(tok_b), json={'rating': 5})
    assert r.status_code == 403


def test_rating_validation(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    ms_id = sign['milestones'][0]['id']
    r = client.patch(f'/journeys/me/milestones/{ms_id}/done', headers=H(student_token['token']), json={'rating': 6})
    assert r.status_code == 400


# ── Close journey ─────────────────────────────────────────────────────────

def test_close_with_chosen_outcome_sets_user_career_choice(client, student_token, career_paths, db):
    """Outcome=chosen → auto-set user_career_choice.primary."""
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se', 'data']}).json()
    jid = sign['id']
    r = client.post(f'/journeys/me/{jid}/close', headers=H(student_token['token']), json={
        'outcome': 'chosen',
        'chosen_career': 'se',
        'final_reflection': 'Em chọn SE vì hợp với tính cách và đã thử thấy hợp.',
    })
    assert r.status_code == 200
    assert r.json()['state'] == 'completed_chosen'
    assert r.json()['chosen_career'] == 'se'

    # Verify user_career_choice updated
    choice = db.query(models.UserCareerChoice).filter(
        models.UserCareerChoice.user_id == student_token['id']
    ).first()
    assert choice is not None
    se_path = db.query(models.CareerPath).filter(models.CareerPath.code == 'se').first()
    assert choice.primary_path_id == se_path.id


def test_close_with_explore_more(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    jid = sign['id']
    r = client.post(f'/journeys/me/{jid}/close', headers=H(student_token['token']), json={
        'outcome': 'explore_more',
        'final_reflection': 'Chưa chắc, muốn thử thêm Data và MMT.',
    })
    assert r.status_code == 200
    assert r.json()['state'] == 'completed_explore_more'


def test_close_chosen_requires_chosen_career(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    jid = sign['id']
    r = client.post(f'/journeys/me/{jid}/close', headers=H(student_token['token']), json={
        'outcome': 'chosen',
        # missing chosen_career
        'final_reflection': '...',
    })
    assert r.status_code == 400


def test_close_invalid_outcome_rejected(client, student_token, career_paths):
    sign = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    jid = sign['id']
    r = client.post(f'/journeys/me/{jid}/close', headers=H(student_token['token']), json={
        'outcome': 'invalid_outcome',
    })
    assert r.status_code == 400


def test_after_close_can_start_new_journey(client, student_token, career_paths):
    sign1 = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']}).json()
    client.post(f'/journeys/me/{sign1["id"]}/close', headers=H(student_token['token']), json={
        'outcome': 'explore_more',
        'final_reflection': '...',
    })
    sign2 = client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['data']})
    assert sign2.status_code == 201


# ── Advisor view ───────────────────────────────────────────────────────────

def test_advisor_sees_assigned_student_journey(client, student_token, advisor_user, career_paths, db):
    db.add(models.AdvisorAssignment(advisor_id=advisor_user['id'], student_id=student_token['id']))
    db.commit()
    client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']})

    r = client.get(f'/advisor/students/{student_token["id"]}/journey', headers=H(advisor_user['token']))
    assert r.status_code == 200
    assert r.json()['active_journey'] is not None


def test_advisor_blocked_for_unassigned_student(client, student_token, advisor_user, career_paths):
    client.post('/journeys/me', headers=H(student_token['token']), json={'candidate_careers': ['se']})
    r = client.get(f'/advisor/students/{student_token["id"]}/journey', headers=H(advisor_user['token']))
    assert r.status_code == 403
