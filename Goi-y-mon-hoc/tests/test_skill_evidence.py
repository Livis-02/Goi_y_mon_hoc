"""Tests cho skill evidence + skill resources endpoints (Evidence-based skill tree)."""
from __future__ import annotations
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def setup(client, db):
    """Tạo SV + admin + 1 skill PYTHON."""
    sv = models.User(username='svev', email='svev@x.c', full_name='SV',
                    role='student', specialization='7480201_07',
                    password_hash=_hash_password('Test@1234'), is_first_login=False)
    admin = models.User(username='admev', email='ad@x.c', full_name='Admin',
                       role='admin', password_hash=_hash_password('Test@1234'),
                       is_first_login=False)
    db.add_all([sv, admin])
    db.commit()

    # Skill
    db.add(models.Skill(code='PYTHON', name='Python', category='programming'))
    db.commit()

    sv_token = client.post('/auth/login', json={'username':'svev','password':'Test@1234'}).json()['access_token']
    ad_token = client.post('/auth/login', json={'username':'admev','password':'Test@1234'}).json()['access_token']

    return {
        'sv_id': sv.id, 'sv_token': sv_token,
        'admin_id': admin.id, 'admin_token': ad_token,
    }


def H(t): return {'Authorization': f'Bearer {t}'}


# ── Skill evidence (SV) ────────────────────────────────────────────────────

def test_sv_can_add_github_evidence(client, setup):
    r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github',
        'url': 'https://github.com/em/python-projects',
        'label': 'Python practice projects',
        'description': '5 projects học Python trong 3 tháng',
    })
    assert r.status_code == 201
    data = r.json()
    assert data['type'] == 'github'
    assert data['url'] == 'https://github.com/em/python-projects'
    assert data['label'] == 'Python practice projects'
    assert data['verified'] is False


def test_sv_can_add_certificate_without_url(client, setup):
    """Certificate có thể không có URL (paper cert)."""
    r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'certificate',
        'label': 'Coursera Python for Everybody',
    })
    assert r.status_code == 201


def test_invalid_type_rejected(client, setup):
    r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'invalid_type',
        'label': 'x',
    })
    assert r.status_code == 400


def test_empty_label_rejected(client, setup):
    r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': '   ',
    })
    assert r.status_code == 400


def test_invalid_url_rejected(client, setup):
    r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'x', 'url': 'not-a-url',
    })
    assert r.status_code == 400


def test_unknown_skill_rejected(client, setup):
    r = client.post('/skills/UNKNOWN/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'x',
    })
    assert r.status_code == 404


def test_advisor_cannot_add_evidence(client, db, setup):
    adv = models.User(username='advev', email='adv@x.c', full_name='Adv',
                      role='advisor', password_hash=_hash_password('x'))
    db.add(adv); db.commit()
    tok = client.post('/auth/login', json={'username':'advev','password':'x'}).json()['access_token']
    r = client.post('/skills/PYTHON/evidence', headers=H(tok), json={
        'type': 'github', 'label': 'x',
    })
    assert r.status_code == 403


def test_evidence_limit_10_per_skill(client, setup):
    for i in range(10):
        r = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
            'type': 'github', 'label': f'Project {i}',
        })
        assert r.status_code == 201
    r11 = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'Project 11',
    })
    assert r11.status_code == 409


def test_sv_can_delete_own_evidence(client, setup):
    add = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'x',
    })
    eid = add.json()['id']
    r = client.delete(f'/skills/evidence/{eid}', headers=H(setup['sv_token']))
    assert r.status_code == 200
    assert r.json()['deleted'] is True


def test_sv_cannot_delete_other_evidence(client, db, setup):
    add = client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'x',
    })
    eid = add.json()['id']
    sv2 = models.User(username='sv2', email='sv2@x.c', full_name='SV2',
                      role='student', password_hash=_hash_password('x'),
                      is_first_login=False)
    db.add(sv2); db.commit()
    tok2 = client.post('/auth/login', json={'username':'sv2','password':'x'}).json()['access_token']
    r = client.delete(f'/skills/evidence/{eid}', headers=H(tok2))
    assert r.status_code == 403


def test_evidence_appears_in_skill_tree(client, db, setup):
    # Career path + required PYTHON
    p = models.CareerPath(code='se_test', name='SE Test', icon='code', color='indigo')
    db.add(p); db.commit()
    db.add(models.CareerPathSkill(path_id=p.id, skill_code='PYTHON', importance=1.0))
    db.commit()

    # SV chưa pass course PYTHON → status no_evidence
    r1 = client.get('/me/skill-tree?career_code=se_test', headers=H(setup['sv_token']))
    skills1 = {s['code']: s for s in r1.json()['skills']}
    assert skills1['PYTHON']['status'] == 'no_evidence'

    # Add personal evidence
    client.post('/skills/PYTHON/evidence', headers=H(setup['sv_token']), json={
        'type': 'github', 'label': 'Python repo',
    })

    # Now status = evidenced
    r2 = client.get('/me/skill-tree?career_code=se_test', headers=H(setup['sv_token']))
    skills2 = {s['code']: s for s in r2.json()['skills']}
    assert skills2['PYTHON']['status'] == 'evidenced'
    assert len(skills2['PYTHON']['evidence_personal']) == 1

