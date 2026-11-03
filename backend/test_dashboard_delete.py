import io
import auth
import app as app_module
from test_app import client, login, csrf_headers  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def ids():
    return {user['username']: user['id'] for user in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def test_student_can_withdraw_only_own_open_correction(client):
    token = login(client, 'student.a')
    users = ids()
    result = client.post(f"/api/students/{users['student.a']}/profile-corrections", json={'field_name': 'Score', 'requested_value': '70', 'reason': 'Incorrect'}, headers=csrf_headers(token))
    correction = result.get_json()['data']['id']
    path = f"/api/students/{users['student.a']}/profile-corrections/{correction}"
    other = login(client, 'student.b')
    assert client.delete(path, headers=csrf_headers(other)).status_code == 403
    token = login(client, 'student.a')
    assert client.delete(path).status_code == 403
    assert client.delete(path, headers=csrf_headers(token)).status_code == 200
    assert client.delete(path, headers=csrf_headers(token)).status_code == 404


def test_reviewed_correction_cannot_be_withdrawn(client):
    token = login(client, 'student.a')
    users = ids()
    result = client.post(f"/api/students/{users['student.a']}/profile-corrections", json={'field_name': 'Score', 'requested_value': '70', 'reason': 'Incorrect'}, headers=csrf_headers(token))
    correction = result.get_json()['data']['id']
    app_module.collaboration.review_profile_correction(app_module.HISTORY_DATABASE_PATH, correction, status='reviewed', reviewer_id=users['admin'], resolution='Reviewed')
    assert client.delete(f"/api/students/{users['student.a']}/profile-corrections/{correction}", headers=csrf_headers(token)).status_code == 409


def test_only_author_can_delete_coaching_item(client):
    token = login(client, 'mentor.a')
    users = ids()
    student = users['student.a']
    response = client.post(f'/api/students/{student}/coaching', json={'kind': 'goal', 'title': 'Mentor goal', 'visibility': 'student'}, headers=csrf_headers(token))
    item = response.get_json()['data']['id']
    path = f'/api/students/{student}/coaching/{item}'
    student_token = login(client, 'student.a')
    assert client.delete(path, headers=csrf_headers(student_token)).status_code == 403
    token = login(client, 'mentor.a')
    assert client.delete(path, headers=csrf_headers(token)).status_code == 200
    assert client.delete(path, headers=csrf_headers(token)).status_code == 404


def test_mentor_can_delete_own_resource_but_not_other_mentors(client):
    users = ids()
    auth.create_user(app_module.AUTH_DATABASE_PATH, username='mentor.other', password='CorrectHorseBattery42', display_name='Other Mentor', role='mentor', cohort='CSE-A')
    token = login(client, 'mentor.a')
    result = client.post(f"/api/students/{users['student.a']}/resources", data={'title': 'Guide', 'file': (io.BytesIO(b'notes'), 'guide.txt')}, headers=csrf_headers(token), content_type='multipart/form-data')
    resource = result.get_json()['data']['id']
    path = f"/api/students/{users['student.a']}/resources/{resource}"
    other = login(client, 'mentor.other')
    assert client.delete(path, headers=csrf_headers(other)).status_code == 403
    other = login(client, 'student.a')
    assert client.delete(path, headers=csrf_headers(other)).status_code == 403
    token = login(client, 'mentor.a')
    assert client.delete(path, headers=csrf_headers(token)).status_code == 200
    assert client.delete(path, headers=csrf_headers(token)).status_code == 404


def test_only_placement_staff_can_remove_placement_record(client):
    users = ids()
    token = login(client, 'admin')
    result = client.post('/api/placement-pipeline', json={'student_id': users['student.a'], 'stage': 'Preparing'}, headers=csrf_headers(token))
    assert result.status_code == 200
    path = f"/api/placement-pipeline/{users['student.a']}"
    other = login(client, 'mentor.a')
    assert client.delete(path, headers=csrf_headers(other)).status_code == 403
    token = login(client, 'admin')
    assert client.delete(path, headers=csrf_headers(token)).status_code == 200
    assert client.delete(path, headers=csrf_headers(token)).status_code == 404


def test_supabase_auth_allows_only_uploader_to_remove_resource(supabase_mode):
    client, profile_for = supabase_mode
    users = ids()
    profile_for('mentor.a')
    headers = {'Authorization': 'Bearer token'}
    result = client.post(f"/api/students/{users['student.a']}/resources", data={'title': 'Guide', 'file': (io.BytesIO(b'notes'), 'guide.txt')}, headers=headers, content_type='multipart/form-data')
    path = f"/api/students/{users['student.a']}/resources/{result.get_json()['data']['id']}"
    profile_for('student.a')
    assert client.delete(path, headers=headers).status_code == 403
    profile_for('mentor.a')
    assert client.delete(path, headers=headers).status_code == 200


def test_supabase_coaching_delete_fails_closed_if_rpc_unavailable(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    user = profile_for('student.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_coaching_list', lambda *args, **kwargs: [{'id': 7, 'author_id': user['id'], 'kind': 'goal', 'visibility': 'student'}])
    def unavailable(*args, **kwargs):
        raise app_module.supabase_coaching.CoachingUnavailable()
    monkeypatch.setattr(app_module, '_coaching_rpc', unavailable)
    result = client.delete(f"/api/students/{user['id']}/coaching/7", headers={'Authorization': 'Bearer token'})
    assert result.status_code == 503
