"""
Flask API Server for LPU Placement Intelligence & Student Readiness Prediction Platform

Public:
  - GET  /api/health
  - GET  /api/v1/readiness
  - POST /api/auth/login
Session and role protected:
  - GET  /api/auth/me
  - POST /api/auth/logout
  - GET  /api/model-info
  - POST /api/predict
  - POST /api/history
  - POST /api/history/query
  - GET  /api/cohort-analytics  (staff roles, cohort scoped)
"""

import os
import io
import base64
import binascii
import secrets
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from functools import wraps

from flask import Flask, g, jsonify, request, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename

import auth
import collaboration
import supabase_auth
import supabase_coaching
import shap_explanations
from config import load_settings
from history import (
    cohort_analytics,
    list_assessments,
    save_assessment,
    validate_prediction_snapshot,
)
from model import (
    load_model,
    predict_student_readiness,
    train_placement_model,
    validate_student_input,
)
from observability import record_request, snapshot

app = Flask(__name__)
settings = load_settings()
app.config["MAX_CONTENT_LENGTH"] = settings.max_content_length
CORS(
    app,
    resources={r"/api/*": {"origins": settings.cors_origins}},
    supports_credentials=True,
)

MODEL_PATH = settings.model_path
HISTORY_DATABASE_PATH = settings.history_database_path
AUTH_DATABASE_PATH = settings.auth_database_path
SESSION_TTL_SECONDS = settings.session_ttl_seconds
AUTH_COOKIE_SECURE = settings.auth_cookie_secure
AUTH_PROVIDER = os.environ.get("AUTH_PROVIDER", "local").strip().lower()
if AUTH_PROVIDER not in {"local", "supabase"}:
    raise RuntimeError("AUTH_PROVIDER must be 'local' or 'supabase'.")
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY", "")
COACHING_STORE = os.environ.get("COACHING_STORE", "sqlite").strip().lower()
if COACHING_STORE not in {"sqlite", "supabase"}:
    raise RuntimeError("COACHING_STORE must be 'sqlite' or 'supabase'.")
if COACHING_STORE == "supabase" and AUTH_PROVIDER != "supabase":
    raise RuntimeError("Supabase coaching requires Supabase authentication.")
RESOURCE_STORE = os.environ.get("RESOURCE_STORE", "sqlite").strip().lower()
if RESOURCE_STORE not in {"sqlite", "supabase"}:
    raise RuntimeError("RESOURCE_STORE must be 'sqlite' or 'supabase'.")
if RESOURCE_STORE == "supabase" and (AUTH_PROVIDER != "supabase" or COACHING_STORE != "supabase"):
    raise RuntimeError("Supabase resources require Supabase authentication and coaching.")
COHORT_MIN_GROUP_SIZE = settings.cohort_min_group_size
login_limiter = auth.LoginRateLimiter(
    settings.login_max_attempts,
    settings.login_window_seconds,
)
model_payload = None

SESSION_COOKIE = "lpu_session"
CSRF_COOKIE = "lpu_csrf"


def _set_auth_cookies(response, token: str, csrf_token: str, max_age: int):
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=max_age,
        httponly=True,
        secure=AUTH_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    # Readable by the SPA so it can echo the token in X-CSRF-Token.
    response.set_cookie(
        CSRF_COOKIE,
        csrf_token,
        max_age=max_age,
        httponly=False,
        secure=AUTH_COOKIE_SECURE,
        samesite="Lax",
        path="/",
    )
    return response


def _clear_auth_cookies(response):
    response.delete_cookie(
        SESSION_COOKIE, path="/", secure=AUTH_COOKIE_SECURE, samesite="Lax", httponly=True
    )
    response.delete_cookie(CSRF_COOKIE, path="/", secure=AUTH_COOKIE_SECURE, samesite="Lax")
    return response


def _remaining_seconds(expires_at: str) -> int:
    try:
        moment = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        return max(1, int((moment - datetime.now(timezone.utc)).total_seconds()))
    except (TypeError, ValueError):
        return SESSION_TTL_SECONDS


