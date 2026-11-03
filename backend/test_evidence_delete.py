import app as app_module
import auth
from test_app import client, login, csrf_headers  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def accounts():
    return {u['username']: u['id'] for u in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def add_evidence(client, student, token):
    result = client.post(f'/api/students/{student}/evidence', json={'evidence_type': 'certification', 'title': 'Certificate'}, headers=csrf_headers(token))
    assert result.status_code == 201
    return result.get_json()['data']['id']


def test_delete_own_evidence_and_audit(client):
    token = login(client, 'student.a')
    student = accounts()['student.a']
    evidence = add_evidence(client, student, token)
    path = f'/api/students/{student}/evidence/{evidence}'
    assert client.delete(path).status_code == 403
    assert client.delete(path, headers=csrf_headers(token)).status_code == 200
    assert client.get(f'/api/students/{student}/evidence').get_json()['data'] == []
    assert client.delete(path, headers=csrf_headers(token)).status_code == 404
    assert any(x['action'] == 'delete_profile_evidence' and x['subject_id'] == student for x in app_module.collaboration.list_audit(app_module.HISTORY_DATABASE_PATH))


def test_other_students_and_staff_cannot_delete(client):
    token = login(client, 'student.a')
    ids = accounts()
    evidence = add_evidence(client, ids['student.a'], token)
    token = login(client, 'student.b')
    assert client.delete(f"/api/students/{ids['student.a']}/evidence/{evidence}", headers=csrf_headers(token)).status_code == 403
    assert client.delete(f"/api/students/{ids['student.b']}/evidence/{evidence}", headers=csrf_headers(token)).status_code == 404
    token = login(client, 'mentor.a')
    assert client.delete(f"/api/students/{ids['student.a']}/evidence/{evidence}", headers=csrf_headers(token)).status_code == 403


def test_supabase_student_can_delete_only_own_evidence(supabase_mode):
    client, profile_for = supabase_mode
    ids = accounts()
    profile_for('student.a')
    headers = {'Authorization': 'Bearer token'}
    created = client.post(f"/api/students/{ids['student.a']}/evidence", json={'evidence_type': 'project', 'title': 'Project'}, headers=headers)
    evidence = created.get_json()['data']['id']
    profile_for('student.b')
    assert client.delete(f"/api/students/{ids['student.a']}/evidence/{evidence}", headers=headers).status_code == 403
    profile_for('student.a')
    assert client.delete(f"/api/v1/students/{ids['student.a']}/evidence/{evidence}", headers=headers).status_code == 200
