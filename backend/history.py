"""Privacy-conscious local persistence for anonymous readiness assessments."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any

FEATURE_NAMES = (
    "cgpa",
    "technical_score",
    "aptitude_score",
    "communication_score",
    "coding_score",
    "projects",
    "internships",
    "certifications",
    "backlogs",
)

DEFAULT_HISTORY_PATH = Path(__file__).resolve().parent / "data" / "assessment_history.sqlite3"


def _connection(database_path: str | os.PathLike[str] = DEFAULT_HISTORY_PATH) -> sqlite3.Connection:
    path = Path(database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_hash TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            readiness_score INTEGER NOT NULL,
            readiness_category TEXT NOT NULL,
            model_probability REAL NOT NULL,
            calibrated_probability REAL,
            model_version TEXT NOT NULL DEFAULT 'unknown',
            student_json TEXT NOT NULL,
            user_id INTEGER,
            cohort TEXT
        )
        """)
    # Migrate databases created before ownership and cohort scoping existed.
    columns = {
        row["name"] for row in connection.execute("PRAGMA table_info(assessments)").fetchall()
    }
    if "user_id" not in columns:
        connection.execute("ALTER TABLE assessments ADD COLUMN user_id INTEGER")
    if "cohort" not in columns:
        connection.execute("ALTER TABLE assessments ADD COLUMN cohort TEXT")
    if "model_version" not in columns:
        connection.execute("ALTER TABLE assessments ADD COLUMN model_version TEXT NOT NULL DEFAULT 'unknown'")
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessments_profile_created "
        "ON assessments(profile_hash, created_at)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessments_user_profile "
        "ON assessments(user_id, profile_hash)"
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_assessments_cohort " "ON assessments(cohort)"
    )
    connection.commit()
    return connection


