import io
import pytest
import app as app_module
import auth
from test_app import client, login, csrf_headers  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def accounts():
    return {u['username']: u['id'] for u in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def test_mentor_can_share_and_student_can_download(client):
    token = login(client, 'mentor.a')
    ids = accounts()
    student = ids['student.a']
    content = b'%PDF-1.7\n' + b'a' * 70000
    response = client.post(f'/api/students/{student}/resources', data={
        'title': 'SQL guide', 'description': 'Practise joins', 'file': (io.BytesIO(content), 'guide.pdf')
    }, headers=csrf_headers(token), content_type='multipart/form-data')
    assert response.status_code == 201, response.get_json()
    resource = response.get_json()['data']['id']
    login(client, 'student.a')
    listing = client.get(f'/api/students/{student}/resources').get_json()['data']
    assert len(listing) == 1 and listing[0]['title'] == 'SQL guide' and 'content' not in listing[0]
    downloaded = client.get(f'/api/students/{student}/resources/{resource}/download')
    assert downloaded.status_code == 200 and downloaded.data == content
    assert 'attachment' in downloaded.headers['Content-Disposition']
    assert downloaded.headers['Cache-Control'] == 'private, no-store'
    login(client, 'student.b')
    assert client.get(f'/api/students/{student}/resources').status_code == 403
    assert client.get(f'/api/students/{student}/resources/{resource}/download').status_code == 403


def test_permissions_and_file_validation(client):
    token = login(client, 'student.a')
    ids = accounts()
    url = f"/api/students/{ids['student.a']}/resources"
    assert client.post(url, data={}, headers=csrf_headers(token)).status_code == 403
    token = login(client, 'mentor.a')
    assert client.post(f"/api/students/{ids['student.b']}/resources", data={}, headers=csrf_headers(token)).status_code == 403
    for name, contents in [('script.html', b'<script>'), ('fake.pdf', b'not a pdf'), ('empty.txt', b'')]:
        response = client.post(url, data={'title': 'Bad', 'file': (io.BytesIO(contents), name)}, headers=csrf_headers(token), content_type='multipart/form-data')
        assert response.status_code == 400
    assert client.post(url, data={'title': 'No csrf', 'file': (io.BytesIO(b'text'), 'test.txt')}, content_type='multipart/form-data').status_code == 403


def test_supabase_authenticated_student_isolation(supabase_mode):
    client, profile_for = supabase_mode
    ids = accounts()
    profile_for('mentor.a')
    response = client.post(f"/api/students/{ids['student.a']}/resources", data={'title': 'Notes', 'file': (io.BytesIO(b'hello'), 'notes.txt')}, headers={'Authorization': 'Bearer token'}, content_type='multipart/form-data')
    assert response.status_code == 201
    profile_for('student.a')
    assert len(client.get(f"/api/students/{ids['student.a']}/resources", headers={'Authorization': 'Bearer token'}).get_json()['data']) == 1
    profile_for('student.b')
    assert client.get(f"/api/students/{ids['student.a']}/resources", headers={'Authorization': 'Bearer token'}).status_code == 403
