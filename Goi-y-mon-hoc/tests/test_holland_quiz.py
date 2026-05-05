"""Test Holland quiz endpoints."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def sv_token(client, db):
    sv = models.User(username='sv_q', email='q@x.c', full_name='SV Quiz',
                    role='student', password_hash=_hash_password('Test@1234'))
    db.add(sv); db.commit()
    r = client.post('/auth/login', json={'username':'sv_q','password':'Test@1234'})
    return r.json()['access_token']


def test_holland_questions_public(client):
    """Endpoint /quiz/holland/questions không cần auth."""
    r = client.get('/quiz/holland/questions')
    assert r.status_code == 200
    d = r.json()
    assert len(d['questions']) == 12
    assert all('id' in q and 'type' in q and 'text' in q for q in d['questions'])
    types = set(q['type'] for q in d['questions'])
    assert types == {'R','I','A','S','E','C'}
    assert len(d['scale']) == 5


def test_holland_submit_invalid(client, sv_token):
    H = {'Authorization': f'Bearer {sv_token}'}
    # Thiếu câu trả lời
    r = client.post('/quiz/holland/submit', headers=H, json={'answers': [{'q':1,'a':3}]})
    assert r.status_code == 400


def test_holland_submit_valid(client, db, sv_token):
    """Submit 12 câu valid → trả RIASEC scores + suggested paths."""
    # Seed 1 path để verify suggestion
    db.add(models.CareerPath(code='ml_engineer', name='ML Engineer',
                              short_description='Xây dựng mô hình ML', icon='psychology', color='indigo'))
    db.commit()

    H = {'Authorization': f'Bearer {sv_token}'}
    # Tạo answers: ưu thế I (Investigative) — câu 2,8 (type I) chọn 5
    answers = []
    for q in range(1, 13):
        if q in (2, 8):  # I-type
            answers.append({'q': q, 'a': 5})
        elif q in (1, 7):  # R
            answers.append({'q': q, 'a': 4})
        else:
            answers.append({'q': q, 'a': 2})
    r = client.post('/quiz/holland/submit', headers=H, json={'answers': answers})
    assert r.status_code == 200
    d = r.json()
    assert d['riasec_scores']['I'] == 10  # 2 câu × 5
    assert d['riasec_scores']['R'] == 8   # 2 câu × 4
    assert d['primary_codes'][0] == 'I'
    assert d['primary_codes'][1] == 'R'
    # Có suggested path nếu trong DB có path map với I
    codes = [p['code'] for p in d['suggested_paths']]
    assert 'ml_engineer' in codes


def test_holland_get_me(client, db, sv_token):
    H = {'Authorization': f'Bearer {sv_token}'}
    # Trước khi submit
    r = client.get('/quiz/holland/me', headers=H)
    assert r.status_code == 200
    assert r.json()['taken'] is False

    # Submit
    answers = [{'q': i, 'a': 3} for i in range(1, 13)]
    client.post('/quiz/holland/submit', headers=H, json={'answers': answers})
    # Sau khi submit
    r2 = client.get('/quiz/holland/me', headers=H)
    d = r2.json()
    assert d['taken'] is True
    assert 'riasec_scores' in d
    assert sum(d['riasec_scores'].values()) == 36  # 12 câu × 3


def test_holland_admin_cannot_submit(client, db):
    admin = models.User(username='aq', email='aq@x.c', full_name='A',
                       role='admin', password_hash=_hash_password('x'))
    db.add(admin); db.commit()
    rt = client.post('/auth/login', json={'username':'aq','password':'x'}).json()['access_token']
    H = {'Authorization': f'Bearer {rt}'}
    answers = [{'q': i, 'a': 3} for i in range(1, 13)]
    r = client.post('/quiz/holland/submit', headers=H, json={'answers': answers})
    assert r.status_code == 403
