"""Flask integration tests for authentication, authorization, and API contracts."""

import json
import sqlite3

import pytest

import app as app_module
import auth

PASSWORD = "CorrectHorseBattery42"

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


@pytest.fixture()
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "assessment_history.sqlite3"
    auth_path = tmp_path / "auth.sqlite3"
    monkeypatch.setattr(app_module, "HISTORY_DATABASE_PATH", str(database_path))
    monkeypatch.setattr(app_module, "AUTH_DATABASE_PATH", str(auth_path))
    monkeypatch.setattr(app_module, "AUTH_COOKIE_SECURE", False)
    monkeypatch.setattr(app_module, "SESSION_TTL_SECONDS", 3600)
    monkeypatch.setattr(app_module, "COHORT_MIN_GROUP_SIZE", 2)
    app_module.login_limiter.reset_all()

    accounts = [
        ("student.a", "Student A", "student", "CSE-A"),
        ("student.a2", "Student A2", "student", "CSE-A"),
        ("student.b", "Student B", "student", "CSE-B"),
        ("mentor.a", "Mentor A", "mentor", "CSE-A"),
        ("officer", "Placement Officer", "placement_officer", None),
        ("admin", "Administrator", "admin", None),
    ]
    for username, display_name, role, cohort in accounts:
        auth.create_user(
            auth_path,
            username=username,
            password=PASSWORD,
            display_name=display_name,
            role=role,
            cohort=cohort,
        )

    app_module.app.config.update(TESTING=True, MAX_CONTENT_LENGTH=65536)
    with app_module.app.test_client() as test_client:
        yield test_client


def login(client, username, password=PASSWORD):
    response = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.get_json()
    return response.get_json()["data"]["csrf_token"]


def csrf_headers(token):
    return {"X-CSRF-Token": token}


def save_prediction(client, username, student=None):
    student = student or SAMPLE_STUDENT
    token = login(client, username)
    prediction = client.post("/api/v1/predict", json=student, headers=csrf_headers(token))
    assert prediction.status_code == 200, prediction.get_json()
    saved = client.post(
        "/api/v1/history",
        json={"student": student, "prediction": prediction.get_json()["data"]},
        headers=csrf_headers(token),
    )
    assert saved.status_code == 201, saved.get_json()
    return student


def test_health_is_public_and_has_security_headers(client):
    response = client.get("/api/health", headers={"X-Request-ID": "qa-health-1"})

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"
    assert response.headers["X-Request-ID"] == "qa-health-1"
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "default-src 'none'" in response.headers["Content-Security-Policy"]


def test_readiness_probe_is_public_but_model_info_requires_auth(client):
    assert client.get("/api/v1/readiness").status_code == 200
    assert client.get("/api/v1/model-info").status_code == 401


def test_login_me_and_logout_flow(client):
    invalid = client.post(
        "/api/auth/login", json={"username": "student.a", "password": "wrong-password"}
    )
    assert invalid.status_code == 401
    assert invalid.get_json()["message"] == "Invalid username or password."

    response = client.post("/api/auth/login", json={"username": "STUDENT.A", "password": PASSWORD})
    assert response.status_code == 200
    payload = response.get_json()["data"]
    assert payload["user"]["role"] == "student"
    assert payload["user"]["cohort"] == "CSE-A"
    assert "password_hash" not in json.dumps(payload)
    cookies = "\n".join(response.headers.getlist("Set-Cookie"))
    assert cookies.count("lpu_session=") == 1
    assert "HttpOnly" in cookies
    assert "lpu_csrf=" in cookies

    me = client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.get_json()["data"]["user"]["username"] == "student.a"

    logout = client.post("/api/auth/logout", headers=csrf_headers(payload["csrf_token"]))
    assert logout.status_code == 200
    assert client.get("/api/auth/me").status_code == 401


def test_login_requires_json_and_rejects_unknown_user(client):
    assert client.post("/api/auth/login", data="username=a").status_code == 400
    unknown = client.post("/api/auth/login", json={"username": "nobody", "password": PASSWORD})
    assert unknown.status_code == 401
    assert unknown.get_json()["message"] == "Invalid username or password."


