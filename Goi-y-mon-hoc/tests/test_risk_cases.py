"""Tests cho Luồng 1: Graduation Risk Management.

Cover:
- risk_engine: feature extraction, rule scoring, predicted grad term
- /risk/me, /advisor/risk-summary endpoints
- Case lifecycle: open → in_progress → resolved
- /cases/queue, /cases/me, /cases/{id}, comments, actions
- Permission boundaries (SV không xem được case của SV khác)
- Background snapshot job
"""
from __future__ import annotations
import pytest
from backend.db import models
from backend.main import _hash_password
from backend.core import risk_engine


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def advisor_token(client, db):
    adv = models.User(
        username='adv01', email='adv@x.com', full_name='Cố Vấn 01',
        role='advisor', password_hash=_hash_password('Test@1234'),
    )
    db.add(adv); db.commit()
    r = client.post('/auth/login', json={'username':'adv01','password':'Test@1234'})
    return r.json()['access_token'], adv.id


@pytest.fixture()
def admin_token(client, db):
    ad = models.User(
        username='admin01', email='ad@x.com', full_name='Admin',
        role='admin', password_hash=_hash_password('Test@1234'),
    )
    db.add(ad); db.commit()
    r = client.post('/auth/login', json={'username':'admin01','password':'Test@1234'})
    return r.json()['access_token']


def _make_student(db, code, spec='7480201_07', tc=None):
    sv = models.User(
        username=code, email=f'{code}@x.com', full_name=f'SV {code}',
        role='student', specialization=spec, password_hash=_hash_password('x'),
        official_earned_credits=tc, is_first_login=False,
    )
    db.add(sv); db.commit()
    return sv


def _student_token(client, db, code):
    sv = db.query(models.User).filter(models.User.username == code).first()
    if not sv:
        sv = _make_student(db, code)
    # Reset password để login được
    sv.password_hash = _hash_password('Test@1234')
    sv.is_first_login = False
    db.commit()
    r = client.post('/auth/login', json={'username': code, 'password': 'Test@1234'})
    return r.json()['access_token'], sv.id


def _add_grade(db, user_id, code, term, score10, credits=3):
    if not db.query(models.Course).filter(models.Course.course_code == code).first():
        db.add(models.Course(
            course_code=code, course_name=f'Mon {code}', credits=credits,
            count_toward_credits=True,
        ))
        db.flush()
    score4 = (
        4.0 if score10 >= 9.0 else 3.7 if score10 >= 8.5 else 3.5 if score10 >= 8.0
        else 3.0 if score10 >= 7.0 else 2.5 if score10 >= 6.5 else 2.0 if score10 >= 5.5
        else 1.5 if score10 >= 5.0 else 1.0 if score10 >= 4.0 else 0.0
    )
    letter = 'A+' if score10 >= 9 else 'A' if score10 >= 8.5 else 'B+' if score10 >= 8 else 'B' if score10 >= 7 else 'C+' if score10 >= 6.5 else 'C' if score10 >= 5.5 else 'D+' if score10 >= 5 else 'D' if score10 >= 4 else 'F'
    db.add(models.UserGrade(
        user_id=user_id, course_code=code, term=term,
        score10=score10, score4=score4, letter=letter,
        passed=score10 >= 4.0,
    ))
    db.commit()


def _assign(db, advisor_id, student_id):
    if not db.query(models.AdvisorAssignment).filter_by(
        advisor_id=advisor_id, student_id=student_id
    ).first():
        db.add(models.AdvisorAssignment(advisor_id=advisor_id, student_id=student_id))
        db.commit()


def _setup_high_risk_grades(db, sv_id, prefix='70800'):
    """Setup grade pattern guaranteed to score above RISK_THRESHOLD_OPEN_CASE (0.60).

    4 main terms với GPA D (1.0) + 2 môn F chưa qua → pace + low_gpa + unrecovered_fails.
    """
    for i, term in enumerate(['HK1/2022-2023','HK2/2022-2023','HK1/2023-2024','HK2/2023-2024']):
        _add_grade(db, sv_id, f'{prefix}{i:02d}', term, 4.5, credits=3)
    # 2 môn F chưa qua (failed_unrecovered)
    _add_grade(db, sv_id, f'{prefix}90', 'HK2/2023-2024', 3.0, credits=3)
    _add_grade(db, sv_id, f'{prefix}91', 'HK2/2023-2024', 2.0, credits=3)


