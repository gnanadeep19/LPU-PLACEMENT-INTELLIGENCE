"""Plan or import existing SQLite data into an empty Supabase Postgres schema.

This tool does not create accounts or read/export passwords. Dry run is the
default. Applying requires a reviewed identity mapping and a privileged direct
database connection supplied through SUPABASE_DATABASE_URL, never a CLI flag.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from uuid import UUID

from config import load_settings
from supabase_migration_inventory import _open_read_only, _table_names, _unknown_tables

# Source and destination fields are fixed, not supplied by the mapping file.
TABLES = {
    "assessments": ("id", "user_id", "cohort", "profile_hash", "created_at", "readiness_score", "readiness_category", "model_probability", "calibrated_probability", "model_version", "student_json"),
    "coaching_records": ("id", "student_id", "author_id", "kind", "title", "detail", "due_date", "status", "visibility", "evidence_url", "created_at", "updated_at"),
    "student_settings": ("student_id", "target_role", "target_roles", "updated_at"),
    "profile_evidence": ("id", "student_id", "evidence_type", "title", "detail", "evidence_url", "source", "verification_status", "submitted_at", "verified_by", "verified_at"),
    "profile_corrections": ("id", "student_id", "field_name", "current_value", "requested_value", "reason", "status", "submitted_at", "reviewed_at", "reviewer_id", "resolution"),
    "placement_events": ("student_id", "stage", "company", "target_role", "updated_by", "updated_at"),
    "placement_history": ("id", "student_id", "stage", "company", "target_role", "updated_by", "updated_at"),
    "staff_audit": ("id", "actor_id", "action", "subject_id", "created_at"),
}
USER_COLUMNS = {"user_id", "student_id", "author_id", "verified_by", "reviewer_id", "updated_by", "actor_id", "subject_id"}
NULLABLE_USERS = {"verified_by", "reviewer_id", "subject_id"}
JSON_COLUMNS = {"student_json", "target_roles"}
RESOURCE_MAX_BYTES = 5 * 1024 * 1024
RESOURCE_SOURCE_COLUMNS = ("id", "student_id", "author_id", "title", "description", "filename", "created_at")


def _resource_rows(db: sqlite3.Connection):
    columns = {row[1] for row in db.execute('PRAGMA table_info("study_resources")')}
    if not set(RESOURCE_SOURCE_COLUMNS + ("content",)).issubset(columns):
        raise ValueError("Source table study_resources is missing required columns.")
    category = 'category' if 'category' in columns else "'General'"
    return db.execute(f'''SELECT id, student_id, author_id, title, description, filename,
        created_at, {category} AS category, length(content) AS content_size
        FROM study_resources ORDER BY id''')


def _resource_digest(db: sqlite3.Connection, resource_id: int, expected_size: int) -> str:
    digest = hashlib.sha256()
    with db.blobopen('study_resources', 'content', resource_id, readonly=True) as blob:
        if len(blob) != expected_size:
            raise ValueError("A study resource changed during migration planning.")
        while chunk := blob.read(65536):
            digest.update(chunk)
    return digest.hexdigest()


def _plan_resources(db: sqlite3.Connection, mapping: dict[int, str]) -> tuple[list[dict], dict, list[int]]:
    """Keep metadata and hashes in memory; do not retain file bytes in the plan."""
    ready, skipped, source_ids = [], 0, []
    for row in _resource_rows(db):
        source = dict(row)
        source_ids.append(source['id'])
        if source['student_id'] not in mapping or source['author_id'] not in mapping:
            skipped += 1
            continue
        size = source['content_size']
        if not isinstance(size, int) or not 1 <= size <= RESOURCE_MAX_BYTES:
            raise ValueError("A study resource is empty or exceeds the supported 5 MB limit.")
        if any(source[key] is None for key in ('title', 'description', 'filename', 'category', 'created_at')):
            raise ValueError("A study resource has incomplete required metadata.")
        ready.append({'source': source, 'sha256': _resource_digest(db, source['id'], size),
                      'student_id': mapping[source['student_id']], 'author_id': mapping[source['author_id']]})
    return ready, {'present': True, 'rows': len(ready) + skipped, 'ready': len(ready), 'unmapped': skipped}, source_ids


def _insert_resources(cursor, history_path: str, resources: list[dict], source_ids: list[int]) -> None:
    """Verify a consistent read-only snapshot and insert one bounded file at a time."""
    db = _open_read_only(history_path)
    db.row_factory = sqlite3.Row
    try:
        db.execute('BEGIN')
        current = {row['id']: dict(row) for row in _resource_rows(db)}
        if sorted(current) != source_ids:
            raise ValueError("The study resource inventory changed after the migration plan was created.")
        statement = '''INSERT INTO public.study_resources
            (legacy_id,student_id,author_id,title,description,filename,category,content,created_at)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)'''
        for item in resources:
            source = item['source']
            if current.get(source['id']) != source:
                raise ValueError("Study resource metadata changed after the migration plan was created.")
            size = source['content_size']
            with db.blobopen('study_resources', 'content', source['id'], readonly=True) as blob:
                if len(blob) != size:
                    raise ValueError("A study resource changed after the migration plan was created.")
                content = blob.read(RESOURCE_MAX_BYTES + 1)
            if len(content) != size or hashlib.sha256(content).hexdigest() != item['sha256']:
                raise ValueError("Study resource content changed after the migration plan was created.")
            cursor.executemany(statement, [(source['id'], item['student_id'], item['author_id'], source['title'],
                source['description'], source['filename'], source['category'], content, source['created_at'])])
    finally:
        db.close()


def load_mapping(path: str) -> dict[int, str]:
    """Read an administrator-reviewed legacy_id,auth_user_id mapping CSV."""
    result: dict[int, str] = {}
    seen_uuids: set[str] = set()
    with open(path, encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not {"legacy_id", "auth_user_id"}.issubset(reader.fieldnames):
            raise ValueError("Mapping CSV must contain legacy_id and auth_user_id headers.")
        for row in reader:
            try:
                legacy_id = int(row["legacy_id"])
                user_id = str(UUID(row["auth_user_id"]))
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                raise ValueError("Mapping contains an invalid legacy ID or UUID.") from exc
            if legacy_id <= 0 or legacy_id in result or user_id in seen_uuids:
                raise ValueError("Mapping IDs must be positive and unique in both directions.")
            result[legacy_id] = user_id
            seen_uuids.add(user_id)
    if not result:
        raise ValueError("Mapping CSV contains no accounts.")
    return result


def make_plan(auth_path: str, history_path: str, mapping: dict[int, str]) -> dict:
    """Build an in-memory plan; only aggregate counts should be printed."""
    auth_db = _open_read_only(auth_path)
    try:
        history_db = _open_read_only(history_path)
    except Exception:
        auth_db.close()
        raise
    auth_db.row_factory = sqlite3.Row
    history_db.row_factory = sqlite3.Row
    try:
        users = {row["id"]: dict(row) for row in auth_db.execute(
            "SELECT id, username, role, cohort, is_active FROM users")}
        if any(legacy_id not in users for legacy_id in mapping):
            raise ValueError("Mapping contains an ID not present in the local accounts database.")
        available = _table_names(history_db)
        # Anything not explicitly supported must be accounted for before an
        # import. Session tokens are intentionally excluded from migration.
        unsupported = {
            "auth": _unknown_tables(auth_db, _table_names(auth_db), {"users", "sessions"}),
            "history": _unknown_tables(history_db, available, set(TABLES) | {"study_resources"}),
        }
        planned: dict[str, list[dict]] = {}
        counts: dict[str, dict] = {}
        for table, columns in TABLES.items():
            if table not in available:
                planned[table] = []
                counts[table] = {"present": False, "rows": 0, "ready": 0, "unmapped": 0}
                continue
            available_columns = {row[1] for row in history_db.execute(f'PRAGMA table_info("{table}")')}
            if not set(columns).issubset(available_columns):
                raise ValueError(f"Source table {table} is missing required columns; update the local schema before planning.")
            ready, skipped = [], 0
            for source_row in history_db.execute(f'SELECT * FROM "{table}" ORDER BY rowid'):
                source = dict(source_row)
                target = {}
                unresolved = False
                for column in columns:
                    value = source[column]
                    target_column = "legacy_id" if column == "id" else column
                    if column in USER_COLUMNS:
                        if value is None and column in NULLABLE_USERS:
                            target[target_column] = None
                        elif value is None or value not in mapping:
                            unresolved = True
                        else:
                            target[target_column] = mapping[value]
                    elif column in JSON_COLUMNS:
                        try:
                            target[target_column] = json.loads(value)
                        except (ValueError, TypeError) as exc:
                            raise ValueError(f"Invalid JSON in source table {table}; correct it before migrating.") from exc
                        expected = dict if column == "student_json" else list
                        if not isinstance(target[target_column], expected):
                            raise ValueError(f"Unexpected JSON structure in source table {table}; correct it before migrating.")
                    else:
                        target[target_column] = value
                if unresolved:
                    skipped += 1
                else:
                    ready.append(target)
            planned[table] = ready
            counts[table] = {"present": True, "rows": len(ready) + skipped, "ready": len(ready), "unmapped": skipped}
        if 'study_resources' in available:
            resources, counts['study_resources'], resource_ids = _plan_resources(history_db, mapping)
        else:
            resources, resource_ids = [], []
            counts['study_resources'] = {"present": False, "rows": 0, "ready": 0, "unmapped": 0}
        return {"users": users, "records": planned, "counts": counts, "unsupported_tables": unsupported,
                "resources": resources, "resource_ids": resource_ids,
                "history_path": str(Path(history_path).resolve()), "mapping": dict(mapping)}
    finally:
        auth_db.close()
        history_db.close()


def verify_target_profiles(source_users: dict, mapping: dict[int, str], rows: list[dict]) -> None:
    """Fail closed if a Postgres profile does not match its local identity."""
    targets = {row["legacy_id"]: row for row in rows if row.get("legacy_id") is not None}
    for legacy_id, supabase_id in mapping.items():
        local, target = source_users[legacy_id], targets.get(legacy_id)
        if (not target or str(target["id"]) != supabase_id
                or target["username"] != local["username"] or target["role"] != local["role"]
                or target["cohort"] != local["cohort"] or bool(target["is_active"]) != bool(local["is_active"])):
            raise ValueError("A target account is missing or its approved identity, role, cohort, or status does not match.")


def apply_plan(connection, plan: dict, mapping: dict[int, str], *, allow_unmapped: bool = False) -> None:
    """Import once into empty tables; caller owns the connection transaction."""
    if plan.get('mapping') != mapping:
        raise ValueError("Identity mapping changed after the migration plan was created.")
    if any(key not in plan for key in ('resources', 'resource_ids', 'history_path')):
        raise ValueError("Study resource inventory is missing; refusing an incomplete import.")
    if "unsupported_tables" not in plan:
        raise ValueError("Unsupported source table inventory is missing; refusing an incomplete import.")
    if any(count for tables in plan["unsupported_tables"].values() for count in tables.values()):
        raise ValueError("Unsupported source tables contain records; refusing an incomplete import.")
    if any(not item["present"] for item in plan["counts"].values()):
        raise ValueError("A source table is missing; refusing an incomplete import.")
    if not allow_unmapped and (len(mapping) != len(plan["users"]) or any(item["unmapped"] for item in plan["counts"].values())):
        raise ValueError("Unmapped records exist; resolve them or explicitly opt to leave them in SQLite.")
    from psycopg.types.json import Jsonb

    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'UTC'")
        # Freeze writes and account mapping until the import commits or rolls back.
        cursor.execute("LOCK TABLE public.app_users IN SHARE MODE")
        cursor.execute("SELECT id, legacy_id, username, role, cohort, is_active FROM public.app_users WHERE legacy_id IS NOT NULL")
        keys = ("id", "legacy_id", "username", "role", "cohort", "is_active")
        profiles = [dict(zip(keys, row)) for row in cursor.fetchall()]
        verify_target_profiles(plan["users"], mapping, profiles)
        for table in (*TABLES, 'study_resources'):
            cursor.execute(f'LOCK TABLE public."{table}" IN ACCESS EXCLUSIVE MODE')
            cursor.execute(f'SELECT count(*) FROM public."{table}"')
            if cursor.fetchone()[0]:
                raise ValueError(f"Target table {table} is not empty; refusing to overwrite or merge data.")
        # Transactional DDL: a failure rolls back both the data and trigger state.
        cursor.execute("SELECT tgenabled FROM pg_catalog.pg_trigger WHERE tgrelid = 'public.coaching_records'::regclass AND tgname = 'coaching_notifications' AND NOT tgisinternal")
        trigger = cursor.fetchone()
        if trigger is None or trigger[0] != 'O':
            raise ValueError("The coaching notification trigger is missing or not in its expected state.")
        cursor.execute('ALTER TABLE public.coaching_records DISABLE TRIGGER coaching_notifications')
        for table, records in plan["records"].items():
            if not records:
                continue
            columns = list(records[0])
            placeholders = ", ".join(["%s"] * len(columns))
            names = ", ".join(f'"{column}"' for column in columns)
            statement = f'INSERT INTO public."{table}" ({names}) VALUES ({placeholders})'
            values = [tuple(Jsonb(row[column]) if column in JSON_COLUMNS else row[column] for column in columns) for row in records]
            cursor.executemany(statement, values)
        _insert_resources(cursor, plan['history_path'], plan['resources'], plan['resource_ids'])
        cursor.execute('ALTER TABLE public.coaching_records ENABLE TRIGGER coaching_notifications')


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping", required=True, help="Reviewed CSV containing legacy_id,auth_user_id")
    parser.add_argument("--auth-db", default=settings.auth_database_path)
    parser.add_argument("--history-db", default=settings.history_database_path)
    parser.add_argument("--apply", action="store_true", help="Write to the configured empty Postgres target")
    parser.add_argument("--allow-unmapped", action="store_true", help="Leave unmapped rows in SQLite during import")
    args = parser.parse_args()
    try:
        mapping = load_mapping(args.mapping)
        plan = make_plan(args.auth_db, args.history_db, mapping)
        print(json.dumps({"mapped_accounts": len(mapping), "unmapped_accounts": len(plan["users"]) - len(mapping), "tables": plan["counts"], "unsupported_tables": plan["unsupported_tables"]}, indent=2))
        if not args.apply:
            if any(count for tables in plan["unsupported_tables"].values() for count in tables.values()):
                print("Import blocked: unsupported source tables contain records and need a migration plan.")
            print("Dry run only: no data was uploaded or changed.")
            return 0
        if any(count for tables in plan["unsupported_tables"].values() for count in tables.values()):
            raise ValueError("Unsupported source tables contain records; no upload was attempted.")
        if any(not item["present"] for item in plan["counts"].values()):
            raise ValueError("A source table is missing; no upload was attempted.")
        if not args.allow_unmapped and (len(mapping) != len(plan["users"]) or any(item["unmapped"] for item in plan["counts"].values())):
            raise ValueError("Unmapped records exist; no upload was attempted.")
        database_url = os.environ.get("SUPABASE_DATABASE_URL", "")
        if not database_url:
            raise ValueError("Set SUPABASE_DATABASE_URL in your local environment before applying.")
        try:
            import psycopg
        except ImportError as exc:
            raise ValueError("Install the migration-only dependencies listed in backend/requirements-migration.txt.") from exc
        # SSL verification is mandatory, regardless of connection-string defaults.
        try:
            with psycopg.connect(database_url, sslmode="verify-full", connect_timeout=10) as connection:
                apply_plan(connection, plan, mapping, allow_unmapped=args.allow_unmapped)
        except Exception as exc:
            # Driver errors can contain a connection string or row contents.
            # Never print those details in CLI output.
            raise RuntimeError("Postgres operation failed.") from exc
        print("Import committed. Local SQLite databases were not changed.")
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f"Migration stopped: {exc}\n")
    except Exception:
        # Database errors can contain connection details or record contents.
        parser.exit(1, "Migration stopped: database operation failed; the transaction was rolled back. Check configuration without sharing credentials.\n")


if __name__ == "__main__":
    raise SystemExit(main())
