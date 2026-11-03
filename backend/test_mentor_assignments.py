import pytest
import app as app_module
import auth
from test_app import client, login, csrf_headers  # noqa: F401


def ids():
    return {u['username']: u['id'] for u in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def test_admin_assignment_replace_clear_and_audit(client):
    token = login(client, 'admin')
    accounts = ids()
    url = f"/api/admin/students/{accounts['student.a']}/mentor"
    assert client.post(url, json={'mentor_id': accounts['mentor.a']}, headers=csrf_headers(token)).status_code == 200
    result = client.get('/api/admin/mentor-assignments').get_json()['data']
    assert len(result) == 1 and result[0]['mentor_id'] == accounts['mentor.a'] and result[0]['valid']
    assert client.post(url, json={'mentor_id': None}, headers=csrf_headers(token)).status_code == 200
    assert client.get('/api/admin/mentor-assignments').get_json()['data'] == []
    con = auth._connection(app_module.AUTH_DATABASE_PATH)
    try:
        assert con.execute('SELECT COUNT(*) FROM mentor_assignment_events').fetchone()[0] == 2
    finally:
        con.close()


def test_assignment_rejects_invalid_and_missing_csrf(client):
    token = login(client, 'admin')
    accounts = ids()
    url = f"/api/admin/students/{accounts['student.b']}/mentor"
    assert client.post(url, json={'mentor_id': accounts['student.a']}, headers=csrf_headers(token)).status_code == 400
    assert client.post(url, json={'mentor_id': True}, headers=csrf_headers(token)).status_code == 400
    assert client.post(url, json={'mentor_id': None}).status_code == 403
    assert client.get('/api/admin/mentor-assignments').get_json()['data'] == []


def test_cross_cohort_assignment_grants_only_the_selected_student_and_revokes(client):
    token = login(client, 'admin')
    accounts = ids()
    other = auth.create_user(app_module.AUTH_DATABASE_PATH, username='student.b2', password='CorrectHorseBattery42', display_name='Student B2', role='student', cohort='CSE-B')
    target = accounts['student.b']
    url = f'/api/admin/students/{target}/mentor'
    assert client.post(url, json={'mentor_id': accounts['mentor.a']}, headers=csrf_headers(token)).status_code == 200
    login(client, 'mentor.a')
    assert client.get(f'/api/students/{target}/coaching').status_code == 200
    assert client.get(f"/api/students/{other['id']}/coaching").status_code == 403
    roster = client.get('/api/mentor/students').get_json()['data']
    student = next(item for item in roster if item['user_id'] == target)
    assert student['assigned_mentor']['id'] == accounts['mentor.a']
    assert student['readiness_score'] is None
    token = login(client, 'admin')
    assert client.post(url, json={'mentor_id': None}, headers=csrf_headers(token)).status_code == 200
    login(client, 'mentor.a')
    assert client.get(f'/api/students/{target}/coaching').status_code == 403
    assert all(item['user_id'] != target for item in client.get('/api/mentor/students').get_json()['data'])


def test_assigned_mentor_appears_in_cohort_roster(client, monkeypatch):
    token = login(client, 'admin')
    accounts = ids()
    client.post(f"/api/admin/students/{accounts['student.a']}/mentor", json={'mentor_id': accounts['mentor.a']}, headers=csrf_headers(token))
    monkeypatch.setattr(app_module.collaboration, 'latest_students', lambda *args, **kwargs: [
        {'user_id': accounts['student.a'], 'cohort': 'CSE-A'}])
    monkeypatch.setattr(app_module, '_coaching_list', lambda *args, **kwargs: [])
    login(client, 'mentor.a')
    response = client.get('/api/mentor/students')
    assert response.status_code == 200
    assert response.get_json()['data'][0]['assigned_mentor']['id'] == accounts['mentor.a']


@pytest.mark.parametrize('user', ['student.a', 'mentor.a', 'officer'])
def test_assignment_is_admin_only(client, user):
    token = login(client, user)
    assert client.get('/api/admin/mentor-assignments').status_code == 403
    assert client.post('/api/admin/students/1/mentor', json={'mentor_id': None}, headers=csrf_headers(token)).status_code == 403


def test_supabase_admin_assignment(supabase_mode):
    client, profile_for = supabase_mode
    accounts = ids()
    profile_for('admin')
    response = client.post(f"/api/v1/admin/students/{accounts['student.a']}/mentor", json={'mentor_id': accounts['mentor.a']}, headers={'Authorization': 'Bearer token'})
    assert response.status_code == 200
    profile_for('mentor.a')
    assert client.get('/api/admin/mentor-assignments', headers={'Authorization': 'Bearer token'}).status_code == 403


def test_supabase_assignment_fails_closed_on_mismatched_student_or_outage(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    accounts = ids()
    student = accounts['student.b']
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_coaching_list', lambda *args, **kwargs: [])
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *args: {'students': [{'id': student, 'username': 'wrong', 'cohort': 'CSE-B'}]})
    headers = {'Authorization': 'Bearer token'}
    assert client.get(f'/api/students/{student}/coaching', headers=headers).status_code == 403
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *args: {'students': [{'id': student, 'username': 'student.b', 'cohort': 'CSE-B'}]})
    assert client.get(f'/api/students/{student}/coaching', headers=headers).status_code == 200
    def unavailable(*args):
        raise app_module.supabase_coaching.CoachingUnavailable()
    monkeypatch.setattr(app_module, '_coaching_rpc', unavailable)
    assert client.get(f'/api/students/{student}/coaching', headers=headers).status_code == 503


from test_supabase_app import supabase_mode  # noqa: E402,F401