def test_login_rate_limit_blocks_repeated_failures(client):
    for _ in range(5):
        response = client.post(
            "/api/auth/login", json={"username": "student.a", "password": "bad-password"}
        )
        assert response.status_code == 401

    blocked = client.post("/api/auth/login", json={"username": "student.a", "password": PASSWORD})
    assert blocked.status_code == 429
    assert int(blocked.headers["Retry-After"]) >= 1


def test_prediction_requires_session_and_csrf(client):
    anonymous = client.post("/api/v1/predict", json=SAMPLE_STUDENT)
    assert anonymous.status_code == 401
    assert anonymous.get_json()["message"] == "Authentication required."

    token = login(client, "student.a")
    missing_csrf = client.post("/api/v1/predict", json=SAMPLE_STUDENT)
    assert missing_csrf.status_code == 403
    assert "verification token" in missing_csrf.get_json()["message"]

    response = client.post("/api/v1/predict", json=SAMPLE_STUDENT, headers=csrf_headers(token))
    assert response.status_code == 200
    prediction = response.get_json()["data"]
    assert 0 <= prediction["readiness_score"] <= 100
    assert prediction["local_explanations"]
    assert "counterfactual_scenarios" in prediction
    assert all("target_met" in gap for gap in prediction["skill_gaps"])


def test_prediction_rejects_invalid_input_when_authenticated(client):
    token = login(client, "student.a")
    response = client.post(
        "/api/predict",
        json=dict(SAMPLE_STUDENT, cgpa=12.5),
        headers=csrf_headers(token),
    )
    assert response.status_code == 400
    assert "CGPA" in response.get_json()["message"]


def test_history_is_scoped_to_the_authenticated_owner(client):
    save_prediction(client, "student.a")

    token = login(client, "student.b")
    other_history = client.post(
        "/api/v1/history/query",
        json={"student": SAMPLE_STUDENT},
        headers=csrf_headers(token),
    )
    assert other_history.status_code == 200
    assert other_history.get_json()["data"] == []

    token = login(client, "student.a")
    own_history = client.post(
        "/api/v1/history/query",
        json={"student": SAMPLE_STUDENT},
        headers=csrf_headers(token),
    )
    assert len(own_history.get_json()["data"]) == 1
    assert own_history.get_json()["data"][0]["student_profile"] == SAMPLE_STUDENT


def test_history_rejects_forged_prediction_snapshot(client):
    token = login(client, "student.a")
    response = client.post(
        "/api/history",
        json={
            "student": SAMPLE_STUDENT,
            "prediction": {
                "readiness_score": 101,
                "readiness_category": "Placement Ready",
                "model_probability": 1.0,
            },
        },
        headers=csrf_headers(token),
    )
    assert response.status_code == 400
    assert "outside permitted ranges" in response.get_json()["message"]


def test_history_recomputes_score_and_model_version_on_server(client):
    token = login(client, "student.a")
    actual = client.post("/api/v1/predict", json=SAMPLE_STUDENT, headers=csrf_headers(token)).get_json()["data"]
    forged = dict(actual, readiness_score=0, readiness_category="Guaranteed placement", model_version="forged-model")
    saved = client.post("/api/v1/history", json={"student": SAMPLE_STUDENT, "prediction": forged},
                        headers=csrf_headers(token))
    assert saved.status_code == 201
    history_response = client.post("/api/v1/history/query", json={"student": SAMPLE_STUDENT},
                                   headers=csrf_headers(token))
    snapshot = history_response.get_json()["data"][0]
    assert snapshot["readiness_score"] == actual["readiness_score"]
    assert snapshot["readiness_category"] == actual["readiness_category"]
    assert snapshot["model_version"] == actual["model_version"]


def test_students_cannot_read_cohort_analytics(client):
    login(client, "student.a")
    response = client.get("/api/v1/cohort-analytics")
    assert response.status_code == 403
    assert "permission" in response.get_json()["message"]


