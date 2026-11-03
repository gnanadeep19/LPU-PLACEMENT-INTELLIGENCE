"""Call cohort-scoped coaching RPCs using the signed-in user's access token."""

from __future__ import annotations

import requests

from supabase_auth import AuthServiceUnavailable, _project_origin


class CoachingUnavailable(RuntimeError):
    """Postgres is unavailable or the RPC migration has not been installed."""


class CoachingForbidden(PermissionError):
    """The database denied access to this coaching record."""


def call(project_url: str, publishable_key: str, token: str, name: str, payload: dict):
    if name not in {"coaching_list", "coaching_create", "coaching_update", "coaching_delete", "mentor_assignment_admin_list", "mentor_assignment_set", "mentor_assignment_mine", "resource_shared_notify", "study_resource_list", "study_resource_create", "study_resource_download", "study_resource_delete"}:
        raise ValueError("Unsupported coaching operation.")
    if not publishable_key or not token:
        raise CoachingUnavailable("Coaching is not configured.")
    try:
        response = requests.post(
            f"{_project_origin(project_url)}/rest/v1/rpc/{name}",
            headers={"apikey": publishable_key, "Authorization": f"Bearer {token}"},
            json=payload, timeout=10, allow_redirects=False,
        )
    except (requests.RequestException, AuthServiceUnavailable) as exc:
        raise CoachingUnavailable("Coaching service is unavailable.") from exc
    if response.status_code in (401, 403):
        raise CoachingForbidden("You do not have access to this coaching record.")
    if response.status_code in (400, 422):
        raise ValueError("Check the coaching details and try again.")
    if response.status_code != 200:
        raise CoachingUnavailable("Coaching service is unavailable.")
    try:
        result = response.json()
    except ValueError as exc:
        raise CoachingUnavailable("Coaching service returned an invalid response.") from exc
    expected = list if name in {"coaching_list", "study_resource_list"} else dict
    if not isinstance(result, expected):
        raise CoachingUnavailable("Coaching service returned an invalid response.")
    return result
