import pytest

import app as app_module
from test_app import client, login  # noqa: F401
from test_supabase_app import supabase_mode  # noqa: F401


@pytest.mark.parametrize('username', ['student.a', 'mentor.a', 'officer'])
def test_directory_denies_non_admin_roles(client, username):
    login(client, username)
    assert client.get('/api/admin/mentors').status_code == 403


def test_directory_requires_login(client):
    assert client.get('/api/admin/mentors').status_code == 401


def test_admin_directory_only_contains_mentor_accounts_and_audits_access(client):
    login(client, 'admin')
    response = client.get('/api/admin/mentors')
    assert response.status_code == 200
    mentors = response.get_json()['data']
    assert len(mentors) == 1
    assert mentors[0]['username'] == 'mentor.a' and mentors[0]['cohort'] == 'CSE-A'
    assert set(mentors[0]) == {'id', 'username', 'display_name', 'cohort', 'is_active'}
    assert any(item['action'] == 'view_mentor_directory' for item in app_module.collaboration.list_audit(app_module.HISTORY_DATABASE_PATH))


def test_supabase_admin_access_and_non_admin_denial(supabase_mode):
    client, profile_for = supabase_mode
    profile_for('admin')
    assert client.get('/api/v1/admin/mentors', headers={'Authorization': 'Bearer token'}).status_code == 200
    profile_for('mentor.a')
    assert client.get('/api/v1/admin/mentors', headers={'Authorization': 'Bearer token'}).status_code == 403