def test_mentor_sees_only_assigned_cohort_and_officer_sees_all(client):
    save_prediction(client, "student.a", dict(SAMPLE_STUDENT, cgpa=7.8))
    save_prediction(client, "student.a2", dict(SAMPLE_STUDENT, cgpa=8.2))
    save_prediction(client, "student.b", dict(SAMPLE_STUDENT, cgpa=6.6))

    login(client, "mentor.a")
    mentor_cohort = client.get("/api/v1/cohort-analytics").get_json()["data"]
    assert mentor_cohort["suppressed"] is False
    assert mentor_cohort["cohort"] == "CSE-A"
    assert mentor_cohort["unique_profiles"] == 2
    assert "student_profile" not in json.dumps(mentor_cohort)

    login(client, "officer")
    institution = client.get("/api/v1/cohort-analytics").get_json()["data"]
    assert institution["cohort"] is None
    assert institution["unique_profiles"] == 3


def _user_id(username):
    return next(user["id"] for user in auth.list_users(app_module.AUTH_DATABASE_PATH)
                if user["username"] == username)


def test_student_cannot_read_another_students_coaching_records(client):
    login(client, "student.a")
    response = client.get(f"/api/v1/students/{_user_id('student.b')}/coaching")
    assert response.status_code == 403
    assert "own student records" in response.get_json()["message"]


def test_mentor_cannot_read_out_of_cohort_student_records(client):
    login(client, "mentor.a")
    response = client.get(f"/api/v1/students/{_user_id('student.b')}/coaching")
    assert response.status_code == 403
    assert "cohort or assigned to you" in response.get_json()["message"]


def test_student_cannot_create_private_mentor_note(client):
    student_id = _user_id("student.a")
    token = login(client, "student.a")
    response = client.post(f"/api/v1/students/{student_id}/coaching", json={
        "kind": "note", "title": "Private note", "visibility": "mentor",
    }, headers=csrf_headers(token))
    assert response.status_code == 403
    assert "action-plan goals only" in response.get_json()["message"]


def test_student_cannot_change_placement_stage(client):
    token = login(client, "student.a")
    response = client.post("/api/v1/placement-pipeline", json={
        "student_id": _user_id("student.a"), "stage": "Placed",
    }, headers=csrf_headers(token))
    assert response.status_code == 403
    assert "permission" in response.get_json()["message"].lower()


def test_invalid_coaching_due_date_and_evidence_url_are_rejected(client):
    student_id = _user_id("student.a")
    token = login(client, "student.a")
    invalid_goal = client.post(f"/api/v1/students/{student_id}/coaching", json={
        "kind": "goal", "title": "Practice", "due_date": "not-a-date",
    }, headers=csrf_headers(token))
    assert invalid_goal.status_code == 400
    assert "valid ISO date" in invalid_goal.get_json()["message"]

    invalid_evidence = client.post(f"/api/v1/students/{student_id}/evidence", json={
        "evidence_type": "project", "title": "Portfolio", "evidence_url": "javascript:alert(1)",
    }, headers=csrf_headers(token))
    assert invalid_evidence.status_code == 400
    assert "HTTP or HTTPS" in invalid_evidence.get_json()["message"]


def test_profile_correction_request_is_owner_scoped_and_admin_reviewed(client):
    student_id = _user_id("student.a")
    token = login(client, "student.a")
    submitted = client.post(f"/api/v1/students/{student_id}/profile-corrections", json={
        "field_name": "coding_score", "current_value": "62", "requested_value": "72",
        "reason": "The saved assessment result was entered incorrectly.",
    }, headers=csrf_headers(token))
    assert submitted.status_code == 201
    correction_id = submitted.get_json()["data"]["id"]

    other_student = _user_id("student.b")
    assert client.get(f"/api/v1/students/{other_student}/profile-corrections").status_code == 403
    login(client, "mentor.a")
    assert client.get("/api/v1/profile-corrections").status_code == 403
    assert client.get(f"/api/v1/students/{student_id}/profile-corrections").status_code == 403

    admin_token = login(client, "admin")
    listed = client.get("/api/v1/profile-corrections")
    assert listed.status_code == 200
    assert listed.get_json()["data"][0]["status"] == "open"
    reviewed = client.patch(f"/api/v1/profile-corrections/{correction_id}", json={
        "status": "reviewed", "resolution": "Reviewed; update using approved evidence and reassess."
    }, headers=csrf_headers(admin_token))
    assert reviewed.status_code == 200
    assert reviewed.get_json()["data"]["status"] == "reviewed"


