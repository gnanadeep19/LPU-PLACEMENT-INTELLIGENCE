"""Report local migration readiness without modifying or exporting student data."""

from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from config import load_settings


REFERENCES = {
    "assessments": ("user_id",),
    "coaching_records": ("student_id", "author_id"),
    "student_settings": ("student_id",),
    "profile_evidence": ("student_id", "verified_by"),
    "profile_corrections": ("student_id", "reviewer_id"),
    "placement_events": ("student_id", "updated_by"),
    "placement_history": ("student_id", "updated_by"),
    "study_resources": ("student_id", "author_id"),
    "staff_audit": ("actor_id", "subject_id"),
}

AUTH_REFERENCES = {
    "mentor_assignments": ("student_id", "mentor_id", "assigned_by"),
    "mentor_assignment_events": ("student_id", "mentor_id", "actor_id"),
}


def _table_names(db: sqlite3.Connection) -> set[str]:
    return {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")}


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _inspect_table(db: sqlite3.Connection, table: str, columns: tuple[str, ...], users: set[int]) -> dict:
    name = _quote_identifier(table)
    present_columns = {row[1] for row in db.execute(f'PRAGMA table_info({name})')}
    result = {"present": True, "rows": db.execute(f'SELECT count(*) FROM {name}').fetchone()[0], "references": {}}
    for column in columns:
        if column not in present_columns:
            result["references"][column] = {"present": False}
            continue
        quoted = _quote_identifier(column)
        counts = db.execute(f'SELECT {quoted}, count(*) FROM {name} GROUP BY {quoted}').fetchall()
        result["references"][column] = {
            "null": sum(count for value, count in counts if value is None),
            "unknown_user": sum(count for value, count in counts if value is not None and value not in users),
        }
    return result


def _unknown_tables(db: sqlite3.Connection, available: set[str], known: set[str]) -> dict[str, int]:
    return {name: db.execute(f'SELECT count(*) FROM {_quote_identifier(name)}').fetchone()[0]
            for name in sorted(available - known)}


def _open_read_only(path: str) -> sqlite3.Connection:
    absolute = Path(path).resolve(strict=True)
    return sqlite3.connect(absolute.as_uri() + "?mode=ro", uri=True)


def inspect_databases(auth_path: str, history_path: str) -> dict:
    """Return aggregate counts only; all connections are SQLite read-only."""
    with _open_read_only(auth_path) as db:
        users = {row[0] for row in db.execute("SELECT id FROM users")}
        roles = dict(db.execute("SELECT role, count(*) FROM users GROUP BY role"))
        auth_available = _table_names(db)
        auth_tables = {table: _inspect_table(db, table, columns, users) if table in auth_available else {"present": False}
                       for table, columns in AUTH_REFERENCES.items()}
        # Session tokens are deliberately neither inspected nor migrated.
        auth_unknown = _unknown_tables(db, auth_available, set(AUTH_REFERENCES) | {"users", "sessions"})
    result = {"users": len(users), "roles": roles, "auth_tables": auth_tables, "tables": {},
              "unrecognized_tables": {"auth": auth_unknown}}
    with _open_read_only(history_path) as db:
        available = _table_names(db)
        for table, columns in REFERENCES.items():
            if table not in available:
                result["tables"][table] = {"present": False}
                continue
            result["tables"][table] = _inspect_table(db, table, columns, users)
        if "resource_notification_outbox" in available:
            columns = {row[1] for row in db.execute('PRAGMA table_info("resource_notification_outbox")')}
            outbox = {"present": True, "rows": db.execute('SELECT count(*) FROM resource_notification_outbox').fetchone()[0]}
            if "status" in columns:
                outbox["status_counts"] = dict(db.execute('SELECT status, count(*) FROM resource_notification_outbox GROUP BY status'))
            resource_columns = {row[1] for row in db.execute('PRAGMA table_info("study_resources")')} if "study_resources" in available else set()
            if "resource_id" in columns and "id" in resource_columns:
                outbox["missing_resource"] = db.execute('''SELECT count(*) FROM resource_notification_outbox o
                    LEFT JOIN study_resources r ON r.id=o.resource_id WHERE r.id IS NULL''').fetchone()[0]
            result["tables"]["resource_notification_outbox"] = outbox
        else:
            result["tables"]["resource_notification_outbox"] = {"present": False}
        if "study_resources" in available:
            columns = {row[1] for row in db.execute('PRAGMA table_info("study_resources")')}
            if "content" in columns:
                result["tables"]["study_resources"]["total_bytes"] = db.execute('SELECT coalesce(sum(length(content)),0) FROM study_resources').fetchone()[0]
        result["unrecognized_tables"]["history"] = _unknown_tables(db, available, set(REFERENCES) | {"resource_notification_outbox"})
    return result


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--auth-db", default=settings.auth_database_path)
    parser.add_argument("--history-db", default=settings.history_database_path)
    args = parser.parse_args()
    try:
        report = inspect_databases(args.auth_db, args.history_db)
    except (OSError, sqlite3.Error) as exc:
        parser.exit(1, f"Unable to inspect the databases: {exc}\n")
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
