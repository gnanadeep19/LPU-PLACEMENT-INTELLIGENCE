"""Verify Supabase access tokens for the staged authentication migration.

Never authorize based on editable user metadata: load role and cohort from the
administrator-provisioned app_users table, protected by RLS.
"""

from __future__ import annotations

from urllib.parse import urlsplit
from uuid import UUID

import requests


class InvalidAccessToken(ValueError):
    """The authentication service rejected the access token."""


class AuthServiceUnavailable(RuntimeError):
    """The authentication service could not safely verify a token."""


def _project_origin(project_url: str) -> str:
    try:
        parsed = urlsplit(project_url.strip())
        valid = (parsed.scheme == "https" and parsed.hostname and not parsed.username
                 and not parsed.password and not parsed.query and not parsed.fragment
                 and parsed.path in ("", "/"))
    except (AttributeError, ValueError) as exc:
        raise AuthServiceUnavailable("A valid HTTPS Supabase project URL is required.") from exc
    if not valid:
        raise AuthServiceUnavailable("A valid HTTPS Supabase project URL is required.")
    return f"{parsed.scheme}://{parsed.netloc}"


def verify_access_token(project_url: str, publishable_key: str, token: str) -> str:
    """Return the verified Supabase Auth user UUID, or fail closed.

    Calls the Auth server rather than trusting unverified JWT contents. The
    publishable/anon key is not an access token. A secret/service key must not
    be passed here or exposed to the frontend.
    """
    origin = _project_origin(project_url)
    if not publishable_key or not token or len(token) > 16384:
        raise InvalidAccessToken("Authentication is required.")
    try:
        response = requests.get(
            f"{origin}/auth/v1/user",
            headers={"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            timeout=5,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise AuthServiceUnavailable("Authentication service is unavailable.") from exc
    if response.status_code in (401, 403):
        raise InvalidAccessToken("Your session is invalid or expired.")
    if response.status_code != 200:
        raise AuthServiceUnavailable("Authentication service is unavailable.")
    try:
        user_id = response.json()["id"]
        return str(UUID(str(user_id)))
    except (KeyError, TypeError, ValueError) as exc:
        raise AuthServiceUnavailable("Authentication service returned an invalid user.") from exc


def load_trusted_profile(project_url: str, publishable_key: str, token: str, user_id: str) -> dict:
    """Load only the verified user's server-provisioned profile under RLS."""
    origin = _project_origin(project_url)
    try:
        response = requests.get(
            f"{origin}/rest/v1/app_users",
            params={"id": f"eq.{user_id}", "select": "id,legacy_id,username,display_name,role,cohort,is_active"},
            headers={"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            timeout=5,
            allow_redirects=False,
        )
    except requests.RequestException as exc:
        raise AuthServiceUnavailable("Account service is unavailable.") from exc
    if response.status_code in (401, 403):
        raise InvalidAccessToken("Your session is invalid or expired.")
    if response.status_code != 200:
        raise AuthServiceUnavailable("Account service is unavailable.")
    try:
        rows = response.json()
        if not isinstance(rows, list) or len(rows) != 1 or not isinstance(rows[0], dict):
            raise InvalidAccessToken("Account is not provisioned or is inactive.")
        profile = rows[0]
        if profile.get("id") != user_id or profile.get("is_active") is not True:
            raise InvalidAccessToken("Account is not provisioned or is inactive.")
        return profile
    except ValueError as exc:
        if isinstance(exc, InvalidAccessToken):
            raise
        raise AuthServiceUnavailable("Account service returned invalid data.") from exc
