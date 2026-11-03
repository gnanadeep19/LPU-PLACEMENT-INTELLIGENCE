"""Optional resource-store behavior using synthetic accounts and mocked RPCs."""
import base64
import io
import sqlite3

import app as app_module
import auth
import supabase_coaching
from test_app import client  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


def ids():
    return {row['username']: row['id'] for row in auth.list_users(app_module.AUTH_DATABASE_PATH)}


def configure(monkeypatch):
    monkeypatch.setattr(app_module, 'COACHING_STORE', 'supabase')
    monkeypatch.setattr(app_module, 'RESOURCE_STORE', 'supabase')


def test_upload_uses_postgres_and_preserves_upload_key(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    configure(monkeypatch)
    calls = []
    def rpc(name, payload):
        calls.append((name, payload))
        return {'id': 23, 'notification_sent': True}
    monkeypatch.setattr(app_module, '_coaching_rpc', rpc)
    student = ids()['student.a']
    key = '2d949656-55bd-42fe-a3a9-0c43b40f6234'
    response = client.post(f'/api/students/{student}/resources', data={
        'title': 'Guide', 'category': 'Coding', 'upload_key': key,
        'file': (io.BytesIO(b'practice'), 'notes.txt')},
        headers={'Authorization': 'Bearer token'}, content_type='multipart/form-data')
    assert response.status_code == 201
    assert response.get_json()['data'] == {'id': 23, 'notification_sent': True}
    assert calls[0][0] == 'study_resource_create'
    assert calls[0][1]['p_upload_key'] == key
    assert base64.b64decode(calls[0][1]['p_content_base64']) == b'practice'
    with app_module.collaboration._connect(app_module.HISTORY_DATABASE_PATH) as db:
        assert db.execute('SELECT count(*) FROM study_resources').fetchone()[0] == 0


def test_student_cannot_upload_and_invalid_key_never_reaches_postgres(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    configure(monkeypatch)
    calls = []
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *args: calls.append(args))
    student = ids()['student.a']
    path = f'/api/students/{student}/resources'
    headers = {'Authorization': 'Bearer token'}
    profile_for('student.a')
    result = client.post(path, data={'title': 'Guide', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=headers, content_type='multipart/form-data')
    assert result.status_code == 403
    profile_for('mentor.a')
    result = client.post(path, data={'title': 'Guide', 'upload_key': 'invalid', 'file': (io.BytesIO(b'notes'), 'notes.txt')}, headers=headers, content_type='multipart/form-data')
    assert result.status_code == 400
    assert calls == []


def test_download_returns_safe_bytes_and_rejects_malformed_response(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    student = profile_for('student.a')['id']
    configure(monkeypatch)
    headers = {'Authorization': 'Bearer token'}
    path = f'/api/students/{student}/resources/23/download'
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *_: {'filename': 'notes.txt', 'content_base64': base64.b64encode(b'notes').decode()})
    result = client.get(path, headers=headers)
    assert result.status_code == 200 and result.data == b'notes'
    assert 'attachment' in result.headers['Content-Disposition']
    assert result.headers['Cache-Control'] == 'private, no-store'
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *_: {'filename': '../unsafe.txt', 'content_base64': 'bm90ZXM='})
    assert client.get(path, headers=headers).status_code == 503
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda *_: {'filename': 'notes.txt', 'content_base64': 'not-base64!'})
    assert client.get(path, headers=headers).status_code == 503


def test_postgres_outage_does_not_fall_back_to_local_resources(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    student = profile_for('student.a')['id']
    configure(monkeypatch)
    db = app_module.collaboration._connect(app_module.HISTORY_DATABASE_PATH)
    db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (?,?, 'Local only','notes.txt',?,'2026-01-01')", (student, student, sqlite3.Binary(b'notes')))
    db.commit(); db.close()
    def unavailable(*_args):
        raise supabase_coaching.CoachingUnavailable('offline')
    monkeypatch.setattr(app_module, '_coaching_rpc', unavailable)
    result = client.get(f'/api/students/{student}/resources', headers={'Authorization': 'Bearer token'})
    assert result.status_code == 503
    assert 'Local only' not in result.get_data(as_text=True)


def test_postgres_denial_is_enforced_after_local_assignment_check(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    configure(monkeypatch)
    student = ids()['student.b']
    monkeypatch.setattr(app_module, '_mentor_assigned_ids', lambda: {student})
    def denied(*_args):
        raise supabase_coaching.CoachingForbidden('denied')
    monkeypatch.setattr(app_module, '_coaching_rpc', denied)
    result = client.get(f'/api/students/{student}/resources', headers={'Authorization': 'Bearer token'})
    assert result.status_code == 403


def test_postgres_delete_is_scoped_and_rejected_when_not_authorized(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    profile_for('mentor.a')
    configure(monkeypatch)
    student = ids()['student.a']
    headers = {'Authorization': 'Bearer token'}
    calls = []
    monkeypatch.setattr(app_module, '_coaching_rpc', lambda name, payload: calls.append((name, payload)) or {'deleted': True})
    path = f'/api/students/{student}/resources/23'
    assert client.delete(path, headers=headers).status_code == 200
    assert calls == [('study_resource_delete', {'p_student_id': student, 'p_resource_id': 23})]
    profile_for('student.a')
    assert client.delete(path, headers=headers).status_code == 403