# ── 1. Risk engine unit tests ────────────────────────────────────────────────

def test_term_sort_key_handles_short_format():
    assert risk_engine._term_sort_key('HK1/2024-2025') == (2024, 1)
    assert risk_engine._term_sort_key('HK2/2024-2025') == (2024, 2)
    assert risk_engine._term_sort_key('HK3/2024-2025') == (2024, 3)


def test_term_sort_key_handles_long_format():
    assert risk_engine._term_sort_key('Học kỳ 1 - Năm học 2024-2025') == (2024, 1)
    assert risk_engine._term_sort_key('Học kỳ 2 - Năm học 2023-2024') == (2023, 2)


def test_term_sort_key_handles_invalid():
    assert risk_engine._term_sort_key('') == (0, 0)
    assert risk_engine._term_sort_key('garbage') == (0, 0)
    assert risk_engine._term_sort_key(None) == (0, 0)


def test_is_main_term():
    assert risk_engine._is_main_term('HK1/2024-2025') is True
    assert risk_engine._is_main_term('HK2/2024-2025') is True
    assert risk_engine._is_main_term('HK3/2024-2025') is False  # summer


def test_extract_features_low_risk_student(client, db):
    """SV mới học 1 kỳ, GPA cao → risk thấp."""
    sv = _make_student(db, '2400000001')
    _add_grade(db, sv.id, '7080001', 'HK1/2024-2025', 9.0, credits=3)
    _add_grade(db, sv.id, '7080002', 'HK1/2024-2025', 8.5, credits=3)

    f = risk_engine.extract_features(db, sv.id)
    assert f.main_terms_studied == 1
    assert f.gpa4 is not None and f.gpa4 >= 3.5
    assert f.failed_unrecovered == 0


def test_extract_features_high_risk_student(client, db):
    """SV học 4 kỳ nhưng TC chậm + GPA thấp → risk cao."""
    sv = _make_student(db, '2200000099')
    # 4 kỳ, mỗi kỳ chỉ pass 1 môn 3 TC → 12 TC sau 4 kỳ (kỳ vọng ~76 TC)
    for i, term in enumerate(['HK1/2022-2023','HK2/2022-2023','HK1/2023-2024','HK2/2023-2024']):
        _add_grade(db, sv.id, f'70800{i+1:02d}', term, 4.5, credits=3)  # D điểm thấp

    f = risk_engine.extract_features(db, sv.id)
    assert f.main_terms_studied == 4
    assert f.pace_ratio < 0.5  # chậm tiến độ
    assert f.gpa4 is not None and f.gpa4 < 2.0


def test_score_rule_based_returns_factors():
    """Rule-based scoring trả về list factor không rỗng cho high risk."""
    f = risk_engine.RiskFeatures(
        earned_credits=20, expected_credits=76, credits_pct=0.13,
        main_terms_studied=4, summer_terms_studied=0,
        gpa4=1.5, gpa4_recent_2=1.4, gpa4_trend=-0.3,
        failed_count=2, failed_unrecovered=2, retake_count=1,
        pace_ratio=0.26,
        on_internship_eligible=False, on_thesis_eligible=False,
    )
    score, factors = risk_engine.score_rule_based(f)
    assert score > 0.5
    assert len(factors) > 0
    # Top factor phải là GPA quá thấp HOẶC pace chậm
    factor_codes = {fac['code'] for fac in factors}
    assert 'low_gpa' in factor_codes or 'slow_credits' in factor_codes


def test_score_rule_based_low_risk_short_history():
    """SV mới 1 kỳ → engine không penalty pace (chưa đủ data)."""
    f = risk_engine.RiskFeatures(
        earned_credits=15, expected_credits=19,
        credits_pct=0.10, main_terms_studied=1, summer_terms_studied=0,
        gpa4=3.2, gpa4_recent_2=None, gpa4_trend=None,
        failed_count=0, failed_unrecovered=0, retake_count=0,
        pace_ratio=0.79,
        on_internship_eligible=False, on_thesis_eligible=False,
    )
    score, factors = risk_engine.score_rule_based(f)
    assert score < 0.4  # low risk