def require_auth(*roles: str, csrf: bool = True):
    """Resolve the session and enforce role plus CSRF requirements."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if AUTH_PROVIDER == "supabase":
                authorization = request.headers.get("Authorization", "")
                if not authorization.startswith("Bearer ") or not authorization[7:].strip():
                    return jsonify({"status": "error", "message": "Authentication required."}), 401
                token = authorization[7:].strip()
                try:
                    identity = supabase_auth.verify_access_token(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, token)
                    profile = supabase_auth.load_trusted_profile(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY, token, identity)
                    legacy_id = profile.get("legacy_id")
                    if type(legacy_id) is not int or legacy_id <= 0:
                        raise supabase_auth.InvalidAccessToken("Account mapping is not available.")
                    connection = auth._connection(AUTH_DATABASE_PATH)
                    try:
                        local = connection.execute(
                            "SELECT id,username,display_name,role,cohort,is_active FROM users WHERE id = ?", (legacy_id,)
                        ).fetchone()
                    finally:
                        connection.close()
                    # During the transition both trusted records must agree. A
                    # mismatch fails closed instead of granting stale privileges.
                    if (local is None or not local["is_active"] or local["username"] != profile.get("username")
                            or local["role"] != profile.get("role") or local["cohort"] != profile.get("cohort")):
                        raise supabase_auth.InvalidAccessToken("Account mapping is not available.")
                    user = {"id": local["id"], "username": local["username"], "display_name": local["display_name"],
                            "role": local["role"], "cohort": local["cohort"]}
                except supabase_auth.InvalidAccessToken:
                    return jsonify({"status": "error", "message": "Your session or account is invalid."}), 401
                except (supabase_auth.AuthServiceUnavailable, OSError):
                    return jsonify({"status": "error", "message": "Authentication service is unavailable."}), 503
                except Exception:
                    app.logger.exception("Supabase account lookup failed")
                    return jsonify({"status": "error", "message": "Authentication service is unavailable."}), 503
                g.current_user = user
                g.auth_provider = "supabase"
                g.supabase_user_id = identity
                g.supabase_access_token = token
                if roles and user["role"] not in roles:
                    return jsonify({"status": "error", "message": "You do not have permission to view this information."}), 403
                # Bearer tokens are explicitly attached by the client, unlike
                # ambient cookies; do not accept cookie auth in this mode.
                return view(*args, **kwargs)

            token = request.cookies.get(SESSION_COOKIE)
            record = auth.get_session(AUTH_DATABASE_PATH, token)
            if record is None:
                message = (
                    "Your session has expired. Please sign in again."
                    if token
                    else "Authentication required."
                )
                return jsonify({"status": "error", "message": message}), 401

            user = record["user"]
            g.current_user = user
            g.csrf_token = record["csrf_token"]
            g.session_token = token
            g.session_expires_at = record["expires_at"]
            g.auth_provider = "local"

            if roles and user["role"] not in roles:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "You do not have permission to view this information.",
                        }
                    ),
                    403,
                )

            if csrf and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
                supplied = request.headers.get("X-CSRF-Token", "")
                if not secrets.compare_digest(supplied, record["csrf_token"]):
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "Your session verification token is invalid. Refresh and retry.",
                            }
                        ),
                        403,
                    )
            return view(*args, **kwargs)

        return wrapper

    return decorator


def _login_response(user: dict, session: dict, status: int = 200):
    response = jsonify(
        {
            "status": "success",
            "data": {
                "user": user,
                "csrf_token": session["csrf_token"],
                "expires_at": session["expires_at"],
                "expires_in": session["expires_in"],
            },
        }
    )
    response.status_code = status
    return _set_auth_cookies(
        response, session["token"], session["csrf_token"], session["expires_in"]
    )


def _client_address() -> str:
    forwarded = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "")
    return (forwarded.split(",")[0].strip() or request.remote_addr or "unknown")[:64]


@app.before_request
def attach_request_context():
    g.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    g.request_started_at = time.perf_counter()


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "no-referrer")
    response.headers.setdefault(
        "Content-Security-Policy", "default-src 'none'; frame-ancestors 'none'"
    )
    response.headers["X-Request-ID"] = getattr(g, "request_id", "unknown")
    duration_ms = round((time.perf_counter() - g.request_started_at) * 1000, 2)
    record_request(request.method, request.path, response.status_code, duration_ms)
    app.logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s request_id=%s",
        request.method,
        request.path,
        response.status_code,
        duration_ms,
        getattr(g, "request_id", "unknown"),
    )
    return response


def get_model():
    """
    Lazy loads or auto-trains the model if not present.
    """
    global model_payload
    if model_payload is None:
        if not os.path.exists(MODEL_PATH):
            app.logger.info("Model file not found. Auto-training demo model...")
            model_payload = train_placement_model(save_path=MODEL_PATH)
        else:
            model_payload = load_model(MODEL_PATH)
    return model_payload


@app.route("/api/auth/login", methods=["POST"])
@app.route("/api/v1/auth/login", methods=["POST"])
def login():
    """Authenticate a provisioned account and start a server-side session."""
    if AUTH_PROVIDER != "local":
        return jsonify({"status": "error", "message": "Use Supabase sign-in for this deployment."}), 404
    if not request.is_json:
        return (
            jsonify(
                {"status": "error", "message": "Request content-type must be application/json."}
            ),
            400,
        )

    payload = request.get_json(silent=True) or {}
    username = auth.normalize_username(payload.get("username"))
    password = str(payload.get("password") or "")
    address = _client_address()

    retry_after = login_limiter.retry_after(address, username)
    if retry_after:
        response = jsonify(
            {
                "status": "error",
                "message": "Too many sign-in attempts. Try again later.",
            }
        )
        response.status_code = 429
        response.headers["Retry-After"] = str(retry_after)
        return response

    if not username or not password:
        login_limiter.record_failure(address, username)
        return jsonify({"status": "error", "message": "Invalid username or password."}), 401

    try:
        user = auth.authenticate(AUTH_DATABASE_PATH, username, password)
    except Exception:
        app.logger.exception("Authentication backend error")
        return jsonify({"status": "error", "message": "Sign-in is temporarily unavailable."}), 503

    if user is None:
        login_limiter.record_failure(address, username)
        return jsonify({"status": "error", "message": "Invalid username or password."}), 401

    login_limiter.reset(address, username)
    # Replace any session that was already attached to this browser.
    auth.delete_session(AUTH_DATABASE_PATH, request.cookies.get(SESSION_COOKIE))
    session = auth.create_session(AUTH_DATABASE_PATH, user["id"], SESSION_TTL_SECONDS)
    return _login_response(user, session)


@app.route("/api/auth/me", methods=["GET"])
@app.route("/api/v1/auth/me", methods=["GET"])
@require_auth(csrf=False)
def current_user():
    if g.auth_provider == "supabase":
        return jsonify({"status": "success", "data": {"user": g.current_user}}), 200
    max_age = _remaining_seconds(g.session_expires_at)
    response = jsonify(
        {
            "status": "success",
            "data": {
                "user": g.current_user,
                "csrf_token": g.csrf_token,
                "expires_at": g.session_expires_at,
                "expires_in": max_age,
            },
        }
    )
    return _set_auth_cookies(response, g.session_token, g.csrf_token, max_age)


@app.route("/api/auth/logout", methods=["POST"])
@app.route("/api/v1/auth/logout", methods=["POST"])
@require_auth()
def logout():
    """Revoke the current server-side session and clear the browser cookies."""
    if g.auth_provider == "supabase":
        return jsonify({"status": "success", "data": {"signed_out": True}}), 200
    auth.delete_session(AUTH_DATABASE_PATH, g.session_token)
    response = jsonify({"status": "success", "data": {"signed_out": True}})
    return _clear_auth_cookies(response)


@app.route("/api/health", methods=["GET"])
@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """
    Health check endpoint.
    """
    return (
        jsonify(
            {
                "status": "ok",
                "service": "LPU Placement Intelligence API",
                "model_loaded": model_payload is not None or os.path.exists(MODEL_PATH),
            }
        ),
        200,
    )


@app.route("/api/v1/metrics", methods=["GET"])
@require_auth("admin", csrf=False)
def metrics():
    """Return process-local operational metrics without student data."""
    return jsonify({"status": "success", "data": snapshot()}), 200


@app.route("/api/model-info", methods=["GET"])
@app.route("/api/v1/model-info", methods=["GET"])
@require_auth(csrf=False)
def model_info():
    """
    Returns model training metrics, target thresholds, and feature metadata.
    """
    try:
        payload = get_model()
        return (
            jsonify(
                {
                    "status": "success",
                    "model_version": payload.get("model_version", "1.0.0"),
                    "trained_at": payload.get("trained_at"),
                    "features": payload.get("feature_names"),
                    "feature_metadata": payload.get("feature_metadata"),
                    "target_thresholds": payload.get("target_thresholds"),
                    "metrics": payload.get("metrics"),
                    "calibration": payload.get("calibration"),
                    "calibration_metrics": payload.get("calibration_metrics"),
                    "feature_importance": payload.get("feature_importance"),
                }
            ),
            200,
        )
    except Exception:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Unable to retrieve model information.",
                }
            ),
            500,
        )


@app.route("/api/explain/shap", methods=["POST"])
@require_auth()
def explain_shap():
    """Explain the current model on demand without saving the student's inputs."""
    if not request.is_json:
        return jsonify({'status': 'error', 'message': 'Request content-type must be application/json.'}), 400
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Input payload must be a JSON object.'}), 400
    valid, student = validate_student_input(data.get('student'))
    if not valid:
        return jsonify({'status': 'error', 'message': student}), 400
    try:
        payload = get_model()
        if data.get('model_version') != payload.get('model_version', 'unversioned'):
            return jsonify({'status': 'error', 'message': 'The model has changed. Analyze your profile again before requesting SHAP.'}), 409
        result = shap_explanations.explain_tree_prediction(payload, student)
        return jsonify({'status': 'success', 'data': result}), 200
    except shap_explanations.ShapExplanationUnavailable:
        return jsonify({'status': 'error', 'message': 'SHAP is unavailable for the current model. The existing factor explanation is still available.'}), 503
    except Exception:
        app.logger.exception('SHAP explanation failed')
        return jsonify({'status': 'error', 'message': 'Unable to explain this assessment. Please retry.'}), 500


@app.route("/api/predict", methods=["POST"])
@app.route("/api/v1/predict", methods=["POST"])
@require_auth()
def predict():
    """
    Receives student profile, validates input, and returns readiness score,
    skill gaps, explainable factors, and personalized improvement plan.
    """
    if not request.is_json:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Request content-type must be application/json.",
                }
            ),
            400,
        )

    data = request.get_json()
    is_valid, validation_result = validate_student_input(data)

    if not is_valid:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": validation_result,
                }
            ),
            400,
        )

    sanitized_student = validation_result

    try:
        payload = get_model()
        prediction_result = predict_student_readiness(payload, sanitized_student)
        return (
            jsonify(
                {
                    "status": "success",
                    "data": prediction_result,
                }
            ),
            200,
        )
    except Exception as e:
        app.logger.error(f"Prediction error: {str(e)}")
        return (
            jsonify(
                {
                    "status": "error",
                    "message": "Unable to calculate readiness prediction.",
                }
            ),
            500,
        )


@app.route("/api/history", methods=["POST"])
@app.route("/api/v1/history", methods=["POST"])
@require_auth()
def save_history():
    """Persist an anonymous assessment snapshot for the supplied profile."""
    if not request.is_json:
        return (
            jsonify(
                {"status": "error", "message": "Request content-type must be application/json."}
            ),
            400,
        )
    data = request.get_json()
    student = data.get("student") if isinstance(data, dict) else None
    prediction = data.get("prediction") if isinstance(data, dict) else None
    is_valid, validation_result = validate_student_input(student)
    prediction_is_valid, prediction_error = validate_prediction_snapshot(prediction)
    if not is_valid or not prediction_is_valid:
        message = validation_result if not is_valid else prediction_error
        return jsonify({"status": "error", "message": message}), 400
    try:
        # Recalculate on the server so a browser cannot attach a forged score or
        # model version to the persisted assessment history.
        trusted_prediction = predict_student_readiness(get_model(), validation_result)
        saved = save_assessment(
            validation_result,
            trusted_prediction,
            database_path=HISTORY_DATABASE_PATH,
            user_id=g.current_user["id"],
            cohort=g.current_user["cohort"],
        )
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"], action="save_assessment", subject_id=g.current_user["id"])
        return jsonify({"status": "success", "data": saved}), 201
    except Exception as exc:
        app.logger.error("History persistence error: %s", exc)
        return jsonify({"status": "error", "message": "Unable to save assessment history."}), 500


@app.route("/api/history/query", methods=["POST"])
@app.route("/api/v1/history/query", methods=["POST"])
@require_auth()
def query_history():
    """Return the caller's history for a profile without putting features in a URL."""
    if not request.is_json:
        return (
            jsonify(
                {"status": "error", "message": "Request content-type must be application/json."}
            ),
            400,
        )
    data = request.get_json(silent=True) or {}
    profile = data.get("student") if isinstance(data, dict) else None
    is_valid, validation_result = validate_student_input(profile)
    if not is_valid:
        return jsonify({"status": "error", "message": validation_result}), 400
    try:
        return (
            jsonify(
                {
                    "status": "success",
                    "data": list_assessments(
                        validation_result,
                        database_path=HISTORY_DATABASE_PATH,
                        user_id=g.current_user["id"],
                    ),
                }
            ),
            200,
        )
    except Exception as exc:
        app.logger.error("History retrieval error: %s", exc)
        return (
            jsonify({"status": "error", "message": "Unable to retrieve assessment history."}),
            500,
        )


@app.route("/api/history", methods=["GET"])
@app.route("/api/v1/history", methods=["GET"])
@require_auth(csrf=False)
def get_history():
    """Deprecated GET form; retained for compatibility with older clients."""
    profile = request.args.to_dict()
    is_valid, validation_result = validate_student_input(profile)
    if not is_valid:
        return jsonify({"status": "error", "message": validation_result}), 400
    try:
        return (
            jsonify(
                {
                    "status": "success",
                    "data": list_assessments(
                        validation_result,
                        database_path=HISTORY_DATABASE_PATH,
                        user_id=g.current_user["id"],
                    ),
                }
            ),
            200,
        )
    except Exception as exc:
        app.logger.error("History retrieval error: %s", exc)
        return (
            jsonify({"status": "error", "message": "Unable to retrieve assessment history."}),
            500,
        )