def profile_hash(student: dict[str, Any]) -> str:
    canonical = {feature: student[feature] for feature in FEATURE_NAMES}
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def save_assessment(
    student: dict[str, Any],
    prediction: dict[str, Any],
    database_path: str | os.PathLike[str] = DEFAULT_HISTORY_PATH,
    *,
    user_id: int | None = None,
    cohort: str | None = None,
) -> dict[str, Any]:
    student_key = profile_hash(student)
    connection = _connection(database_path)
    try:
        cursor = connection.execute(
            """
            INSERT INTO assessments (
                profile_hash, readiness_score, readiness_category,
                model_probability, calibrated_probability, student_json,
                user_id, cohort, model_version
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                student_key,
                prediction["readiness_score"],
                prediction["readiness_category"],
                prediction["model_probability"],
                prediction.get("calibrated_probability"),
                json.dumps(student, sort_keys=True),
                user_id,
                cohort,
                str(prediction.get("model_version") or "unknown")[:80],
            ),
        )
        connection.commit()
        return {
            "id": cursor.lastrowid,
            "profile_hash": student_key,
            "created_at": connection.execute(
                "SELECT created_at FROM assessments WHERE id = ?", (cursor.lastrowid,)
            ).fetchone()["created_at"],
        }
    finally:
        connection.close()


def validate_prediction_snapshot(prediction: Any) -> tuple[bool, str]:
    if not isinstance(prediction, dict):
        return False, "Prediction must be a JSON object."
    required = ("readiness_score", "readiness_category", "model_probability")
    if any(field not in prediction for field in required):
        return False, "Prediction is missing required fields."
    if (
        not isinstance(prediction["readiness_category"], str)
        or len(prediction["readiness_category"]) > 80
    ):
        return False, "Readiness category is invalid."
    try:
        score = int(prediction["readiness_score"])
        probability = float(prediction["model_probability"])
        calibrated = prediction.get("calibrated_probability")
        if not 0 <= score <= 100 or not 0 <= probability <= 1:
            return False, "Prediction values are outside permitted ranges."
        if calibrated is not None and not 0 <= float(calibrated) <= 1:
            return False, "Calibrated probability is outside permitted range."
    except (TypeError, ValueError):
        return False, "Prediction numeric fields are invalid."
    return True, ""


def list_assessments(
    student: dict[str, Any],
    limit: int = 20,
    database_path: str | os.PathLike[str] = DEFAULT_HISTORY_PATH,
    *,
    user_id: int | None = None,
) -> list[dict[str, Any]]:
    """Return only assessments owned by ``user_id``.

    ``user_id=None`` matches legacy anonymous rows and never widens access to
    another account's history.
    """
    bounded_limit = max(1, min(limit, 100))
    connection = _connection(database_path)
    try:
        # Signed-in students need their full history to compare changed inputs.
        # Legacy anonymous rows remain restricted to the supplied profile hash.
        predicate = "user_id = ?" if user_id is not None else "profile_hash = ? AND user_id IS NULL"
        identity = user_id if user_id is not None else profile_hash(student)
        rows = connection.execute(
            """
            SELECT id, created_at, readiness_score, readiness_category,
                   model_probability, calibrated_probability, model_version, student_json
            FROM assessments
            WHERE """ + predicate + """
            ORDER BY created_at DESC, id DESC
            LIMIT ?
            """,
            (identity, bounded_limit),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "created_at": row["created_at"],
                "readiness_score": row["readiness_score"],
                "readiness_category": row["readiness_category"],
                "model_probability": row["model_probability"],
                "calibrated_probability": row["calibrated_probability"],
                "model_version": row["model_version"],
                "student_profile": json.loads(row["student_json"]),
            }
            for row in rows
        ]
    finally:
        connection.close()


def cohort_analytics(
    thresholds: dict[str, float],
    database_path: str | os.PathLike[str] = DEFAULT_HISTORY_PATH,
    *,
    cohort: str | None = None,
    minimum_group_size: int = 5,
) -> dict[str, Any]:
    """Return aggregate metrics only; individual profiles never leave storage.

    ``cohort=None`` covers every cohort and is reserved for placement officers
    and administrators. Groups smaller than ``minimum_group_size`` return a
    suppressed payload with no scores, distribution, or gaps.
    """
    connection = _connection(database_path)
    try:
        if cohort:
            rows = connection.execute(
                """
                SELECT profile_hash, readiness_score, calibrated_probability, student_json
                FROM assessments
                WHERE id IN (
                    SELECT MAX(id) FROM assessments WHERE cohort = ? GROUP BY profile_hash
                )
                """,
                (cohort,),
            ).fetchall()
        else:
            rows = connection.execute("""
                SELECT profile_hash, readiness_score, calibrated_probability, student_json
                FROM assessments
                WHERE id IN (SELECT MAX(id) FROM assessments GROUP BY profile_hash)
                """).fetchall()
    finally:
        connection.close()

    if rows and len(rows) < minimum_group_size:
        return {
            "suppressed": True,
            "unique_profiles": None,
            "latest_assessments": None,
            "minimum_group_size": minimum_group_size,
            "cohort": cohort,
            "average_readiness_score": None,
            "average_calibrated_probability": None,
            "readiness_distribution": {},
            "common_gaps": [],
        }

    if not rows:
        return {
            "suppressed": False,
            "unique_profiles": 0,
            "latest_assessments": 0,
            "minimum_group_size": minimum_group_size,
            "cohort": cohort,
            "average_readiness_score": None,
            "average_calibrated_probability": None,
            "readiness_distribution": {},
            "common_gaps": [],
        }

    distribution: dict[str, int] = {}
    gap_counts = {feature: 0 for feature in FEATURE_NAMES}
    for row in rows:
        score = row["readiness_score"]
        category = (
            "Placement Ready" if score >= 75 else "Nearly Ready" if score >= 50 else "Needs Focus"
        )
        distribution[category] = distribution.get(category, 0) + 1
        student = json.loads(row["student_json"])
        for feature, threshold in thresholds.items():
            below_target = (
                student[feature] > threshold
                if feature == "backlogs"
                else student[feature] < threshold
            )
            if below_target:
                gap_counts[feature] += 1

    common_gaps = [
        {"feature": feature, "profiles": count, "share": round(count / len(rows), 4)}
        for feature, count in sorted(gap_counts.items(), key=lambda item: item[1], reverse=True)
        if count
    ]
    probabilities = [
        row["calibrated_probability"] for row in rows if row["calibrated_probability"] is not None
    ]
    return {
        "suppressed": False,
        "unique_profiles": len(rows),
        "latest_assessments": len(rows),
        "minimum_group_size": minimum_group_size,
        "cohort": cohort,
        "average_readiness_score": round(
            sum(row["readiness_score"] for row in rows) / len(rows), 2
        ),
        "average_calibrated_probability": (
            round(sum(probabilities) / len(probabilities), 4) if probabilities else None
        ),
        "readiness_distribution": distribution,
        "common_gaps": common_gaps,
    }
