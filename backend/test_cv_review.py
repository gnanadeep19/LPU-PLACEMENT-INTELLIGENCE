import io

import app as app_module
import auth
import supabase_coaching
from test_app import client, login, csrf_headers  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def accounts():
    return {user['username']: user['id'] for user in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def submit(client, student_id, token, filename='resume.pdf', content=b'%PDF-1.7\nresume'):
    return client.post(f'/api/students/{student_id}/cv', data={'file': (io.BytesIO(content), filename)},
                       headers=csrf_headers(token), content_type='multipart/form-data')


def test_student_submission_and_mentor_approval(client):
    student_id = accounts()['student.a']
    token = login(client, 'student.a')
    saved = submit(client, student_id, token)
    assert saved.status_code == 201
    cv_id = saved.get_json()['data']['id']
    listing = client.get(f'/api/students/{student_id}/cv').get_json()['data']
    assert listing[0]['status'] == 'pending' and 'content' not in listing[0]
    assert submit(client, student_id, token).status_code == 409

    mentor_token = login(client, 'mentor.a')
    assert client.get(f'/api/students/{student_id}/cv/{cv_id}/download').data.startswith(b'%PDF-')
    review = client.patch(f'/api/students/{student_id}/cv/{cv_id}/review',
                          json={'status': 'approved', 'feedback': 'Well structured'}, headers=csrf_headers(mentor_token))
    assert review.status_code == 200 and review.get_json()['data']['status'] == 'approved'
    login(client, 'student.a')
    saved = client.get(f'/api/students/{student_id}/cv').get_json()['data'][0]
    assert saved['status'] == 'approved' and saved['feedback'] == 'Well structured' and saved['reviewed_at']
    download = client.get(f'/api/students/{student_id}/cv/{cv_id}/download')
    assert download.headers['Cache-Control'] == 'private, no-store'
    assert 'attachment' in download.headers['Content-Disposition']


def test_cv_access_boundaries_and_validation(client):
    ids = accounts()
    student_id = ids['student.a']
    token = login(client, 'student.a')
    assert submit(client, ids['student.b'], token).status_code == 403
    for filename, content in [('resume.pdf', b'not pdf'), ('resume.html', b'<script>'), ('resume.docx', b''), ('resume.docx', b'bad zip')]:
        assert submit(client, student_id, token, filename, content).status_code == 400
    cv_id = submit(client, student_id, token).get_json()['data']['id']
    assert client.patch(f'/api/students/{student_id}/cv/{cv_id}/review', json={'status': 'approved'}, headers=csrf_headers(token)).status_code == 403
    login(client, 'student.b')
    assert client.get(f'/api/students/{student_id}/cv').status_code == 403
    assert client.get(f'/api/students/{student_id}/cv/{cv_id}/download').status_code == 403
    mentor_token = login(client, 'mentor.a')
    assert submit(client, student_id, mentor_token).status_code == 403
    assert client.get(f"/api/students/{ids['student.b']}/cv").status_code == 403
    assert client.patch(f"/api/students/{ids['student.b']}/cv/{cv_id}/review", json={'status': 'approved'}, headers=csrf_headers(mentor_token)).status_code == 403
    assert client.patch(f'/api/students/{student_id}/cv/{cv_id}/review', json={'status': 'changes_requested', 'feedback': ''}, headers=csrf_headers(mentor_token)).status_code == 400
    assert client.patch(f'/api/students/{student_id}/cv/{cv_id}/review', json=['approved'], headers=csrf_headers(mentor_token)).status_code == 400
    assert client.patch(f'/api/students/{student_id}/cv/{cv_id}/review', json={'status': 'approved'}).status_code == 403


def test_mentor_reviews_only_latest_pending_version(client):
    student_id = accounts()['student.a']
    token = login(client, 'student.a')
    old = submit(client, student_id, token).get_json()['data']['id']
    new = submit(client, student_id, token, 'updated.docx', b'PK\x03\x04document').get_json()['data']['id']
    mentor_token = login(client, 'mentor.a')
    url = f'/api/students/{student_id}/cv/{old}/review'
    assert client.patch(url, json={'status': 'approved'}, headers=csrf_headers(mentor_token)).status_code == 409
    url = f'/api/students/{student_id}/cv/{new}/review'
    assert client.patch(url, json={'status': 'changes_requested', 'feedback': 'Add project outcomes'}, headers=csrf_headers(mentor_token)).status_code == 200
    assert client.patch(url, json={'status': 'approved'}, headers=csrf_headers(mentor_token)).status_code == 409
    token = login(client, 'student.a')
    assert submit(client, student_id, token, 'updated.docx', b'PK\x03\x04document').status_code == 201
    assert client.get(f'/api/students/{student_id}/cv').get_json()['data'][0]['status'] == 'pending'


def test_supabase_assigned_mentor_access_is_checked_and_fails_closed(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    ids = accounts()
    profile_for('student.b')
    result = client.post(f"/api/students/{ids['student.b']}/cv", data={'file': (io.BytesIO(b'%PDF-test'), 'cv.pdf')},
                         headers={'Authorization': 'Bearer token'}, content_type='multipart/form-data')
    assert result.status_code == 201
    profile_for('mentor.a')
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *_: {'students': [{'id': ids['student.b'], 'username': 'student.b', 'cohort': 'CSE-B'}]})
    assert client.get(f"/api/students/{ids['student.b']}/cv", headers={'Authorization': 'Bearer token'}).status_code == 200
    def unavailable(*_args): raise supabase_coaching.CoachingUnavailable('offline')
    monkeypatch.setattr(app_module, '_coaching_rpc', unavailable)
    assert client.get(f"/api/students/{ids['student.b']}/cv", headers={'Authorization': 'Bearer token'}).status_code == 503


def test_mentor_can_find_an_unassessed_cohort_student_who_submitted_a_cv(client):
    ids = accounts()
    token = login(client, 'student.a')
    assert submit(client, ids['student.a'], token).status_code == 201
    login(client, 'mentor.a')
    response = client.get('/api/mentor/students')
    assert response.status_code == 200
    roster = response.get_json()['data']
    assert any(item['user_id'] == ids['student.a'] and item['readiness_score'] is None and item['cv_status'] == 'pending' for item in roster)
    assert all(item['user_id'] != ids['student.b'] for item in roster)