@app.route("/api/cohort-analytics", methods=["GET"])
@app.route("/api/v1/cohort-analytics", methods=["GET"])
@require_auth(*auth.STAFF_ROLES, csrf=False)
def get_cohort_analytics():
    """Return aggregate analytics scoped to the caller's role and cohort."""
    user = g.current_user
    if user["role"] == "mentor":
        if not user.get("cohort"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "No cohort is assigned to this mentor account.",
                    }
                ),
                403,
            )
        cohort = user["cohort"]
    else:
        # Placement officers and administrators see institution-wide aggregates.
        cohort = None

    try:
        payload = get_model()
        analytics = cohort_analytics(
            payload.get("target_thresholds", {}),
            database_path=HISTORY_DATABASE_PATH,
            cohort=cohort,
            minimum_group_size=COHORT_MIN_GROUP_SIZE,
        )
        return jsonify({"status": "success", "data": analytics}), 200
    except Exception as exc:
        app.logger.error("Cohort analytics error: %s", exc)
        return (
            jsonify({"status": "error", "message": "Unable to retrieve cohort analytics."}),
            500,
        )


@app.route("/api/student/profile", methods=["GET", "PUT"])
@app.route("/api/v1/student/profile", methods=["GET", "PUT"])
@require_auth("student")
def student_profile():
    """Return the signed-in student's latest saved assessment and target role."""
    user_id = g.current_user["id"]
    if request.method == "GET":
        return jsonify({"status": "success", "data": collaboration.get_student_profile(HISTORY_DATABASE_PATH, user_id)}), 200
    data = request.get_json(silent=True) or {}
    try:
        saved = collaboration.save_target_role(HISTORY_DATABASE_PATH, user_id, data.get("target_roles", data.get("target_role", "")))
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=user_id, action="update_target_roles", subject_id=user_id)
        return jsonify({"status": "success", "data": saved}), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception as exc:
        app.logger.error("Student target-role update failed: %s", exc)
        return jsonify({"status": "error", "message": "Unable to save your target role."}), 500


def _target_student(student_id: int):
    """Look up a student account without exposing credentials or sessions."""
    connection = auth._connection(AUTH_DATABASE_PATH)
    try:
        return connection.execute(
            "SELECT id,username,display_name,role,cohort,is_active FROM users WHERE id=?",
            (student_id,),
        ).fetchone()
    finally:
        connection.close()


def _mentor_assigned_ids() -> set[int]:
    if hasattr(g, 'mentor_assigned_ids'):
        return g.mentor_assigned_ids
    if COACHING_STORE == 'supabase':
        result = _coaching_rpc('mentor_assignment_mine', {})
        values = result.get('students')
        if not isinstance(values, list) or any(not isinstance(value, dict) or type(value.get('id')) is not int for value in values):
            raise supabase_coaching.CoachingUnavailable('Assignment service returned invalid data.')
        local = {item['id']: item for item in auth.list_users(AUTH_DATABASE_PATH) if item['role'] == 'student' and item['is_active']}
        g.mentor_assigned_ids = {value['id'] for value in values if value['id'] in local
            and local[value['id']]['username'] == value.get('username') and local[value['id']]['cohort'] == value.get('cohort')}
    else:
        db = auth._connection(AUTH_DATABASE_PATH)
        try:
            g.mentor_assigned_ids = {row['student_id'] for row in db.execute('SELECT student_id FROM mentor_assignments WHERE mentor_id=?', (g.current_user['id'],))}
        finally:
            db.close()
    return g.mentor_assigned_ids


def _can_access_student(student_id: int, *, write: bool = False) -> tuple[bool, str]:
    actor = g.current_user
    target = _target_student(student_id)
    if target is None or not target["is_active"] or target["role"] != "student":
        return False, "Student record not found."
    if actor["role"] == "student":
        return (actor["id"] == student_id, "You can only access your own student records.")
    if actor["role"] == "mentor":
        if (not actor.get("cohort") or actor["cohort"] != target["cohort"]) and student_id not in _mentor_assigned_ids():
            return False, "You can only access students in your cohort or assigned to you."
        return True, ""
    if actor["role"] in {"admin", "placement_officer"}:
        return True, ""
    return False, "You do not have permission to access this student record."


def _coaching_rpc(name: str, payload: dict):
    return supabase_coaching.call(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY,
                                  g.supabase_access_token, name, payload)


def _coaching_list(student_id: int, *, include_private: bool, access_token: str | None = None):
    if COACHING_STORE == "supabase":
        # Database RPC independently enforces the authenticated user's access.
        if access_token is not None:
            return supabase_coaching.call(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY,
                                          access_token, "coaching_list", {"p_student_id": student_id})
        return _coaching_rpc("coaching_list", {"p_student_id": student_id})
    return collaboration.list_records(HISTORY_DATABASE_PATH, student_id, include_private=include_private)


@app.route("/api/admin/mentors", methods=["GET"])
@app.route("/api/v1/admin/mentors", methods=["GET"])
@require_auth("admin", csrf=False)
def admin_mentor_directory():
    """List local mentor accounts without exposing credentials or claiming Supabase access."""
    try:
        mentors = [{key: account[key] for key in ('id', 'username', 'display_name', 'cohort', 'is_active')}
                   for account in auth.list_users(AUTH_DATABASE_PATH) if account['role'] == 'mentor']
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user['id'], action='view_mentor_directory')
        return jsonify({'status': 'success', 'data': mentors}), 200
    except Exception:
        app.logger.exception('Mentor directory retrieval failed')
        return jsonify({'status': 'error', 'message': 'Mentor directory is unavailable. Please retry.'}), 500


@app.route("/api/admin/students", methods=["GET"])
@app.route("/api/v1/admin/students", methods=["GET"])
@require_auth("admin", csrf=False)
def admin_student_directory():
    """List local student accounts, including those without assessments."""
    try:
        students = [{key: account[key] for key in ('id', 'username', 'display_name', 'cohort', 'is_active')}
                    for account in auth.list_users(AUTH_DATABASE_PATH) if account['role'] == 'student']
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user['id'], action='view_student_directory')
        return jsonify({'status': 'success', 'data': students}), 200
    except Exception:
        app.logger.exception('Student directory retrieval failed')
        return jsonify({'status': 'error', 'message': 'Student directory is unavailable. Please retry.'}), 500


@app.route("/api/admin/mentor-assignments", methods=["GET"])
@app.route("/api/v1/admin/mentor-assignments", methods=["GET"])
@require_auth("admin", csrf=False)
def admin_mentor_assignments():
    if COACHING_STORE == 'supabase':
        try:
            result = _coaching_rpc('mentor_assignment_admin_list', {})
            accounts = auth.list_users(AUTH_DATABASE_PATH)
            def matching_ids(key, role):
                profiles = result.get(key)
                if not isinstance(profiles, list):
                    raise supabase_coaching.CoachingUnavailable('Assignment service returned invalid data.')
                local = {item['id']: item for item in accounts if item['role'] == role and item['is_active']}
                return [p['id'] for p in profiles if isinstance(p, dict) and type(p.get('id')) is int and p['id'] in local
                        and local[p['id']]['username'] == p.get('username') and local[p['id']]['cohort'] == p.get('cohort')]
            mentor_ids = matching_ids('mapped_mentors', 'mentor')
            student_ids = matching_ids('mapped_students', 'student')
            assignments = result.get('assignments')
            if not isinstance(assignments, list):
                raise supabase_coaching.CoachingUnavailable('Assignment service returned invalid data.')
            for item in assignments:
                item['valid'] = bool(item.get('valid') and item.get('student_id') in student_ids and item.get('mentor_id') in mentor_ids)
            return jsonify({'status': 'success', 'data': assignments, 'mapped_mentor_ids': mentor_ids, 'mapped_student_ids': student_ids}), 200
        except supabase_coaching.CoachingForbidden:
            return jsonify({'status': 'error', 'message': 'You cannot view mentor assignments.'}), 403
        except supabase_coaching.CoachingUnavailable:
            return jsonify({'status': 'error', 'message': 'Mentor assignments are unavailable. Please retry.'}), 503
    connection = auth._connection(AUTH_DATABASE_PATH)
    try:
        rows = connection.execute("""SELECT a.student_id, a.mentor_id, m.display_name,
            CASE WHEN s.is_active = 1 AND s.role = 'student' AND m.is_active = 1
                AND m.role = 'mentor'
                THEN 1 ELSE 0 END AS valid
            FROM mentor_assignments a JOIN users s ON s.id = a.student_id
            JOIN users m ON m.id = a.mentor_id""").fetchall()
        return jsonify({'status': 'success', 'data': [dict(row) for row in rows]}), 200
    finally:
        connection.close()


