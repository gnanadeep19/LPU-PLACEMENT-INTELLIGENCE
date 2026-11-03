"""Application configuration loaded from environment variables."""

import os
from dataclasses import dataclass


def _as_bool(value: str, default: bool = False) -> bool:
    if value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_origins(value: str) -> tuple[str, ...]:
    origins = tuple(origin.strip() for origin in value.split(",") if origin.strip())
    return origins or ("http://127.0.0.1:5173", "http://localhost:5173")


@dataclass(frozen=True)
class Settings:
    environment: str
    host: str
    port: int
    debug: bool
    model_path: str
    cors_origins: tuple[str, ...]
    history_database_path: str
    auth_database_path: str
    session_ttl_seconds: int
    auth_cookie_secure: bool
    cohort_min_group_size: int
    login_max_attempts: int
    login_window_seconds: int
    max_content_length: int


def load_settings() -> Settings:
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.environ.get(
        "MODEL_PATH",
        os.path.join(backend_dir, "placement_model.joblib"),
    )
    history_database_path = os.environ.get(
        "HISTORY_DATABASE_PATH",
        os.path.join(backend_dir, "data", "assessment_history.sqlite3"),
    )
    auth_database_path = os.environ.get(
        "AUTH_DATABASE_PATH",
        os.path.join(backend_dir, "data", "auth.sqlite3"),
    )
    environment = os.environ.get("APP_ENV", "development")
    return Settings(
        environment=environment,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "5000")),
        debug=_as_bool(os.environ.get("FLASK_DEBUG", "False")),
        model_path=model_path,
        cors_origins=_as_origins(
            os.environ.get(
                "CORS_ORIGINS",
                "http://127.0.0.1:5173,http://localhost:5173",
            )
        ),
        history_database_path=history_database_path,
        auth_database_path=auth_database_path,
        session_ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", "28800")),
        auth_cookie_secure=_as_bool(
            os.environ.get("AUTH_COOKIE_SECURE", "True" if environment == "production" else "False")
        ),
        cohort_min_group_size=max(2, int(os.environ.get("COHORT_MIN_GROUP_SIZE", "5"))),
        login_max_attempts=max(1, int(os.environ.get("LOGIN_MAX_ATTEMPTS", "5"))),
        login_window_seconds=max(30, int(os.environ.get("LOGIN_WINDOW_SECONDS", "300"))),
        max_content_length=int(os.environ.get("MAX_CONTENT_LENGTH", "65536")),
    )
