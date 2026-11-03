"""Tests for the staged Supabase Auth server-side verifier."""

from unittest.mock import Mock, patch

import pytest
import requests

from supabase_auth import AuthServiceUnavailable, InvalidAccessToken, load_trusted_profile, verify_access_token


PROJECT = "https://example.supabase.co"
USER_ID = "4d9e8e7d-b06c-4c79-8873-8a1d7ba61c08"


@patch("supabase_auth.requests.get")
def test_verify_uses_auth_server_and_never_follows_redirects(get):
    get.return_value = Mock(status_code=200, json=lambda: {"id": USER_ID, "user_metadata": {"role": "admin"}})
    assert verify_access_token(PROJECT, "public-key", "user-token") == USER_ID
    assert get.call_args.args[0] == f"{PROJECT}/auth/v1/user"
    assert get.call_args.kwargs["headers"] == {"apikey": "public-key", "Authorization": "Bearer user-token"}
    assert get.call_args.kwargs["allow_redirects"] is False
    assert get.call_args.kwargs["timeout"] == 5


@pytest.mark.parametrize("status", [401, 403])
@patch("supabase_auth.requests.get")
def test_expired_or_invalid_tokens_are_rejected(get, status):
    get.return_value = Mock(status_code=status)
    with pytest.raises(InvalidAccessToken):
        verify_access_token(PROJECT, "key", "token")


@pytest.mark.parametrize("status", [302, 429, 500])
@patch("supabase_auth.requests.get")
def test_service_failures_fail_closed(get, status):
    get.return_value = Mock(status_code=status)
    with pytest.raises(AuthServiceUnavailable):
        verify_access_token(PROJECT, "key", "token")


@patch("supabase_auth.requests.get", side_effect=requests.Timeout())
def test_timeout_fails_closed(get):
    with pytest.raises(AuthServiceUnavailable):
        verify_access_token(PROJECT, "key", "token")


@patch("supabase_auth.requests.get")
def test_malformed_identity_is_not_accepted(get):
    get.return_value = Mock(status_code=200, json=lambda: {"id": "not-a-uuid"})
    with pytest.raises(AuthServiceUnavailable):
        verify_access_token(PROJECT, "key", "token")


@pytest.mark.parametrize("url", ["http://example.supabase.co", "https://example.supabase.co/path", "https://user:password@example.supabase.co"])
@patch("supabase_auth.requests.get")
def test_invalid_project_url_never_sends_credentials(get, url):
    with pytest.raises(AuthServiceUnavailable):
        verify_access_token(url, "key", "token")
    get.assert_not_called()


@patch("supabase_auth.requests.get")
def test_trusted_profile_is_loaded_for_the_verified_uuid(get):
    row = {"id": USER_ID, "legacy_id": 5, "role": "student", "is_active": True}
    get.return_value = Mock(status_code=200, json=lambda: [row])
    assert load_trusted_profile(PROJECT, "public-key", "token", USER_ID) == row
    assert get.call_args.kwargs['params']['id'] == f'eq.{USER_ID}'
    assert get.call_args.kwargs['allow_redirects'] is False


@pytest.mark.parametrize("rows", [[], [{"id": USER_ID, "is_active": False}], [{"id": "other", "is_active": True}]])
@patch("supabase_auth.requests.get")
def test_missing_inactive_or_mismatched_profile_is_rejected(get, rows):
    get.return_value = Mock(status_code=200, json=lambda: rows)
    with pytest.raises(InvalidAccessToken):
        load_trusted_profile(PROJECT, "key", "token", USER_ID)