@app.route("/api/admin/students/<int:student_id>/mentor", methods=["POST"])
@app.route("/api/v1/admin/students/<int:student_id>/mentor", methods=["POST"])
@require_auth("admin")
def assign_student_mentor(student_id):
    data = request.get_json(silent=True)
    if not isinstance(data, dict) or 'mentor_id' not in data:
        return jsonify({'status': 'error', 'message': 'Choose a mentor or clear the assignment.'}), 400
    mentor_id = data['mentor_id']
    if mentor_id is not None and (type(mentor_id) is not int or mentor_id <= 0):
        return jsonify({'status': 'error', 'message': 'Invalid mentor selection.'}), 400
    if COACHING_STORE == 'supabase':
        connection = auth._connection(AUTH_DATABASE_PATH)
        try:
            student = connection.execute("SELECT id,username,cohort FROM users WHERE id=? AND role='student' AND is_active=1", (student_id,)).fetchone()
            mentor = None if mentor_id is None else connection.execute("SELECT id,username,cohort FROM users WHERE id=? AND role='mentor' AND is_active=1", (mentor_id,)).fetchone()
        finally:
            connection.close()
        if not student:
            return jsonify({'status': 'error', 'message': 'Active student not found.'}), 404
        if mentor_id is not None and not mentor:
            return jsonify({'status': 'error', 'message': 'Choose an active mentor.'}), 400
        try:
            result = _coaching_rpc('mentor_assignment_set', {'p_student_id': student_id, 'p_mentor_id': mentor_id,
                'p_student_username': student['username'], 'p_student_cohort': student['cohort'],
                'p_mentor_username': mentor['username'] if mentor else None, 'p_mentor_cohort': mentor['cohort'] if mentor else None})
            return jsonify({'status': 'success', 'data': result}), 200
        except supabase_coaching.CoachingForbidden:
            return jsonify({'status': 'error', 'message': 'You cannot change this assignment.'}), 403
        except supabase_coaching.CoachingUnavailable:
            return jsonify({'status': 'error', 'message': 'Mentor assignments are unavailable. Please retry.'}), 503
        except ValueError:
            return jsonify({'status': 'error', 'message': 'The student and mentor must have active linked Supabase profiles.'}), 400
    connection = auth._connection(AUTH_DATABASE_PATH)
    try:
        connection.execute('BEGIN IMMEDIATE')
        student = connection.execute('SELECT role, cohort, is_active FROM users WHERE id = ?', (student_id,)).fetchone()
        if not student or student['role'] != 'student' or not student['is_active']:
            return jsonify({'status': 'error', 'message': 'Active student not found.'}), 404
        if mentor_id is not None:
            mentor = connection.execute('SELECT role, cohort, is_active FROM users WHERE id = ?', (mentor_id,)).fetchone()
            if not mentor or mentor['role'] != 'mentor' or not mentor['is_active']:
                return jsonify({'status': 'error', 'message': 'Choose an active mentor.'}), 400
            connection.execute('''INSERT INTO mentor_assignments(student_id, mentor_id, assigned_by, updated_at)
                VALUES (?, ?, ?, ?) ON CONFLICT(student_id) DO UPDATE SET
                mentor_id=excluded.mentor_id, assigned_by=excluded.assigned_by, updated_at=excluded.updated_at''',
                (student_id, mentor_id, g.current_user['id'], auth._isoformat(auth._utcnow())))
        else:
            connection.execute('DELETE FROM mentor_assignments WHERE student_id = ?', (student_id,))
        connection.execute('INSERT INTO mentor_assignment_events(student_id, mentor_id, actor_id, created_at) VALUES (?, ?, ?, ?)',
                           (student_id, mentor_id, g.current_user['id'], auth._isoformat(auth._utcnow())))
        connection.commit()
    finally:
        connection.close()
    try:
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user['id'], action='update_mentor_assignment', subject_id=student_id)
    except Exception:
        app.logger.exception('Unable to copy mentor assignment event to staff audit')
    return jsonify({'status': 'success', 'data': {'student_id': student_id, 'mentor_id': mentor_id}}), 200


@app.route("/api/mentor/students", methods=["GET"])
@app.route("/api/v1/mentor/students", methods=["GET"])
@require_auth(*auth.STAFF_ROLES, csrf=False)
def get_mentor_students():
    """Return assessed cohort students and individually assigned students."""
    user = g.current_user
    cohort = user.get("cohort") if user["role"] == "mentor" else None
    if user["role"] == "mentor" and not cohort:
        return jsonify({"status": "error", "message": "No cohort is assigned to this mentor account."}), 403
    try:
        assigned_ids = _mentor_assigned_ids() if user['role'] == 'mentor' else set()
        students = collaboration.latest_students(HISTORY_DATABASE_PATH, AUTH_DATABASE_PATH, cohort=None)
        if user['role'] == 'mentor':
            students = [student for student in students if student['cohort'] == cohort or student['user_id'] in assigned_ids]
            seen_ids = {student['user_id'] for student in students}
            cv_db = collaboration._connect(HISTORY_DATABASE_PATH)
            try:
                cv_status = {row['student_id']: row['status'] for row in cv_db.execute('''SELECT c.student_id,c.status
                    FROM cv_submissions c JOIN (SELECT student_id,max(id) AS latest_id FROM cv_submissions GROUP BY student_id) latest
                    ON latest.latest_id=c.id''')}
            finally:
                cv_db.close()
            for account in auth.list_users(AUTH_DATABASE_PATH):
                if (account['id'] in assigned_ids or (account['cohort'] == cohort and account['id'] in cv_status)) and account['id'] not in seen_ids and account['role'] == 'student' and account['is_active']:
                    profile = collaboration.get_student_profile(HISTORY_DATABASE_PATH, account['id'])
                    students.append({'user_id': account['id'], 'username': account['username'], 'display_name': account['display_name'],
                        'cohort': account['cohort'], 'profile': {}, 'readiness_score': None, 'readiness_category': 'Not assessed',
                        'created_at': None, 'previous_score': None, 'target_roles': profile['target_roles'],
                        'target_role': profile['target_role'], 'evidence': collaboration.list_evidence(HISTORY_DATABASE_PATH, account['id'])})
        staff = [account for account in auth.list_users(AUTH_DATABASE_PATH)
                 if account['is_active'] and account['role'] == 'mentor']
        if COACHING_STORE == 'supabase':
            if user['role'] == 'admin':
                data = _coaching_rpc('mentor_assignment_admin_list', {})
                assignments = {row['student_id']: row['mentor_id'] for row in data.get('assignments', []) if row.get('valid')}
            else:
                assignments = {student_id: user['id'] for student_id in assigned_ids}
        else:
            connection = auth._connection(AUTH_DATABASE_PATH)
            try:
                assignments = {row['student_id']: row['mentor_id'] for row in connection.execute(
                    'SELECT student_id, mentor_id FROM mentor_assignments').fetchall()}
            finally:
                connection.close()
        # Every timeline is still checked by the Postgres RPC using this user's
        # token. Fetching them serially made a modest roster exceed the browser's
        # timeout; bounded concurrency avoids multiplying network round trips.
        timelines = None
        if COACHING_STORE == 'supabase' and students:
            access_token = g.supabase_access_token
            with ThreadPoolExecutor(max_workers=min(8, len(students))) as executor:
                pending = {
                    student['user_id']: executor.submit(
                        _coaching_list, student['user_id'],
                        include_private=(user['role'] != 'mentor' or user['cohort'] == cohort),
                        access_token=access_token,
                    ) for student in students
                }
                timelines = {}
                for student_id, future in pending.items():
                    try:
                        timelines[student_id] = future.result()
                    except (supabase_coaching.CoachingForbidden, supabase_coaching.CoachingUnavailable, ValueError) as exc:
                        timelines[student_id] = exc
        permitted_students = []
        for student in students:
            if user['role'] == 'mentor':
                student['cv_status'] = cv_status.get(student['user_id'])
            collaboration.audit(HISTORY_DATABASE_PATH, actor_id=user["id"], action="view_student_list", subject_id=student["user_id"])
            try:
                if timelines is not None:
                    result = timelines[student['user_id']]
                    if isinstance(result, Exception):
                        raise result
                    student["coaching_records"] = result
                else:
                    student["coaching_records"] = _coaching_list(
                        student["user_id"], include_private=(user["role"] != "mentor" or user["cohort"] == cohort))
                student["coaching_available"] = True
            except (supabase_coaching.CoachingForbidden, supabase_coaching.CoachingUnavailable, ValueError):
                # Never substitute SQLite coaching or treat a denied/unavailable
                # timeline as empty. Mentors need both systems to authorize it;
                # fail the roster rather than silently hide inaccessible rows.
                if user["role"] == "mentor":
                    raise
                student["coaching_records"] = None
                student["coaching_available"] = False
            student["cohort_mentors"] = [
                {"id": mentor["id"], "display_name": mentor["display_name"]}
                for mentor in staff if mentor["cohort"] and mentor["cohort"] == student["cohort"]
            ]
            student["assigned_mentor"] = next(({'id': mentor['id'], 'display_name': mentor['display_name']} for mentor in staff
                if mentor['id'] == assignments.get(student['user_id'])), None)
            permitted_students.append(student)
        return jsonify({"status": "success", "data": permitted_students}), 200
    except (supabase_coaching.CoachingForbidden, supabase_coaching.CoachingUnavailable):
        return jsonify({"status": "error", "message": "Student assignments or coaching are unavailable. Please retry."}), 503
    except Exception:
        app.logger.error("Student roster retrieval failed")
        return jsonify({"status": "error", "message": "Unable to retrieve the permitted student roster."}), 500


