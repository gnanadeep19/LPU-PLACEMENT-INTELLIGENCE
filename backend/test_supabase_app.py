"""Transition-mode authorization checks; no live Supabase project required."""

import pytest

import app as app_module
import auth
import supabase_auth
from test_app import client  # noqa: F401 - shared isolated database fixture


USER_ID = "4d9e8e7d-b06c-4c79-8873-8a1d7ba61c08"


@pytest.fixture
def supabase_mode(client, monkeypatch):
    monkeypatch.setattr(app_module, "AUTH_PROVIDER", "supabase")
    monkeypatch.setattr(app_module, "SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setattr(app_module, "SUPABASE_PUBLISHABLE_KEY", "public-key")
    monkeypatch.setattr(supabase_auth, "verify_access_token", lambda *args: USER_ID)

    def profile_for(username):
        user = next(row for row in auth.list_users(app_module.AUTH_DATABASE_PATH) if row["username"] == username)
        profile = {**user, "legacy_id": user["id"], "id": USER_ID}
        monkeypatch.setattr(supabase_auth, "load_trusted_profile", lambda *args: profile)
        return user

    return client, profile_for


def test_supabase_mode_rejects_cookie_fallback_and_local_password_login(supabase_mode):
    client, profile_for = supabase_mode
    profile_for("student.a")
    assert client.get('/api/auth/me').status_code == 401
    assert client.post('/api/auth/login', json={'username': 'student.a', 'password': 'anything'}).status_code == 404


def test_verified_user_is_mapped_and_role_checks_remain_in_force(supabase_mode):
    client, profile_for = supabase_mode
    student = profile_for("student.a")
    headers = {"Authorization": "Bearer verified-token"}
    response = client.get('/api/auth/me', headers=headers)
    assert response.status_code == 200
    assert response.get_json()['data']['user']['id'] == student['id']
    assert client.get('/api/mentor/students', headers=headers).status_code == 403
    assert client.get('/api/students/2/coaching', headers=headers).status_code == 403


def test_mentor_cannot_access_another_cohort(supabase_mode):
    client, profile_for = supabase_mode
    profile_for("mentor.a")
    student_b = next(row for row in auth.list_users(app_module.AUTH_DATABASE_PATH) if row['username'] == 'student.b')
    response = client.get(f"/api/students/{student_b['id']}/coaching", headers={"Authorization": "Bearer token"})
    assert response.status_code == 403


def test_mismatched_role_or_unknown_mapping_fails_closed(supabase_mode, monkeypatch):
    client, profile_for = supabase_mode
    user = profile_for("student.a")
    headers = {"Authorization": "Bearer token"}
    monkeypatch.setattr(supabase_auth, "load_trusted_profile", lambda *args: {
        "id": USER_ID, "legacy_id": user['id'], "username": user['username'], "role": "admin", "cohort": user['cohort'], "is_active": True,
    })
    assert client.get('/api/auth/me', headers=headers).status_code == 401
    monkeypatch.setattr(supabase_auth, "load_trusted_profile", lambda *args: {"legacy_id": 999999})
    assert client.get('/api/auth/me', headers=headers).status_code == 401


def test_auth_service_outage_is_not_treated_as_login_failure(supabase_mode, monkeypatch):
    client, _ = supabase_mode
    def unavailable(*args):
        raise supabase_auth.AuthServiceUnavailable()
    monkeypatch.setattr(supabase_auth, 'verify_access_token', unavailable)
    assert client.get('/api/auth/me', headers={"Authorization": "Bearer token"}).status_code == 503
