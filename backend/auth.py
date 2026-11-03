"""Local credential authentication, sessions, and role checks.

This module is intentionally storage-focused: Flask request handling lives in
``app.py``. Accounts are provisioned by the placement office with
``manage_users.py``; there is no self-registration.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from werkzeug.security import check_password_hash, generate_password_hash

ROLES = ("student", "mentor", "placement_officer", "admin")
STAFF_ROLES = ("mentor", "placement_officer", "admin")
ROLE_LABELS = {
    "student": "Student",
    "mentor": "Mentor",
    "placement_officer": "Placement officer",
    "admin": "Administrator",
}

USERNAME_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{2,39}$")
COHORT_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{1,39}$")
MIN_PASSWORD_LENGTH = 12
MAX_PASSWORD_LENGTH = 1024

DEFAULT_AUTH_PATH = Path(__file__).resolve().parent / "data" / "auth.sqlite3"

_DUMMY_HASH: str | None = None
_DUMMY_LOCK = threading.Lock()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _isoformat(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _parse_timestamp(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _connection(database_path: str | os.PathLike[str]) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA journal_mode = WAL")
    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('student', 'mentor', 'placement_officer', 'admin')),
            cohort TEXT,
            is_active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL
        )
        """)
    connection.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            csrf_token TEXT NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL
        )
        """)
    connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id)")
    connection.execute("CREATE INDEX IF NOT EXISTS idx_sessions_expiry ON sessions(expires_at)")
    connection.execute("""CREATE TABLE IF NOT EXISTS mentor_assignments (
        student_id INTEGER PRIMARY KEY REFERENCES users(id),
        mentor_id INTEGER NOT NULL REFERENCES users(id),
        assigned_by INTEGER NOT NULL REFERENCES users(id),
        updated_at TEXT NOT NULL
    )""")
    connection.execute("""CREATE TABLE IF NOT EXISTS mentor_assignment_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_id INTEGER NOT NULL REFERENCES users(id),
        mentor_id INTEGER REFERENCES users(id),
        actor_id INTEGER NOT NULL REFERENCES users(id),
        created_at TEXT NOT NULL
    )""")
    connection.commit()
    return connection


def _public_user(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "role": row["role"],
        "cohort": row["cohort"],
    }


def normalize_username(username: Any) -> str:
    return str(username or "").strip().lower()


def normalize_cohort(cohort: Any) -> str | None:
    if cohort is None:
        return None
    value = str(cohort).strip()
    return value or None


def validate_password(password: Any) -> str:
    value = str(password or "")
    if len(value) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    if len(value) > MAX_PASSWORD_LENGTH:
        raise ValueError("Password is too long.")
    return value


def create_user(
    database_path: str | os.PathLike[str],
    *,
    username: str,
    password: str,
    display_name: str,
    role: str,
    cohort: str | None = None,
) -> dict[str, Any]:
    username = normalize_username(username)
    if not USERNAME_PATTERN.match(username):
        raise ValueError(
            "Username must be 3-40 characters: lowercase letters, digits, dot, dash, underscore."
        )
    if role not in ROLES:
        raise ValueError(f"Role must be one of: {', '.join(ROLES)}.")
    display_name = str(display_name or "").strip()
    if not 1 <= len(display_name) <= 80:
        raise ValueError("Display name must be between 1 and 80 characters.")
    cohort = normalize_cohort(cohort)
    if cohort is not None and not COHORT_PATTERN.match(cohort):
        raise ValueError(
            "Cohort must be 2-40 letters, digits, spaces, dots, dashes or underscores."
        )
    if role == "mentor" and not cohort:
        raise ValueError("A mentor account requires an assigned cohort.")
    validate_password(password)

    connection = _connection(database_path)
    try:
        try:
            cursor = connection.execute(
                """
                INSERT INTO users (username, display_name, password_hash, role, cohort, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    username,
                    display_name,
                    generate_password_hash(password),
                    role,
                    cohort,
                    _isoformat(_utcnow()),
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise ValueError("That username is already in use.") from exc
        connection.commit()
        row = connection.execute("SELECT * FROM users WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _public_user(row)
    finally:
        connection.close()


def set_password(
    database_path: str | os.PathLike[str],
    username: str,
    password: str,
) -> bool:
    validate_password(password)
    connection = _connection(database_path)
    try:
        cursor = connection.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (generate_password_hash(password), normalize_username(username)),
        )
        connection.commit()
        if cursor.rowcount == 0:
            return False
        connection.execute(
            """
            DELETE FROM sessions
            WHERE user_id IN (SELECT id FROM users WHERE username = ?)
            """,
            (normalize_username(username),),
        )
        connection.commit()
        return True
    finally:
        connection.close()


def set_active(database_path: str | os.PathLike[str], username: str, active: bool) -> bool:
    connection = _connection(database_path)
    try:
        cursor = connection.execute(
            "UPDATE users SET is_active = ? WHERE username = ?",
            (1 if active else 0, normalize_username(username)),
        )
        if not active:
            connection.execute(
                """
                DELETE FROM sessions
                WHERE user_id IN (SELECT id FROM users WHERE username = ?)
                """,
                (normalize_username(username),),
            )
        connection.commit()
        return cursor.rowcount > 0
    finally:
        connection.close()


def list_users(database_path: str | os.PathLike[str]) -> list[dict[str, Any]]:
    connection = _connection(database_path)
    try:
        rows = connection.execute(
            "SELECT id, username, display_name, role, cohort, is_active, created_at "
            "FROM users ORDER BY role, username"
        ).fetchall()
        return [
            {
                **_public_user(row),
                "is_active": bool(row["is_active"]),
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    finally:
        connection.close()


def _dummy_password_check(password: str) -> None:
    """Burn comparable CPU when the username does not exist."""
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        with _DUMMY_LOCK:
            if _DUMMY_HASH is None:
                _DUMMY_HASH = generate_password_hash(secrets.token_urlsafe(32))
    check_password_hash(_DUMMY_HASH, password)


def authenticate(
    database_path: str | os.PathLike[str],
    username: str,
    password: str,
) -> dict[str, Any] | None:
    username = normalize_username(username)
    connection = _connection(database_path)
    try:
        row = connection.execute(
            "SELECT * FROM users WHERE username = ? AND is_active = 1",
            (username,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        _dummy_password_check(password)
        return None
    if not check_password_hash(row["password_hash"], password):
        return None
    return _public_user(row)


def create_session(
    database_path: str | os.PathLike[str],
    user_id: int,
    ttl_seconds: int,
) -> dict[str, Any]:
    token = secrets.token_urlsafe(32)
    csrf_token = secrets.token_urlsafe(32)
    now = _utcnow()
    expires_at = now + timedelta(seconds=max(60, int(ttl_seconds)))

    connection = _connection(database_path)
    try:
        connection.execute("DELETE FROM sessions WHERE expires_at <= ?", (_isoformat(now),))
        connection.execute(
            """
            INSERT INTO sessions (token_hash, user_id, csrf_token, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token_digest(token), user_id, csrf_token, _isoformat(now), _isoformat(expires_at)),
        )
        connection.commit()
    finally:
        connection.close()

    return {
        "token": token,
        "csrf_token": csrf_token,
        "expires_at": _isoformat(expires_at),
        "expires_in": max(60, int(ttl_seconds)),
    }


def get_session(
    database_path: str | os.PathLike[str],
    token: str | None,
) -> dict[str, Any] | None:
    if not token:
        return None
    connection = _connection(database_path)
    try:
        row = connection.execute(
            """
            SELECT s.token_hash, s.csrf_token, s.expires_at,
                   u.id AS user_id, u.username, u.display_name, u.role, u.cohort, u.is_active
            FROM sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.token_hash = ?
            """,
            (token_digest(token),),
        ).fetchone()

        if row is None:
            return None
        if not row["is_active"] or _parse_timestamp(row["expires_at"]) <= _utcnow():
            connection.execute("DELETE FROM sessions WHERE token_hash = ?", (row["token_hash"],))
            connection.commit()
            return None

        return {
            "token_hash": row["token_hash"],
            "csrf_token": row["csrf_token"],
            "expires_at": row["expires_at"],
            "user": {
                "id": row["user_id"],
                "username": row["username"],
                "display_name": row["display_name"],
                "role": row["role"],
                "cohort": row["cohort"],
            },
        }
    finally:
        connection.close()


def delete_session(database_path: str | os.PathLike[str], token: str | None) -> None:
    if not token:
        return
    connection = _connection(database_path)
    try:
        connection.execute("DELETE FROM sessions WHERE token_hash = ?", (token_digest(token),))
        connection.commit()
    finally:
        connection.close()


def purge_expired_sessions(database_path: str | os.PathLike[str]) -> int:
    connection = _connection(database_path)
    try:
        cursor = connection.execute(
            "DELETE FROM sessions WHERE expires_at <= ?", (_isoformat(_utcnow()),)
        )
        connection.commit()
        return cursor.rowcount
    finally:
        connection.close()


class LoginRateLimiter:
    """Small in-process throttle for repeated credential failures.

    This is a first line of defence for a single process. Multi-worker
    deployments should also rate limit at the ingress.
    """

    def __init__(self, max_attempts: int = 5, window_seconds: int = 300) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _key(remote_address: str, username: str) -> str:
        return f"{remote_address}|{username}"

    def retry_after(self, remote_address: str, username: str) -> int:
        now = self._now()
        key = self._key(remote_address, username)
        with self._lock:
            attempts = [
                stamp for stamp in self._failures.get(key, []) if now - stamp < self.window_seconds
            ]
            self._failures[key] = attempts
            if len(attempts) >= self.max_attempts:
                return max(1, int(self.window_seconds - (now - attempts[0])))
            return 0

    def record_failure(self, remote_address: str, username: str) -> None:
        key = self._key(remote_address, username)
        with self._lock:
            self._failures.setdefault(key, []).append(self._now())

    def reset(self, remote_address: str, username: str) -> None:
        with self._lock:
            self._failures.pop(self._key(remote_address, username), None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()

    @staticmethod
    def _now() -> float:
        return datetime.now(timezone.utc).timestamp()
