import app as app_module
import auth
import supabase_coaching
from threading import Barrier
from test_app import client  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def test_student_coaching_uses_postgres_without_sqlite_fallback(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    student = profile_for('student.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    calls = []
    def rpc(_url, _key, token, name, payload):
        calls.append((token, name, payload))
        return {'id': 5, 'kind': 'goal', 'title': payload.get('p_title')} if name == 'coaching_create' else []
    monkeypatch.setattr(supabase_coaching, 'call', rpc)
    headers = {'Authorization': 'Bearer token'}
    response = client.post(f"/api/students/{student['id']}/coaching", headers=headers,
                           json={'kind': 'goal', 'title': ' Practice SQL ', 'visibility': 'mentor'})
    assert response.status_code == 201
    assert calls[0][0:2] == ('token', 'coaching_create')
    assert calls[0][2]['p_title'] == 'Practice SQL'
    assert calls[0][2]['p_visibility'] == 'student'
    assert app_module.collaboration.list_records(app_module.HISTORY_DATABASE_PATH, student['id'], include_private=True) == []


def test_student_cannot_send_private_note_or_invalid_date_to_postgres(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    student = profile_for('student.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    def forbidden_rpc(*args):
        raise AssertionError('Invalid input must not reach Postgres')
    monkeypatch.setattr(supabase_coaching, 'call', forbidden_rpc)
    headers = {'Authorization': 'Bearer token'}
    assert client.post(f"/api/students/{student['id']}/coaching", headers=headers, json={'kind': 'note', 'title': 'Private'}).status_code == 403
    assert client.post(f"/api/students/{student['id']}/coaching", headers=headers, json={'kind': 'goal', 'title': 'Goal', 'due_date': 'bad'}).status_code == 400


def test_mentor_from_other_cohort_is_denied_before_database_call(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    student = next(row for row in auth.list_users(app_module.AUTH_DATABASE_PATH) if row['username'] == 'student.b')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    def forbidden_rpc(_url, _key, _token, name, _payload):
        if name == 'mentor_assignment_mine':
            return {'students': []}
        raise AssertionError('Unassigned cross-cohort coaching must not reach Postgres')
    monkeypatch.setattr(supabase_coaching, 'call', forbidden_rpc)
    assert client.get(f"/api/students/{student['id']}/coaching", headers={'Authorization': 'Bearer token'}).status_code == 403


def test_postgres_outage_reports_error_without_silently_reading_sqlite(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    student = profile_for('student.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    def outage(*args):
        raise supabase_coaching.CoachingUnavailable()
    monkeypatch.setattr(supabase_coaching, 'call', outage)
    response = client.get(f"/api/students/{student['id']}/coaching", headers={'Authorization': 'Bearer token'})
    assert response.status_code == 503


def test_admin_roster_preserves_available_timelines_when_one_is_denied(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('admin')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda name, payload: {'assignments': []})
    users = auth.list_users(app_module.AUTH_DATABASE_PATH)
    a = next(user for user in users if user['username'] == 'student.a')
    b = next(user for user in users if user['username'] == 'student.b')
    monkeypatch.setattr(app_module.collaboration, 'latest_students', lambda *args, **kwargs: [
        {'user_id': a['id'], 'cohort': a['cohort']}, {'user_id': b['id'], 'cohort': b['cohort']},
    ])
    monkeypatch.setattr(app_module.collaboration, 'audit', lambda *args, **kwargs: None)
    def list_records(student_id, **kwargs):
        if student_id == b['id']:
            raise supabase_coaching.CoachingForbidden()
        return [{'kind': 'check_in', 'title': 'Meeting'}]
    monkeypatch.setattr(app_module, '_coaching_list', list_records)
    response = client.get('/api/mentor/students', headers={'Authorization': 'Bearer token'})
    assert response.status_code == 200
    rows = response.get_json()['data']
    assert rows[0]['coaching_records'][0]['title'] == 'Meeting'
    assert rows[0]['cohort_mentors'][0]['display_name'] == 'Mentor A'
    assert rows[1]['coaching_records'] is None and rows[1]['coaching_available'] is False


def test_mentor_roster_fails_closed_when_postgres_denies_access(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    mentor = profile_for('mentor.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_mentor_assigned_ids', lambda: set())
    monkeypatch.setattr(app_module.collaboration, 'latest_students', lambda *args, **kwargs: [
        {'user_id': 1, 'cohort': mentor['cohort']},
    ])
    monkeypatch.setattr(app_module.collaboration, 'audit', lambda *args, **kwargs: None)
    def denied(*args, **kwargs):
        raise supabase_coaching.CoachingForbidden()
    monkeypatch.setattr(app_module, '_coaching_list', denied)
    response = client.get('/api/mentor/students', headers={'Authorization': 'Bearer token'})
    assert response.status_code == 503


def test_mentor_roster_fetches_timelines_concurrently_with_user_token(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    mentor = profile_for('mentor.a')
    students = [user for user in auth.list_users(app_module.AUTH_DATABASE_PATH)
                if user['username'] in {'student.a', 'student.a2'}]
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_mentor_assigned_ids', lambda: set())
    monkeypatch.setattr(app_module.collaboration, 'latest_students', lambda *args, **kwargs: [
        {'user_id': user['id'], 'cohort': mentor['cohort']} for user in students
    ])
    monkeypatch.setattr(app_module.collaboration, 'audit', lambda *args, **kwargs: None)
    barrier = Barrier(2, timeout=3)
    calls = []

    def timeline(student_id, *, include_private, access_token):
        calls.append((student_id, access_token))
        barrier.wait()
        return [{'kind': 'goal', 'title': str(student_id)}]

    monkeypatch.setattr(app_module, '_coaching_list', timeline)
    response = client.get('/api/mentor/students', headers={'Authorization': 'Bearer user-token'})
    assert response.status_code == 200
    rows = response.get_json()['data']
    assert {row['user_id'] for row in rows} == {user['id'] for user in students}
    assert all(row['coaching_available'] and row['coaching_records'][0]['kind'] == 'goal' for row in rows)
    assert {token for _, token in calls} == {'user-token'}


def test_mentor_roster_parallel_failure_does_not_return_partial_data(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    mentor = profile_for('mentor.a')
    students = [user for user in auth.list_users(app_module.AUTH_DATABASE_PATH)
                if user['username'] in {'student.a', 'student.a2'}]
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_mentor_assigned_ids', lambda: set())
    monkeypatch.setattr(app_module.collaboration, 'latest_students', lambda *args, **kwargs: [
        {'user_id': user['id'], 'cohort': mentor['cohort']} for user in students
    ])
    monkeypatch.setattr(app_module.collaboration, 'audit', lambda *args, **kwargs: None)

    def timeline(student_id, **kwargs):
        if student_id == students[0]['id']:
            raise supabase_coaching.CoachingUnavailable()
        return [{'kind': 'goal', 'title': 'Private test goal'}]

    monkeypatch.setattr(app_module, '_coaching_list', timeline)
    response = client.get('/api/mentor/students', headers={'Authorization': 'Bearer user-token'})
    assert response.status_code == 503
    assert 'data' not in response.get_json()