def test_profile_correction_requires_reason_and_student_cannot_review(client):
    student_id = _user_id("student.a")
    token = login(client, "student.a")
    missing_reason = client.post(f"/api/v1/students/{student_id}/profile-corrections", json={
        "field_name": "coding_score", "requested_value": "72",
    }, headers=csrf_headers(token))
    assert missing_reason.status_code == 400

    forbidden = client.patch("/api/v1/profile-corrections/1", json={"status": "reviewed"},
                             headers=csrf_headers(token))
    assert forbidden.status_code == 403


def test_duplicate_pending_evidence_submission_is_rejected(client):
    student_id = _user_id("student.a")
    token = login(client, "student.a")
    payload = {"evidence_type": "project", "title": "Placement dashboard", "detail": "React project",
               "evidence_url": "https://example.com/project"}
    first = client.post(f"/api/v1/students/{student_id}/evidence", json=payload,
                        headers=csrf_headers(token))
    duplicate = client.post(f"/api/v1/students/{student_id}/evidence", json=payload,
                            headers=csrf_headers(token))
    assert first.status_code == 201
    assert duplicate.status_code == 400
    assert "already awaiting review" in duplicate.get_json()["message"]


def test_small_cohort_is_suppressed(client, monkeypatch):
    monkeypatch.setattr(app_module, "COHORT_MIN_GROUP_SIZE", 5)
    save_prediction(client, "student.a")

    login(client, "mentor.a")
    cohort = client.get("/api/v1/cohort-analytics").get_json()["data"]
    assert cohort["suppressed"] is True
    assert cohort["unique_profiles"] is None
    assert cohort["readiness_distribution"] == {}
    assert cohort["common_gaps"] == []


def test_metrics_require_admin(client):
    login(client, "mentor.a")
    assert client.get("/api/v1/metrics").status_code == 403
    login(client, "admin")
    assert client.get("/api/v1/metrics").status_code == 200


def test_expired_session_is_rejected_and_reports_expiry(client):
    login(client, "student.a")
    with sqlite3.connect(app_module.AUTH_DATABASE_PATH) as connection:
        connection.execute("UPDATE sessions SET expires_at = '2000-01-01T00:00:00Z'")

    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert "expired" in response.get_json()["message"].lower()


def test_deactivating_an_account_revokes_its_sessions(client):
    login(client, "student.a")
    auth.set_active(app_module.AUTH_DATABASE_PATH, "student.a", False)
    assert client.get("/api/auth/me").status_code == 401
    relogin = client.post("/api/auth/login", json={"username": "student.a", "password": PASSWORD})
    assert relogin.status_code == 401


def test_oversized_payload_returns_413(client):
    token = login(client, "student.a")
    app_module.app.config["MAX_CONTENT_LENGTH"] = 64
    response = client.post(
        "/api/predict",
        data=json.dumps({"payload": "x" * 1000}),
        content_type="application/json",
        headers=csrf_headers(token),
    )
    assert response.status_code == 413
    assert response.get_json()["message"] == "Request payload is too large"


def test_mentor_account_requires_cohort(tmp_path):
    with pytest.raises(ValueError, match="cohort"):
        auth.create_user(
            tmp_path / "auth.sqlite3",
            username="mentor.zero",
            password=PASSWORD,
            display_name="Mentor Zero",
            role="mentor",
            cohort=None,
        )