RESOURCE_MAX_BYTES = 5 * 1024 * 1024


def _deliver_resource_notification(student_id, resource_id):
    """Retry an existing durable intent using the current staff member's token.

    The remote RPC deduplicates using the resource and student IDs. Keep the
    SQLite write lock while sending so an authorized delete cannot race a
    retry and create a notification for a resource already removed.
    """
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('''SELECT r.title, r.author_id, o.status FROM study_resources r
            JOIN resource_notification_outbox o ON o.resource_id=r.id
            WHERE r.id=? AND r.student_id=?''', (resource_id, student_id)).fetchone()
        if row is None:
            db.rollback()
            return None
        if row['author_id'] != g.current_user['id'] and g.current_user['role'] != 'admin':
            db.rollback()
            raise PermissionError('Only the uploader or an administrator can retry this notification.')
        if row['status'] == 'sent':
            db.commit()
            return True
        now = collaboration._now()
        try:
            response = _coaching_rpc('resource_shared_notify', {'p_student_id': student_id,
                'p_resource_id': resource_id, 'p_title': row['title']})
            if not isinstance(response, dict) or response.get('sent') is not True:
                raise supabase_coaching.CoachingUnavailable('Invalid notification response.')
        except (supabase_coaching.CoachingForbidden, supabase_coaching.CoachingUnavailable, ValueError, OSError):
            db.execute('UPDATE resource_notification_outbox SET attempts=attempts+1, last_attempt_at=? WHERE resource_id=?', (now, resource_id))
            db.commit()
            return False
        db.execute("UPDATE resource_notification_outbox SET status='sent', attempts=attempts+1, last_attempt_at=?, sent_at=? WHERE resource_id=?", (now, now, resource_id))
        db.commit()
        return True
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/resources", methods=["GET", "POST"])
@app.route("/api/v1/students/<int:student_id>/resources", methods=["GET", "POST"])
@require_auth()
def student_resources(student_id):
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403 if message.startswith('You') else 404
    if request.method == 'POST' and g.current_user['role'] not in auth.STAFF_ROLES:
        return jsonify({'status': 'error', 'message': 'Only permitted staff can share resources.'}), 403
    if request.method == 'POST':
        request.max_content_length = RESOURCE_MAX_BYTES + 65536
        upload = request.files.get('file')
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', 'General').strip()
        filename = secure_filename(upload.filename or '') if upload else ''
        ext = os.path.splitext(filename)[1].lower()
        if not upload or not filename or not 1 <= len(title) <= 140 or len(description) > 2000:
            return jsonify({'status': 'error', 'message': 'Provide a title, a file, and a description of at most 2000 characters.'}), 400
        if category not in {'General', 'Coding', 'Technical skills', 'Aptitude', 'Communication', 'Resume', 'Interview'}:
            return jsonify({'status': 'error', 'message': 'Choose a supported resource category.'}), 400
        if ext not in {'.pdf', '.docx', '.pptx', '.txt', '.png', '.jpg', '.jpeg'}:
            return jsonify({'status': 'error', 'message': 'Use a PDF, DOCX, PPTX, TXT, PNG, or JPG file.'}), 400
        content = upload.stream.read(RESOURCE_MAX_BYTES + 1)
        if not content or len(content) > RESOURCE_MAX_BYTES:
            return jsonify({'status': 'error', 'message': 'Choose a non-empty file of at most 5 MB.'}), 400
        signatures = {'.pdf': b'%PDF-', '.docx': b'PK\x03\x04', '.pptx': b'PK\x03\x04',
                      '.png': b'\x89PNG\r\n\x1a\n', '.jpg': b'\xff\xd8\xff', '.jpeg': b'\xff\xd8\xff'}
        if (ext in signatures and not content.startswith(signatures[ext])) or (ext == '.txt' and b'\x00' in content):
            return jsonify({'status': 'error', 'message': 'The file contents do not match the selected type.'}), 400
        if RESOURCE_STORE == 'supabase':
            try:
                raw_upload_key = request.form.get('upload_key', '').strip()
                upload_key = str(uuid.UUID(raw_upload_key)) if raw_upload_key else str(uuid.uuid4())
                created = _coaching_rpc('study_resource_create', {'p_student_id': student_id, 'p_title': title,
                    'p_description': description, 'p_filename': filename, 'p_category': category,
                    'p_content_base64': base64.b64encode(content).decode('ascii'), 'p_upload_key': upload_key})
                if type(created.get('id')) is not int or created.get('notification_sent') is not True:
                    raise supabase_coaching.CoachingUnavailable('Invalid resource response.')
                return jsonify({'status': 'success', 'data': {'id': created['id'], 'notification_sent': True}}), 201
            except supabase_coaching.CoachingForbidden:
                return jsonify({'status': 'error', 'message': 'You do not have permission to share this resource.'}), 403
            except ValueError:
                return jsonify({'status': 'error', 'message': 'The resource details could not be accepted.'}), 400
            except supabase_coaching.CoachingUnavailable:
                return jsonify({'status': 'error', 'message': 'Study resources are unavailable. Please retry.'}), 503
        db = collaboration._connect(HISTORY_DATABASE_PATH)
        try:
            cursor = db.execute('''INSERT INTO study_resources(student_id,author_id,title,description,filename,content,created_at,category)
                VALUES (?,?,?,?,?,?,?,?)''', (student_id, g.current_user['id'], title, description, filename, content, collaboration._now(), category))
            if COACHING_STORE == 'supabase':
                db.execute('INSERT INTO resource_notification_outbox(resource_id) VALUES (?)', (cursor.lastrowid,))
            db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                       (g.current_user['id'], 'share_study_resource', student_id, collaboration._now()))
            db.commit()
            resource_id = cursor.lastrowid
        finally:
            db.close()
        notification_sent = None
        if COACHING_STORE == 'supabase':
            try:
                notification_sent = _deliver_resource_notification(student_id, resource_id) is True
            except Exception:
                # The upload and pending intent are already committed. Do not
                # ask the caller to upload a second copy if delivery fails.
                app.logger.exception('Resource notification attempt failed')
                notification_sent = False
        return jsonify({'status': 'success', 'data': {'id': resource_id, 'notification_sent': notification_sent}}), 201
    if RESOURCE_STORE == 'supabase':
        try:
            rows = _coaching_rpc('study_resource_list', {'p_student_id': student_id})
            return jsonify({'status': 'success', 'data': rows}), 200
        except supabase_coaching.CoachingForbidden:
            return jsonify({'status': 'error', 'message': 'You do not have permission to view these resources.'}), 403
        except (supabase_coaching.CoachingUnavailable, ValueError):
            return jsonify({'status': 'error', 'message': 'Study resources are unavailable. Please retry.'}), 503
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        rows = db.execute('''SELECT r.id, r.student_id, r.author_id, r.title, r.description, r.filename,
            length(r.content) AS size, r.created_at, r.category, o.status AS notification_status
            FROM study_resources r LEFT JOIN resource_notification_outbox o ON o.resource_id=r.id
            WHERE r.student_id=? ORDER BY r.created_at DESC,r.id DESC''', (student_id,)).fetchall()
        return jsonify({'status': 'success', 'data': [dict(row) for row in rows]}), 200
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/resources/<int:resource_id>/notification", methods=["POST"])
@app.route("/api/v1/students/<int:student_id>/resources/<int:resource_id>/notification", methods=["POST"])
@require_auth("mentor", "admin", "placement_officer")
def retry_study_resource_notification(student_id, resource_id):
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    if RESOURCE_STORE == 'supabase':
        return jsonify({'status': 'error', 'message': 'Postgres resource notifications are sent with the upload.'}), 409
    if COACHING_STORE != 'supabase':
        return jsonify({'status': 'error', 'message': 'Resource notifications require Supabase mode.'}), 409
    try:
        delivered = _deliver_resource_notification(student_id, resource_id)
        if delivered is None:
            return jsonify({'status': 'error', 'message': 'No pending notification was found for this resource.'}), 404
        if not delivered:
            return jsonify({'status': 'error', 'message': 'Notification could not be delivered. Please try again.'}), 503
        return jsonify({'status': 'success', 'data': {'notification_sent': True}}), 200
    except PermissionError as exc:
        return jsonify({'status': 'error', 'message': str(exc)}), 403


