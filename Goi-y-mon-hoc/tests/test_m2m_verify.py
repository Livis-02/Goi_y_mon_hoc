"""Quick integration test for multi-CN M2M flow."""
import pytest
from backend.db import models
from backend.main import _hash_password


@pytest.fixture()
def admin_token(client, db):
    admin = models.User(
        username='admintest', email='at@example.com',
        full_name='Admin Test', role='admin',
        password_hash=_hash_password('Test@1234'),
    )
    db.add(admin)
    db.commit()
    r = client.post('/auth/login', json={'username':'admintest','password':'Test@1234'})
    assert r.status_code == 200
    return r.json()['access_token']


def test_multi_cn_m2m_flow(client, admin_token):
    H = {'Authorization': f'Bearer {admin_token}'}
    code = '9999999'

    # 1. Create course với 2 CN
    r = client.post('/admin/courses', headers=H, json={
        'course_code': code, 'course_name': 'Test Multi-CN', 'credits': 3,
        'specializations': ['7480201_07', '7480201_06'],
        'typical_semester': 5,
    })
    assert r.status_code == 200, f"Create failed: {r.json()}"
    crs_id = r.json()['id']
    assert sorted(r.json()['specializations']) == ['7480201_06', '7480201_07'], r.json()

    # 2-5. Verify visibility per spec
    r = client.get('/admin/courses/grouped?spec=7480201_07', headers=H)
    assert code in [c['course_code'] for c in r.json()['compulsory']], "KHMT missing"
    r = client.get('/admin/courses/grouped?spec=7480201_06', headers=H)
    assert code in [c['course_code'] for c in r.json()['compulsory']], "MMT missing"
    r = client.get('/admin/courses/grouped?spec=7480201_05', headers=H)
    assert code not in [c['course_code'] for c in r.json()['compulsory']], "CNPM has it (wrong)"
    r = client.get('/admin/courses/grouped?spec=common', headers=H)
    assert code not in [c['course_code'] for c in r.json()['compulsory']], "common has it (wrong)"

    # 6. Partial update — chỉ đổi HK, không gửi specializations → giữ M2M
    r = client.put(f'/admin/courses/{crs_id}', headers=H, json={
        'course_code': code, 'course_name': 'Test Multi-CN', 'credits': 3,
        'typical_semester': 7,
    })
    assert r.status_code == 200
    assert sorted(r.json()['specializations']) == ['7480201_06', '7480201_07'], \
        f"Specs lost after partial update: {r.json()}"

    # 7. After partial update, both still see it
    r = client.get('/admin/courses/grouped?spec=7480201_07', headers=H)
    assert code in [c['course_code'] for c in r.json()['compulsory']]
    r = client.get('/admin/courses/grouped?spec=7480201_06', headers=H)
    assert code in [c['course_code'] for c in r.json()['compulsory']]

    # 8. Single-CN update via specializations
    r = client.put(f'/admin/courses/{crs_id}', headers=H, json={
        'course_code': code, 'course_name': 'Test Multi-CN', 'credits': 3,
        'typical_semester': 7,
        'specializations': ['7480201_07'],
    })
    assert r.status_code == 200
    assert r.json()['specializations'] == ['7480201_07']
    assert r.json()['required_specialization'] == '7480201_07'

    # 9. MMT no longer has it
    r = client.get('/admin/courses/grouped?spec=7480201_06', headers=H)
    assert code not in [c['course_code'] for c in r.json()['compulsory']]

    # 10. Empty specs → common
    r = client.put(f'/admin/courses/{crs_id}', headers=H, json={
        'course_code': code, 'course_name': 'Test Multi-CN', 'credits': 3,
        'typical_semester': 7, 'specializations': [],
    })
    assert r.status_code == 200
    assert r.json()['specializations'] == []
    assert r.json()['required_specialization'] is None

    r = client.get('/admin/courses/grouped?spec=common', headers=H)
    assert code in [c['course_code'] for c in r.json()['compulsory']], "Should appear in common after [] specs"