def test_predict_risk_for_student_returns_full_dict(client, db):
    """End-to-end: predict_risk_for_student trả về dict hoàn chỉnh."""
    sv = _make_student(db, '2400000010')
    _add_grade(db, sv.id, '7080010', 'HK1/2024-2025', 8.0)

    r = risk_engine.predict_risk_for_student(db, sv.id)
    assert 'risk_score' in r
    assert 0.0 <= r['risk_score'] <= 1.0
    assert 'level' in r and r['level'] in ('high', 'medium', 'low')
    assert 'factors' in r
    assert 'predicted_grad_term' in r


def test_predict_risk_rejects_non_student(client, db):
    """Không cho predict cho user role != student."""
    adv = models.User(
        username='advt01', email='advt@x.com', full_name='Adv',
        role='advisor', password_hash=_hash_password('x'),
    )
    db.add(adv); db.commit()
    with pytest.raises(ValueError):
        risk_engine.extract_features(db, adv.id)


# ── 2. /risk/me endpoint ─────────────────────────────────────────────────────

def test_risk_me_returns_score_for_student(client, db):
    token, sv_id = _student_token(client, db, '2400000020')
    _add_grade(db, sv_id, '7080020', 'HK1/2024-2025', 8.0)

    r = client.get('/risk/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    data = r.json()
    assert 'risk_score' in data
    assert 'level' in data
    assert 'factors' in data


def test_risk_me_forbidden_for_advisor(client, db, advisor_token):
    """Advisor không có /risk/me — chỉ student."""
    token, _ = advisor_token
    r = client.get('/risk/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 403


# ── 3. /advisor/risk-summary ────────────────────────────────────────────────

def test_advisor_risk_summary_lists_assigned_students(client, db, advisor_token):
    """Advisor chỉ thấy SV của mình trong risk-summary."""
    adv_token, adv_id = advisor_token
    sv1 = _make_student(db, '2400000030')
    sv2 = _make_student(db, '2400000031')
    _add_grade(db, sv1.id, '7080030', 'HK1/2024-2025', 7.0)
    _assign(db, adv_id, sv1.id)
    # sv2 KHÔNG assigned

    r = client.get('/advisor/risk-summary', headers={'Authorization': f'Bearer {adv_token}'})
    assert r.status_code == 200
    data = r.json()
    student_ids = [item['student_id'] for item in data['items']]
    assert sv1.id in student_ids
    assert sv2.id not in student_ids


def test_advisor_risk_summary_blocked_for_student(client, db):
    token, _ = _student_token(client, db, '2400000040')
    r = client.get('/advisor/risk-summary', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 403


# ── 4. Case lifecycle ───────────────────────────────────────────────────────

def test_snapshot_job_creates_case_for_high_risk(client, db, advisor_token):
    """Snapshot job phát hiện SV high risk → tự tạo case state=open."""
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token

    sv = _make_student(db, '2200000050')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70811')

    result = _run_risk_snapshot_job(db)
    assert result['cases_opened'] >= 1

    # Verify case tồn tại với state=open + advisor_id auto-assigned
    case = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv.id).first()
    assert case is not None
    assert case.state == 'open'
    assert case.advisor_id == adv_id
    assert case.opened_risk_score is not None and float(case.opened_risk_score) >= risk_engine.RISK_THRESHOLD_OPEN_CASE


def test_snapshot_job_no_duplicate_case_when_already_open(client, db, advisor_token):
    """Job chạy lại không tạo case mới nếu đã có case open cho SV."""
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000051')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70821')

    r1 = _run_risk_snapshot_job(db)
    r2 = _run_risk_snapshot_job(db)
    cases = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv.id).all()
    # Run lần 2 không tạo case mới — chỉ update existing
    assert len(cases) == 1


# ── 5. Cases queue + permissions ────────────────────────────────────────────

