"""Verify delete advisor với transfer SV + chức trưởng BM."""
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
    db.add(admin); db.commit()
    r = client.post('/auth/login', json={'username':'admintest','password':'Test@1234'})
    return r.json()['access_token']


def _make_advisor(db, code, name, spec, is_head=False):
    a = models.User(
        username=code, email=f'{code}@x.com',
        full_name=name, role='advisor',
        teacher_code=code, managed_specialization=spec,
        is_head_of_department=is_head,
        password_hash=_hash_password('x'),
    )
    db.add(a); db.commit()
    return a


def _make_sv(db, code):
    sv = models.User(
        username=code, email=f'{code}@x.com',
        full_name='SV Test', role='student',
        password_hash=_hash_password('x'),
    )
    db.add(sv); db.commit()
    return sv


def test_delete_advisor_with_transfer_moves_sv_and_head(client, admin_token, db):
    """Advisor là trưởng BM + có SV → DELETE bắt buộc transfer_to + chuyển SV + chức trưởng."""
    head = _make_advisor(db, 'KHMT001', 'Trưởng BM KHMT', '7480201_07', is_head=True)
    successor = _make_advisor(db, 'KHMT002', 'Phó BM KHMT', '7480201_07', is_head=False)
    sv1 = _make_sv(db, '2400000001')
    sv2 = _make_sv(db, '2400000002')
    db.add(models.AdvisorAssignment(advisor_id=head.id, student_id=sv1.id))
    db.add(models.AdvisorAssignment(advisor_id=head.id, student_id=sv2.id))
    db.commit()

    H = {'Authorization': f'Bearer {admin_token}'}

    # Thiếu transfer_to → 400
    r = client.delete(f'/admin/advisors/{head.id}', headers=H)
    assert r.status_code == 400
    assert 'transfer' in r.json()['detail'].lower() or 'kế nhiệm' in r.json()['detail']

    # Có transfer_to → OK
    r = client.delete(f'/admin/advisors/{head.id}?transfer_to={successor.id}', headers=H)
    assert r.status_code == 200, r.json()

    # Verify successor giờ là trưởng BM + có 2 SV
    db.refresh(successor)
    assert successor.is_head_of_department == True
    assigns = db.query(models.AdvisorAssignment).filter(
        models.AdvisorAssignment.advisor_id == successor.id
    ).all()
    assert len(assigns) == 2

    # Head cũ đã xóa
    assert db.query(models.User).filter(models.User.id == head.id).first() is None


def test_delete_lone_advisor_orphans_students(client, admin_token, db):
    """Advisor duy nhất của BM → cho phép xóa, SV thành orphan."""
    only_one = _make_advisor(db, 'CNPM001', 'Chỉ 1 GV', '7480201_05', is_head=True)
    sv = _make_sv(db, '2400000003')
    db.add(models.AdvisorAssignment(advisor_id=only_one.id, student_id=sv.id))
    db.commit()

    H = {'Authorization': f'Bearer {admin_token}'}
    # Không cần transfer_to vì BM chỉ có 1 GV
    r = client.delete(f'/admin/advisors/{only_one.id}', headers=H)
    assert r.status_code == 200, r.json()

    # SV trở thành orphan
    assigns = db.query(models.AdvisorAssignment).filter(
        models.AdvisorAssignment.student_id == sv.id
    ).all()
    assert len(assigns) == 0
