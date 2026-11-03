"""Live-server smoke test for the LPU Placement Intelligence API.

The API requires an authenticated account. Provision one first:

    py backend/manage_users.py create-user --username smoke.student \\
        --display-name "Smoke Student" --role student --cohort CSE-SMOKE

Then start the server and run:

    SMOKE_USERNAME=smoke.student SMOKE_PASSWORD=... py backend/test_api.py

Optional: API_BASE_URL (default http://127.0.0.1:5000).
"""

import os
import sys

import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:5000").rstrip("/")
USERNAME = os.environ.get("SMOKE_USERNAME", "")
PASSWORD = os.environ.get("SMOKE_PASSWORD", "")

SAMPLE_STUDENT = {
    "cgpa": 7.8,
    "technical_score": 75,
    "aptitude_score": 68,
    "communication_score": 72,
    "coding_score": 70,
    "projects": 2,
    "internships": 1,
    "certifications": 2,
    "backlogs": 0,
}


def run_tests() -> int:
    print("=" * 65)
    print("   Running Automated Backend API Verification Tests   ")
    print("=" * 65)

    if not USERNAME or not PASSWORD:
        print(
            "\n[SKIPPED]: Set SMOKE_USERNAME and SMOKE_PASSWORD to run authenticated "
            "checks.\nCreate an account with backend/manage_users.py first."
        )
        return 2

    try:
        health_resp = requests.get(f"{BASE_URL}/api/health", timeout=5)
    except requests.exceptions.ConnectionError:
        print(f"\n[ERROR]: Flask server is not running on {BASE_URL}")
        print("Please start the backend with: python backend/app.py")
        return 1

    print(f"[TEST 1] GET /api/health -> Status: {health_resp.status_code}")
    assert health_resp.status_code == 200, "Health check failed!"

    session = requests.Session()
    login_resp = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=10,
    )
    print(f"[TEST 2] POST /api/auth/login -> Status: {login_resp.status_code}")
    if login_resp.status_code != 200:
        print(f"         {login_resp.json().get('message')}")
        return 1
    login_data = login_resp.json()["data"]
    csrf = login_data["csrf_token"]
    headers = {"X-CSRF-Token": csrf}
    print(f"         Role: {login_data['user']['role']} | Cohort: {login_data['user']['cohort']}")

    me_resp = session.get(f"{BASE_URL}/api/auth/me", timeout=5)
    print(f"[TEST 3] GET /api/auth/me -> Status: {me_resp.status_code}")
    assert me_resp.status_code == 200, "Session lookup failed!"
    assert me_resp.json()["data"]["user"]["username"] == USERNAME.lower()

    info_resp = requests.get(f"{BASE_URL}/api/model-info", timeout=10)
    print(f"[TEST 4] GET /api/model-info (anonymous) -> Status: {info_resp.status_code}")
    assert info_resp.status_code == 401, "Model info must require authentication!"
    info_resp = session.get(f"{BASE_URL}/api/model-info", timeout=10)
    print(f"         GET /api/model-info (session) -> Status: {info_resp.status_code}")
    assert info_resp.status_code == 200, "Authenticated model-info check failed!"

    missing_csrf = session.post(f"{BASE_URL}/api/predict", json=SAMPLE_STUDENT, timeout=10)
    print(f"[TEST 5] POST /api/predict without CSRF -> Status: {missing_csrf.status_code}")
    assert missing_csrf.status_code == 403, "CSRF protection is not enforced!"

    pred_resp = session.post(
        f"{BASE_URL}/api/predict", json=SAMPLE_STUDENT, headers=headers, timeout=15
    )
    print(f"[TEST 6] POST /api/predict (valid profile) -> Status: {pred_resp.status_code}")
    assert pred_resp.status_code == 200, pred_resp.text
    prediction = pred_resp.json()["data"]
    print(f"         Readiness Score:  {prediction['readiness_score']} / 100")
    print(f"         Skill Gaps Found: {len(prediction['skill_gaps'])}")

    history_resp = session.post(
        f"{BASE_URL}/api/history/query",
        json={"student": SAMPLE_STUDENT},
        headers=headers,
        timeout=10,
    )
    print(f"[TEST 7] POST /api/history/query -> Status: {history_resp.status_code}")
    assert history_resp.status_code == 200, history_resp.text

    bad_resp = session.post(
        f"{BASE_URL}/api/predict",
        json=dict(SAMPLE_STUDENT, cgpa=12.5),
        headers=headers,
        timeout=10,
    )
    print(f"[TEST 8] POST /api/predict (invalid CGPA) -> Status: {bad_resp.status_code}")
    assert bad_resp.status_code == 400, "Validation check failed to reject invalid CGPA!"

    logout_resp = session.post(f"{BASE_URL}/api/auth/logout", headers=headers, timeout=5)
    print(f"[TEST 9] POST /api/auth/logout -> Status: {logout_resp.status_code}")
    assert logout_resp.status_code == 200, "Logout failed!"
    assert session.get(f"{BASE_URL}/api/auth/me", timeout=5).status_code == 401

    print("\n" + "=" * 65)
    print("   ALL API TESTS PASSED! Backend is ready.   ")
    print("=" * 65)
    return 0


if __name__ == "__main__":
    sys.exit(run_tests())