@app.route("/api/students/<int:student_id>/resources/<int:resource_id>", methods=["DELETE"])
@app.route("/api/v1/students/<int:student_id>/resources/<int:resource_id>", methods=["DELETE"])
@require_auth("mentor", "admin", "placement_officer")
def delete_study_resource(student_id, resource_id):
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    if RESOURCE_STORE == 'supabase':
        try:
            deleted = _coaching_rpc('study_resource_delete', {'p_student_id': student_id, 'p_resource_id': resource_id})
            if deleted.get('deleted') is not True:
                raise supabase_coaching.CoachingUnavailable('Invalid deletion response.')
            return jsonify({'status': 'success', 'message': 'Resource removed.'}), 200
        except supabase_coaching.CoachingForbidden:
            return jsonify({'status': 'error', 'message': 'You do not have permission to remove this resource.'}), 403
        except (supabase_coaching.CoachingUnavailable, ValueError):
            return jsonify({'status': 'error', 'message': 'Study resources are unavailable. Please retry.'}), 503
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        row = db.execute('SELECT author_id FROM study_resources WHERE id=? AND student_id=?', (resource_id, student_id)).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Resource not found.'}), 404
        if row['author_id'] != g.current_user['id'] and g.current_user['role'] != 'admin':
            return jsonify({'status': 'error', 'message': 'Only the uploader or an administrator can remove this resource.'}), 403
        db.execute('DELETE FROM study_resources WHERE id=? AND student_id=?', (resource_id, student_id))
        db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                   (g.current_user['id'], 'delete_study_resource', student_id, collaboration._now()))
        db.commit()
        return jsonify({'status': 'success', 'message': 'Resource removed.'}), 200
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/resources/<int:resource_id>/download", methods=["GET"])
@app.route("/api/v1/students/<int:student_id>/resources/<int:resource_id>/download", methods=["GET"])
@require_auth(csrf=False)
def download_student_resource(student_id, resource_id):
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403 if message.startswith('You') else 404
    if RESOURCE_STORE == 'supabase':
        try:
            result = _coaching_rpc('study_resource_download', {'p_student_id': student_id, 'p_resource_id': resource_id})
            filename = result.get('filename')
            encoded = result.get('content_base64')
            if not isinstance(filename, str) or not filename or secure_filename(filename) != filename or not isinstance(encoded, str) or len(encoded) > 6990508:
                raise supabase_coaching.CoachingUnavailable('Invalid resource response.')
            content = base64.b64decode(encoded, validate=True)
            if not content or len(content) > RESOURCE_MAX_BYTES:
                raise supabase_coaching.CoachingUnavailable('Invalid resource response.')
            response = send_file(io.BytesIO(content), mimetype='application/octet-stream', as_attachment=True, download_name=filename)
            response.headers['Cache-Control'] = 'private, no-store'
            return response
        except supabase_coaching.CoachingForbidden:
            return jsonify({'status': 'error', 'message': 'You do not have permission to download this resource.'}), 403
        except (supabase_coaching.CoachingUnavailable, ValueError, binascii.Error):
            return jsonify({'status': 'error', 'message': 'Study resources are unavailable. Please retry.'}), 503
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        row = db.execute('SELECT filename,content FROM study_resources WHERE id=? AND student_id=?', (resource_id, student_id)).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Resource not found.'}), 404
        if g.current_user['role'] in auth.STAFF_ROLES:
            db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                       (g.current_user['id'], 'download_study_resource', student_id, collaboration._now()))
            db.commit()
        response = send_file(io.BytesIO(row['content']), mimetype='application/octet-stream', as_attachment=True, download_name=row['filename'])
        response.headers['Cache-Control'] = 'private, no-store'
        return response
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/coaching", methods=["GET", "POST"])
@app.route("/api/v1/students/<int:student_id>/coaching", methods=["GET", "POST"])
@require_auth()
def student_coaching(student_id: int):
    """Read/add actions and mentor records for a self or assigned-cohort student."""
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({"status": "error", "message": message}), 403 if message.startswith("You") else 404
    actor = g.current_user
    if request.method == "GET":
        is_staff = actor["role"] in auth.STAFF_ROLES
        if is_staff and COACHING_STORE == "sqlite":
            collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="view_coaching_timeline", subject_id=student_id)
        try:
            return jsonify({"status": "success", "data": _coaching_list(student_id, include_private=is_staff)}), 200
        except supabase_coaching.CoachingForbidden:
            return jsonify({"status": "error", "message": "You do not have access to this coaching record."}), 403
        except supabase_coaching.CoachingUnavailable:
            return jsonify({"status": "error", "message": "Coaching service is unavailable. Please retry."}), 503
    data = request.get_json(silent=True) or {}
    kind = str(data.get("kind", "goal"))
    if actor["role"] == "student" and kind != "goal":
        return jsonify({"status": "error", "message": "Students can create action-plan goals only."}), 403
    if actor["role"] == "mentor" and kind not in collaboration.KINDS:
        return jsonify({"status": "error", "message": "Choose a supported coaching record type."}), 400
    visibility = data.get("visibility", "student")
    if actor["role"] == "student":
        visibility = "student"
    try:
        if COACHING_STORE == "supabase":
            title, detail, due_date, visibility = collaboration.validate_record(
                kind=kind, title=data.get("title", ""), detail=data.get("detail", ""),
                due_date=data.get("due_date"), visibility=visibility)
            created = _coaching_rpc("coaching_create", {"p_student_id": student_id, "p_kind": kind,
                "p_title": title, "p_detail": detail, "p_due_date": due_date, "p_visibility": visibility})
        else:
            created = collaboration.create_record(
                HISTORY_DATABASE_PATH, student_id=student_id, author_id=actor["id"], kind=kind,
                title=data.get("title", ""), detail=data.get("detail", ""),
                due_date=data.get("due_date"), visibility=visibility)
            collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="create_coaching_record", subject_id=student_id)
        return jsonify({"status": "success", "data": created}), 201
    except supabase_coaching.CoachingForbidden:
        return jsonify({"status": "error", "message": "You do not have access to this coaching record."}), 403
    except supabase_coaching.CoachingUnavailable:
        return jsonify({"status": "error", "message": "Coaching service is unavailable. Please retry."}), 503
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400
    except Exception:
        app.logger.error("Coaching record creation failed")
        return jsonify({"status": "error", "message": "Unable to save this coaching record."}), 500


@app.route("/api/students/<int:student_id>/coaching/<int:record_id>", methods=["PATCH"])
@app.route("/api/v1/students/<int:student_id>/coaching/<int:record_id>", methods=["PATCH"])
@require_auth()
def update_student_coaching(student_id: int, record_id: int):
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({"status": "error", "message": message}), 403 if message.startswith("You") else 404
    data = request.get_json(silent=True) or {}
    try:
        records = _coaching_list(student_id, include_private=g.current_user["role"] in auth.STAFF_ROLES)
        record = next((item for item in records if item["id"] == record_id), None)
        if record is None or record["kind"] != "goal":
            return jsonify({"status": "error", "message": "Action plan item not found."}), 404
        if g.current_user["role"] == "student" and record["visibility"] != "student":
            return jsonify({"status": "error", "message": "You do not have permission to update this item."}), 403
        if COACHING_STORE == "supabase":
            evidence = collaboration.validate_record_update(status=data.get("status"), evidence_url=data.get("evidence_url"))
            updated = _coaching_rpc("coaching_update", {"p_student_id": student_id, "p_record_id": record_id,
                "p_status": data.get("status"), "p_evidence_url": evidence})
        else:
            updated = collaboration.update_record(HISTORY_DATABASE_PATH, record_id,
                status=data.get("status"), evidence_url=data.get("evidence_url"), actor_id=g.current_user["id"])
            collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"], action="update_coaching_record", subject_id=student_id)
        return jsonify({"status": "success", "data": updated}), 200
    except supabase_coaching.CoachingForbidden:
        return jsonify({"status": "error", "message": "You do not have access to this coaching record."}), 403
    except supabase_coaching.CoachingUnavailable:
        return jsonify({"status": "error", "message": "Coaching service is unavailable. Please retry."}), 503
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/students/<int:student_id>/coaching/<int:record_id>", methods=["DELETE"])
@app.route("/api/v1/students/<int:student_id>/coaching/<int:record_id>", methods=["DELETE"])
@require_auth()
def delete_student_coaching(student_id, record_id):
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    actor = g.current_user
    try:
        records = _coaching_list(student_id, include_private=actor['role'] in auth.STAFF_ROLES)
        record = next((item for item in records if item['id'] == record_id), None)
        if not record:
            return jsonify({'status': 'error', 'message': 'Coaching record not found.'}), 404
        if record['author_id'] != actor['id'] or (actor['role'] == 'student' and (record['kind'] != 'goal' or record['visibility'] != 'student')):
            return jsonify({'status': 'error', 'message': 'Only the author can remove this record.'}), 403
        if COACHING_STORE == 'supabase':
            _coaching_rpc('coaching_delete', {'p_student_id': student_id, 'p_record_id': record_id})
        else:
            db = collaboration._connect(HISTORY_DATABASE_PATH)
            try:
                cursor = db.execute('DELETE FROM coaching_records WHERE id=? AND student_id=? AND author_id=?', (record_id, student_id, actor['id']))
                if not cursor.rowcount:
                    return jsonify({'status': 'error', 'message': 'Coaching record not found.'}), 404
                db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                           (actor['id'], 'delete_coaching_record', student_id, collaboration._now()))
                db.commit()
            finally:
                db.close()
        return jsonify({'status': 'success', 'message': 'Coaching record removed.'}), 200
    except supabase_coaching.CoachingForbidden:
        return jsonify({'status': 'error', 'message': 'You do not have permission to remove this item.'}), 403
    except supabase_coaching.CoachingUnavailable:
        return jsonify({'status': 'error', 'message': 'Coaching deletion is unavailable. Please contact an administrator.'}), 503