def test_cases_queue_returns_open_cases_for_advisor(client, db, advisor_token):
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000060')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70831')
    _run_risk_snapshot_job(db)

    r = client.get('/cases/queue', headers={'Authorization': f'Bearer {adv_token}'})
    assert r.status_code == 200
    cases = r.json()
    assert len(cases) >= 1
    assert cases[0]['student']['id'] == sv.id


def test_cases_me_returns_student_own_cases(client, db, advisor_token):
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000070')
    sv.password_hash = _hash_password('Test@1234')
    db.commit()
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70841')
    _run_risk_snapshot_job(db)

    sv_login = client.post('/auth/login', json={'username':'2200000070','password':'Test@1234'})
    token = sv_login.json()['access_token']
    r = client.get('/cases/me', headers={'Authorization': f'Bearer {token}'})
    assert r.status_code == 200
    data = r.json()
    assert len(data['open']) >= 1
    assert data['open'][0]['student']['id'] == sv.id


def test_student_cannot_view_other_student_case(client, db, advisor_token):
    """Permission: SV A không xem được case của SV B."""
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token

    sv_b = _make_student(db, '2200000080')
    _assign(db, adv_id, sv_b.id)
    _setup_high_risk_grades(db, sv_b.id, prefix='70851')
    _run_risk_snapshot_job(db)
    case_b = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv_b.id).first()
    assert case_b is not None

    sv_a_token, _ = _student_token(client, db, '2400000081')
    r = client.get(f'/cases/{case_b.id}', headers={'Authorization': f'Bearer {sv_a_token}'})
    assert r.status_code == 403


# ── 6. Case state transitions + actions + comments ──────────────────────────

def test_advisor_can_change_case_state(client, db, advisor_token):
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000090')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70861')
    _run_risk_snapshot_job(db)
    case = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv.id).first()

    H = {'Authorization': f'Bearer {adv_token}'}
    r = client.post(f'/cases/{case.id}/state', headers=H, json={'state': 'in_progress'})
    assert r.status_code == 200
    assert r.json()['state'] == 'in_progress'

    r2 = client.post(f'/cases/{case.id}/state', headers=H, json={'state': 'resolved', 'reason': 'GPA cải thiện'})
    assert r2.status_code == 200
    assert r2.json()['state'] == 'resolved'
    assert r2.json()['close_reason'] == 'GPA cải thiện'


def test_advisor_can_add_action_and_comment(client, db, advisor_token):
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000091')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70871')
    _run_risk_snapshot_job(db)
    case = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv.id).first()
    H = {'Authorization': f'Bearer {adv_token}'}

    # Add action
    a = client.post(f'/cases/{case.id}/actions', headers=H, json={
        'action_type': 'meeting',
        'title': 'Gặp SV thảo luận tuần tới',
        'assigned_to': adv_id,
    })
    assert a.status_code == 200
    action_id = a.json()['id']

    # Add comment
    c = client.post(f'/cases/{case.id}/comments', headers=H, json={'content': 'Đã liên hệ qua Zalo.'})
    assert c.status_code == 200
    assert c.json()['content'] == 'Đã liên hệ qua Zalo.'

    # Mark action done
    d = client.patch(f'/cases/actions/{action_id}/done', headers=H, json={'note': 'Đã gặp 12/4'})
    assert d.status_code == 200
    assert d.json()['state'] == 'done'

    # Adding action auto-changes state from open → in_progress
    detail = client.get(f'/cases/{case.id}', headers=H).json()
    assert detail['state'] == 'in_progress'


def test_invalid_state_transition_rejected(client, db, advisor_token):
    from backend.main import _run_risk_snapshot_job
    adv_token, adv_id = advisor_token
    sv = _make_student(db, '2200000092')
    _assign(db, adv_id, sv.id)
    _setup_high_risk_grades(db, sv.id, prefix='70881')
    _run_risk_snapshot_job(db)
    case = db.query(models.RiskCase).filter(models.RiskCase.student_id == sv.id).first()

    H = {'Authorization': f'Bearer {adv_token}'}
    r = client.post(f'/cases/{case.id}/state', headers=H, json={'state': 'invalid_state'})
    assert r.status_code == 400
