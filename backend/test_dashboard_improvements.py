import io

import app as app_module
import auth
from test_app import client, login, csrf_headers, SAMPLE_STUDENT  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401
import supabase_coaching
import history


def users():
    return {user['username']: user['id'] for user in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def test_resource_category_is_saved_and_invalid_category_is_rejected(client):
    student = users()['student.a']
    token = login(client, 'mentor.a')
    url = f'/api/students/{student}/resources'
    response = client.post(url, data={'title': 'SQL', 'category': 'Coding', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=csrf_headers(token), content_type='multipart/form-data')
    assert response.status_code == 201
    rows = client.get(url).get_json()['data']
    assert rows[0]['category'] == 'Coding'
    response = client.post(url, data={'title': 'Bad category', 'category': 'Unexpected', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=csrf_headers(token), content_type='multipart/form-data')
    assert response.status_code == 400


def test_placement_history_is_staff_only_and_keeps_each_update(client):
    student = users()['student.a']
    token = login(client, 'admin')
    for stage in ('Applied', 'Interviewing'):
        result = client.post('/api/placement-pipeline', json={'student_id': student, 'stage': stage, 'target_role': 'Developer'}, headers=csrf_headers(token))
        assert result.status_code == 200
    path = f'/api/placement-pipeline/{student}/history'
    history = client.get(path).get_json()['data']
    assert [item['stage'] for item in history] == ['Interviewing', 'Applied']
    assert all(item['updated_by'] == users()['admin'] for item in history)
    login(client, 'student.a')
    assert client.get(path).status_code == 403


def test_saved_resource_is_not_lost_when_notification_service_fails(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    def unavailable(*args, **kwargs):
        raise supabase_coaching.CoachingUnavailable('Offline')
    monkeypatch.setattr(app_module, '_coaching_rpc', unavailable)
    student = users()['student.a']
    headers = {'Authorization': 'Bearer token'}
    response = client.post(f'/api/students/{student}/resources', data={'title': 'Guide', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=headers, content_type='multipart/form-data')
    assert response.status_code == 201
    assert response.get_json()['data']['notification_sent'] is False
    assert len(client.get(f'/api/students/{student}/resources', headers=headers).get_json()['data']) == 1


def test_history_includes_changed_profiles_but_not_other_students(client):
    student = users()['student.a']
    prediction = {'readiness_score': 60, 'readiness_category': 'Developing', 'model_probability': .6}
    history.save_assessment(SAMPLE_STUDENT, prediction, app_module.HISTORY_DATABASE_PATH, user_id=student)
    changed = dict(SAMPLE_STUDENT, coding_score=80)
    history.save_assessment(changed, prediction, app_module.HISTORY_DATABASE_PATH, user_id=student)
    token = login(client, 'student.a')
    result = client.post('/api/history/query', json={'student': changed}, headers=csrf_headers(token))
    assert [row['student_profile']['coding_score'] for row in result.get_json()['data']] == [80, SAMPLE_STUDENT['coding_score']]
    token = login(client, 'student.b')
    assert client.post('/api/history/query', json={'student': changed}, headers=csrf_headers(token)).get_json()['data'] == []


def test_resource_notification_retry_is_durable_scoped_and_idempotent(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    author = profile_for('mentor.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    calls = []
    def rpc(name, payload):
        calls.append((name, payload))
        if len(calls) == 1:
            raise supabase_coaching.CoachingUnavailable('Temporary outage')
        return {'sent': True}
    monkeypatch.setattr(app_module, '_coaching_rpc', rpc)
    student = users()['student.a']
    headers = {'Authorization': 'Bearer token'}
    path = f'/api/students/{student}/resources'
    response = client.post(path, data={'title': 'Guide', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=headers, content_type='multipart/form-data')
    assert response.status_code == 201
    resource_id = response.get_json()['data']['id']
    assert response.get_json()['data']['notification_sent'] is False
    assert client.get(path, headers=headers).get_json()['data'][0]['notification_status'] == 'pending'

    profile_for('student.a')
    retry_path = f'{path}/{resource_id}/notification'
    assert client.post(retry_path, headers=headers).status_code == 403
    auth.create_user(app_module.AUTH_DATABASE_PATH, username='mentor.other', password='CorrectHorseBattery42', display_name='Other Mentor', role='mentor', cohort='CSE-A')
    profile_for('mentor.other')
    assert client.post(retry_path, headers=headers).status_code == 403
    assert len(calls) == 1

    profile_for('mentor.a')
    assert client.post(retry_path, headers=headers).status_code == 200
    assert calls[-1][1] == {'p_student_id': student, 'p_resource_id': resource_id, 'p_title': 'Guide'}
    assert client.get(path, headers=headers).get_json()['data'][0]['notification_status'] == 'sent'
    assert client.post(retry_path, headers=headers).status_code == 200
    assert len(calls) == 2
    assert author['id'] == users()['mentor.a']