@app.route("/api/students/<int:student_id>/cv", methods=["GET", "POST"])
@app.route("/api/v1/students/<int:student_id>/cv", methods=["GET", "POST"])
@require_auth("student", "mentor")
def student_cv(student_id):
    """Students submit CV versions; authorized mentors can review metadata."""
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    actor = g.current_user
    if request.method == 'POST':
        if actor['role'] != 'student' or actor['id'] != student_id:
            return jsonify({'status': 'error', 'message': 'Only the student can upload their CV.'}), 403
        request.max_content_length = RESOURCE_MAX_BYTES + 65536
        upload = request.files.get('file')
        filename = secure_filename(upload.filename or '') if upload else ''
        extension = os.path.splitext(filename)[1].lower()
        if not upload or not filename or len(filename) > 200 or extension not in {'.pdf', '.docx'}:
            return jsonify({'status': 'error', 'message': 'Choose a PDF or DOCX CV.'}), 400
        content = upload.stream.read(RESOURCE_MAX_BYTES + 1)
        if not content or len(content) > RESOURCE_MAX_BYTES:
            return jsonify({'status': 'error', 'message': 'Choose a non-empty CV of at most 5 MB.'}), 400
        if (extension == '.pdf' and not content.startswith(b'%PDF-')) or (extension == '.docx' and not content.startswith(b'PK\x03\x04')):
            return jsonify({'status': 'error', 'message': 'The file contents do not match the selected type.'}), 400
        db = collaboration._connect(HISTORY_DATABASE_PATH)
        try:
            db.execute('BEGIN IMMEDIATE')
            current = db.execute('SELECT filename,content,status FROM cv_submissions WHERE student_id=? ORDER BY id DESC LIMIT 1', (student_id,)).fetchone()
            if current and current['status'] == 'pending' and current['filename'] == filename and current['content'] == content:
                return jsonify({'status': 'error', 'message': 'This CV is already awaiting mentor review.'}), 409
            now = collaboration._now()
            result = db.execute('INSERT INTO cv_submissions(student_id,filename,content,submitted_at) VALUES (?,?,?,?)', (student_id, filename, content, now))
            db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)', (actor['id'], 'submit_cv', student_id, now))
            db.commit()
            return jsonify({'status': 'success', 'data': {'id': result.lastrowid, 'status': 'pending'}}), 201
        finally:
            db.close()
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        rows = db.execute('''SELECT id,filename,length(content) AS size,status,feedback,submitted_at,reviewed_at
            FROM cv_submissions WHERE student_id=? ORDER BY id DESC LIMIT 20''', (student_id,)).fetchall()
        if actor['role'] == 'mentor':
            db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)', (actor['id'], 'view_cv', student_id, collaboration._now()))
            db.commit()
        return jsonify({'status': 'success', 'data': [dict(row) for row in rows]}), 200
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/cv/<int:cv_id>/download", methods=["GET"])
@app.route("/api/v1/students/<int:student_id>/cv/<int:cv_id>/download", methods=["GET"])
@require_auth("student", "mentor", csrf=False)
def download_student_cv(student_id, cv_id):
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        row = db.execute('SELECT filename,content FROM cv_submissions WHERE id=? AND student_id=?', (cv_id, student_id)).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'CV not found.'}), 404
        if g.current_user['role'] == 'mentor':
            db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)', (g.current_user['id'], 'download_cv', student_id, collaboration._now()))
            db.commit()
        response = send_file(io.BytesIO(row['content']), mimetype='application/octet-stream', as_attachment=True, download_name=row['filename'])
        response.headers['Cache-Control'] = 'private, no-store'
        return response
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/cv/<int:cv_id>/review", methods=["PATCH"])
@app.route("/api/v1/students/<int:student_id>/cv/<int:cv_id>/review", methods=["PATCH"])
@require_auth("mentor")
def review_student_cv(student_id, cv_id):
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({'status': 'error', 'message': 'Provide a valid review decision.'}), 400
    decision, feedback = data.get('status'), data.get('feedback', '')
    if decision not in ('approved', 'changes_requested') or not isinstance(feedback, str) or len(feedback.strip()) > 1000:
        return jsonify({'status': 'error', 'message': 'Choose a review decision and provide feedback of at most 1000 characters.'}), 400
    feedback = feedback.strip()
    if decision == 'changes_requested' and not feedback:
        return jsonify({'status': 'error', 'message': 'Explain the changes the student should make.'}), 400
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        db.execute('BEGIN IMMEDIATE')
        latest = db.execute('SELECT id,status FROM cv_submissions WHERE student_id=? ORDER BY id DESC LIMIT 1', (student_id,)).fetchone()
        if not latest or latest['id'] != cv_id or latest['status'] != 'pending':
            return jsonify({'status': 'error', 'message': 'This CV is no longer the latest pending submission. Refresh and review the current version.'}), 409
        now = collaboration._now()
        db.execute('UPDATE cv_submissions SET status=?,feedback=?,reviewer_id=?,reviewed_at=? WHERE id=? AND student_id=?', (decision, feedback, g.current_user['id'], now, cv_id, student_id))
        db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)', (g.current_user['id'], 'review_cv', student_id, now))
        db.commit()
        return jsonify({'status': 'success', 'data': {'id': cv_id, 'status': decision, 'feedback': feedback, 'reviewed_at': now}}), 200
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/evidence", methods=["GET", "POST"])
@app.route("/api/v1/students/<int:student_id>/evidence", methods=["GET", "POST"])
@require_auth()
def student_evidence(student_id: int):
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({"status": "error", "message": message}), 403 if message.startswith("You") else 404
    actor = g.current_user
    if request.method == "GET":
        if actor["role"] in auth.STAFF_ROLES:
            collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="view_student_evidence", subject_id=student_id)
        return jsonify({"status": "success", "data": collaboration.list_evidence(HISTORY_DATABASE_PATH, student_id)}), 200
    if actor["role"] != "student":
        return jsonify({"status": "error", "message": "Students submit profile evidence; administrators verify it."}), 403
    data = request.get_json(silent=True) or {}
    try:
        item = collaboration.create_evidence(HISTORY_DATABASE_PATH, student_id=student_id,
            evidence_type=data.get("evidence_type", ""), title=data.get("title", ""),
            detail=data.get("detail", ""), evidence_url=data.get("evidence_url", ""))
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="submit_profile_evidence", subject_id=student_id)
        return jsonify({"status": "success", "data": item}), 201
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/students/<int:student_id>/evidence/<int:evidence_id>", methods=["DELETE"])
@app.route("/api/v1/students/<int:student_id>/evidence/<int:evidence_id>", methods=["DELETE"])
@require_auth("student")
def delete_student_evidence(student_id: int, evidence_id: int):
    if g.current_user['id'] != student_id:
        return jsonify({'status': 'error', 'message': 'You can only remove your own evidence.'}), 403
    allowed, message = _can_access_student(student_id, write=True)
    if not allowed:
        return jsonify({'status': 'error', 'message': message}), 403
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        cursor = db.execute('DELETE FROM profile_evidence WHERE id=? AND student_id=?', (evidence_id, student_id))
        if not cursor.rowcount:
            return jsonify({'status': 'error', 'message': 'Evidence not found.'}), 404
        db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                   (g.current_user['id'], 'delete_profile_evidence', student_id, collaboration._now()))
        db.commit()
        return jsonify({'status': 'success', 'message': 'Evidence removed.'}), 200
    finally:
        db.close()


@app.route("/api/students/<int:student_id>/profile-corrections", methods=["GET", "POST"])
@app.route("/api/v1/students/<int:student_id>/profile-corrections", methods=["GET", "POST"])
@require_auth()
def student_profile_corrections(student_id: int):
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({"status": "error", "message": message}), 403 if message.startswith("You") else 404
    if request.method == "GET":
        if g.current_user["role"] not in {"student", "admin"}:
            return jsonify({"status": "error", "message": "Correction requests are visible to the student and administrators only."}), 403
        return jsonify({"status": "success", "data": collaboration.list_profile_corrections(
            HISTORY_DATABASE_PATH, student_id=student_id)}), 200
    if g.current_user["role"] != "student":
        return jsonify({"status": "error", "message": "Only students can submit profile correction requests."}), 403
    data = request.get_json(silent=True) or {}
    try:
        item = collaboration.create_profile_correction(HISTORY_DATABASE_PATH, student_id=student_id,
            field_name=data.get("field_name", ""), current_value=data.get("current_value", ""),
            requested_value=data.get("requested_value", ""), reason=data.get("reason", ""))
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"],
            action="submit_profile_correction", subject_id=student_id)
        return jsonify({"status": "success", "data": item}), 201
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/students/<int:student_id>/profile-corrections/<int:correction_id>", methods=["DELETE"])
@app.route("/api/v1/students/<int:student_id>/profile-corrections/<int:correction_id>", methods=["DELETE"])
@require_auth("student")
def withdraw_profile_correction(student_id, correction_id):
    if g.current_user['id'] != student_id:
        return jsonify({'status': 'error', 'message': 'You can only withdraw your own requests.'}), 403
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        row = db.execute('SELECT status FROM profile_corrections WHERE id=? AND student_id=?', (correction_id, student_id)).fetchone()
        if not row:
            return jsonify({'status': 'error', 'message': 'Correction request not found.'}), 404
        if row['status'] != 'open':
            return jsonify({'status': 'error', 'message': 'Reviewed requests cannot be withdrawn.'}), 409
        cursor = db.execute("DELETE FROM profile_corrections WHERE id=? AND student_id=? AND status='open'", (correction_id, student_id))
        if not cursor.rowcount:
            return jsonify({'status': 'error', 'message': 'This request has already been reviewed.'}), 409
        db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                   (g.current_user['id'], 'withdraw_profile_correction', student_id, collaboration._now()))
        db.commit()
        return jsonify({'status': 'success', 'message': 'Correction request withdrawn.'}), 200
    finally:
        db.close()


@app.route("/api/profile-corrections", methods=["GET"])
@app.route("/api/v1/profile-corrections", methods=["GET"])
@require_auth("admin")
def list_all_profile_corrections():
    collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"], action="view_profile_corrections")
    return jsonify({"status": "success", "data": collaboration.list_profile_corrections(HISTORY_DATABASE_PATH)}), 200


@app.route("/api/profile-corrections/<int:correction_id>", methods=["PATCH"])
@app.route("/api/v1/profile-corrections/<int:correction_id>", methods=["PATCH"])
@require_auth("admin")
def review_profile_correction(correction_id: int):
    data = request.get_json(silent=True) or {}
    try:
        updated = collaboration.review_profile_correction(HISTORY_DATABASE_PATH, correction_id,
            status=data.get("status", ""), reviewer_id=g.current_user["id"], resolution=data.get("resolution", ""))
        if updated is None:
            return jsonify({"status": "error", "message": "Correction request not found."}), 404
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"],
            action="review_profile_correction", subject_id=updated["student_id"])
        return jsonify({"status": "success", "data": updated}), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/students/<int:student_id>/evidence/<int:evidence_id>", methods=["PATCH"])
@app.route("/api/v1/students/<int:student_id>/evidence/<int:evidence_id>", methods=["PATCH"])
@require_auth("admin")
def verify_student_evidence(student_id: int, evidence_id: int):
    target = _target_student(student_id)
    if target is None or not target["is_active"] or target["role"] != "student":
        return jsonify({"status": "error", "message": "Student record not found."}), 404
    if not any(item["id"] == evidence_id for item in collaboration.list_evidence(HISTORY_DATABASE_PATH, student_id)):
        return jsonify({"status": "error", "message": "Evidence record not found."}), 404
    data = request.get_json(silent=True) or {}
    try:
        updated = collaboration.verify_evidence(HISTORY_DATABASE_PATH, evidence_id,
            status=data.get("status", ""), verifier_id=g.current_user["id"])
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user["id"], action="verify_profile_evidence", subject_id=student_id)
        return jsonify({"status": "success", "data": updated}), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/placement-pipeline", methods=["GET", "POST"])
@app.route("/api/v1/placement-pipeline", methods=["GET", "POST"])
@require_auth(*auth.STAFF_ROLES)
def placement_pipeline():
    actor = g.current_user
    if request.method == "GET":
        entries = collaboration.list_placements(HISTORY_DATABASE_PATH)
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="view_placement_pipeline")
        allowed_entries = []
        for item in entries:
            target = _target_student(item["student_id"])
            if target and target["is_active"] and target["role"] == "student" and (actor["role"] != "mentor" or target["cohort"] == actor.get("cohort")):
                collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="view_placement_record", subject_id=item["student_id"])
                item["display_name"] = target["display_name"]
                item["username"] = target["username"]
                item["cohort"] = target["cohort"]
                allowed_entries.append(item)
        return jsonify({"status": "success", "data": allowed_entries}), 200
    if actor["role"] not in {"admin", "placement_officer"}:
        return jsonify({"status": "error", "message": "Only placement staff can change placement stages."}), 403
    data = request.get_json(silent=True) or {}
    try:
        student_id = int(data.get("student_id"))
    except (TypeError, ValueError):
        return jsonify({"status": "error", "message": "A valid student ID is required."}), 400
    allowed, message = _can_access_student(student_id)
    if not allowed:
        return jsonify({"status": "error", "message": message}), 404
    try:
        saved = collaboration.save_placement(HISTORY_DATABASE_PATH, student_id=student_id,
            stage=data.get("stage", ""), company=data.get("company", ""),
            target_role=data.get("target_role", ""), updated_by=actor["id"])
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="update_placement_stage", subject_id=student_id)
        return jsonify({"status": "success", "data": saved}), 200
    except ValueError as exc:
        return jsonify({"status": "error", "message": str(exc)}), 400


@app.route("/api/placement-pipeline/<int:student_id>/history", methods=["GET"])
@app.route("/api/v1/placement-pipeline/<int:student_id>/history", methods=["GET"])
@require_auth("admin", "placement_officer")
def placement_stage_history(student_id):
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        rows = db.execute("SELECT id, student_id, stage, company, target_role, updated_by, updated_at FROM placement_history WHERE student_id=? ORDER BY updated_at DESC, id DESC", (student_id,)).fetchall()
        collaboration.audit(HISTORY_DATABASE_PATH, actor_id=g.current_user['id'], action='view_placement_history', subject_id=student_id)
        return jsonify({'status': 'success', 'data': [dict(row) for row in rows]}), 200
    finally:
        db.close()


@app.route("/api/placement-pipeline/<int:student_id>", methods=["DELETE"])
@app.route("/api/v1/placement-pipeline/<int:student_id>", methods=["DELETE"])
@require_auth("admin", "placement_officer")
def delete_placement_record(student_id):
    db = collaboration._connect(HISTORY_DATABASE_PATH)
    try:
        cursor = db.execute('DELETE FROM placement_events WHERE student_id=?', (student_id,))
        if not cursor.rowcount:
            return jsonify({'status': 'error', 'message': 'Placement record not found.'}), 404
        db.execute('INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES (?,?,?,?)',
                   (g.current_user['id'], 'delete_placement_record', student_id, collaboration._now()))
        db.commit()
        return jsonify({'status': 'success', 'message': 'Placement record removed.'}), 200
    finally:
        db.close()


@app.route("/api/placement-pipeline/summary", methods=["GET"])
@app.route("/api/v1/placement-pipeline/summary", methods=["GET"])
@require_auth(*auth.STAFF_ROLES, csrf=False)
def placement_pipeline_summary():
    actor = g.current_user
    entries = collaboration.list_placements(HISTORY_DATABASE_PATH)
    if actor["role"] == "mentor":
        entries = [item for item in entries if (target := _target_student(item["student_id"]))
                   and target["is_active"] and target["cohort"] == actor.get("cohort")]
    collaboration.audit(HISTORY_DATABASE_PATH, actor_id=actor["id"], action="view_placement_summary")
    if entries and len(entries) < COHORT_MIN_GROUP_SIZE:
        return jsonify({"status":"success","data":{"suppressed":True,"minimum_group_size":COHORT_MIN_GROUP_SIZE,"total":None,"stages":{}}}),200
    counts = {stage:0 for stage in collaboration.STAGES}
    for item in entries:
        counts[item["stage"]] = counts.get(item["stage"],0)+1
    return jsonify({"status":"success","data":{"suppressed":False,"minimum_group_size":COHORT_MIN_GROUP_SIZE,"total":len(entries),"stages":counts}}),200


@app.route("/api/staff/audit", methods=["GET"])
@app.route("/api/v1/staff/audit", methods=["GET"])
@require_auth("admin", csrf=False)
def staff_audit_log():
    return jsonify({"status": "success", "data": collaboration.list_audit(HISTORY_DATABASE_PATH)}), 200


@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({"status": "error", "message": "Method not allowed"}), 405


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500


@app.errorhandler(supabase_coaching.CoachingUnavailable)
def assignment_service_unavailable(error):
    return jsonify({'status': 'error', 'message': 'Mentor assignments are unavailable. Please retry.'}), 503


@app.errorhandler(413)
def request_too_large(error):
    return jsonify({"status": "error", "message": "Request payload is too large"}), 413


@app.route("/api/v1/readiness", methods=["GET"])
def readiness_probe():
    """Return whether the process can serve predictions with a loaded model."""
    try:
        payload = get_model()
        return (
            jsonify(
                {
                    "status": "ready",
                    "service": "LPU Placement Intelligence API",
                    "model_version": payload.get("model_version", "unknown"),
                }
            ),
            200,
        )
    except Exception:
        return (
            jsonify(
                {
                    "status": "not_ready",
                    "service": "LPU Placement Intelligence API",
                }
            ),
            503,
        )


if __name__ == "__main__":
    print(
        f"Starting LPU Placement Intelligence API on "
        f"{settings.host}:{settings.port} ({settings.environment})..."
    )
    # Pre-load or train model
    get_model()
    app.run(host=settings.host, port=settings.port, debug=settings.debug)
