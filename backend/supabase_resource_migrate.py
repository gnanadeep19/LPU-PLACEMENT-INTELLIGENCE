"""Rehearse or safely copy study resources into a Postgres resource table.

This tool does not migrate other dashboard data and is not a cutover tool.
Stop resource writes before running it and keep verified SQLite backups. Dry
run is the default; database credentials are read only from the environment.
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3

from config import load_settings
from supabase_migration_inventory import _open_read_only, _table_names
from supabase_migrate import _insert_resources, _plan_resources, load_mapping, verify_target_profiles


def make_resource_plan(auth_path: str, history_path: str, mapping: dict[int, str]) -> dict:
    auth_db = _open_read_only(auth_path)
    try:
        db = _open_read_only(history_path)
    except Exception:
        auth_db.close()
        raise
    auth_db.row_factory = sqlite3.Row
    db.row_factory = sqlite3.Row
    try:
        users = {row['id']: dict(row) for row in auth_db.execute(
            'SELECT id,username,role,cohort,is_active FROM users')}
        if any(legacy_id not in users for legacy_id in mapping):
            raise ValueError('A mapped account is missing from the local accounts database.')
        if not {'study_resources', 'resource_notification_outbox'}.issubset(_table_names(db)):
            raise ValueError('Resource or notification inventory is missing.')
        resources, counts, ids = _plan_resources(db, mapping)
        if counts['unmapped']:
            raise ValueError('Some resource owners or authors are unmapped; no records were copied.')
        pending = db.execute("SELECT count(*) FROM resource_notification_outbox WHERE status='pending'").fetchone()[0]
        return {'users': users, 'mapping': dict(mapping), 'resources': resources,
                'resource_ids': ids, 'history_path': history_path,
                'counts': counts, 'pending_notifications': pending}
    finally:
        auth_db.close()
        db.close()


def apply_resource_plan(connection, plan: dict, mapping: dict[int, str], *, allow_existing: bool = False) -> None:
    """Copy into a locked target without overwriting any existing resources."""
    if plan.get('mapping') != mapping:
        raise ValueError('Identity mapping changed after planning.')
    if plan.get('pending_notifications') != 0:
        raise ValueError('Pending resource notifications must be resolved before migration.')
    db = _open_read_only(plan['history_path'])
    try:
        pending = db.execute("SELECT count(*) FROM resource_notification_outbox WHERE status='pending'").fetchone()[0]
        if pending:
            raise ValueError('Pending resource notifications changed after planning.')
    finally:
        db.close()
    with connection.cursor() as cursor:
        cursor.execute("SET LOCAL TIME ZONE 'UTC'")
        cursor.execute('LOCK TABLE public.app_users IN SHARE MODE')
        cursor.execute('SELECT id, legacy_id, username, role, cohort, is_active FROM public.app_users WHERE legacy_id IS NOT NULL')
        keys = ('id', 'legacy_id', 'username', 'role', 'cohort', 'is_active')
        verify_target_profiles(plan['users'], mapping, [dict(zip(keys, row)) for row in cursor.fetchall()])
        cursor.execute('LOCK TABLE public.study_resources IN ACCESS EXCLUSIVE MODE')
        cursor.execute('SELECT count(*) FROM public.study_resources')
        existing_count = cursor.fetchone()[0]
        if existing_count and not allow_existing:
            raise ValueError('Target study resources are not empty; refusing to merge or overwrite.')
        if existing_count:
            # Do not silently replay a previous import, or duplicate the same
            # student/author/content that is already present in Postgres.
            cursor.execute("SELECT legacy_id, student_id, author_id, encode(sha256(content),'hex') FROM public.study_resources")
            existing = cursor.fetchall()
            if any(row[0] is not None for row in existing):
                raise ValueError('Target has imported resource IDs; reconcile the previous import manually.')
            existing_files = {(str(row[1]), str(row[2]), row[3]) for row in existing}
            if any((item['student_id'], item['author_id'], item['sha256']) in existing_files for item in plan['resources']):
                raise ValueError('A matching target resource exists; reconcile the duplicate manually.')
        _insert_resources(cursor, plan['history_path'], plan['resources'], plan['resource_ids'])


def main() -> int:
    settings = load_settings()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mapping', required=True, help='Reviewed CSV containing legacy_id,auth_user_id')
    parser.add_argument('--auth-db', default=settings.auth_database_path)
    parser.add_argument('--history-db', default=settings.history_database_path)
    parser.add_argument('--apply', action='store_true', help='Copy resources after validating the target')
    parser.add_argument('--allow-existing', action='store_true', help='Allow existing non-imported Postgres resources after duplicate checks')
    args = parser.parse_args()
    try:
        mapping = load_mapping(args.mapping)
        plan = make_resource_plan(args.auth_db, args.history_db, mapping)
        print(json.dumps({'resource_counts': plan['counts'], 'pending_notifications': plan['pending_notifications']}, indent=2))
        if not args.apply:
            print('Dry run only: no resources were copied or changed.')
            return 0
        if plan['pending_notifications']:
            raise ValueError('Pending resource notifications must be resolved before migration.')
        database_url = os.environ.get('SUPABASE_DATABASE_URL', '')
        if not database_url:
            raise ValueError('Set SUPABASE_DATABASE_URL locally before applying.')
        try:
            import psycopg
        except ImportError as exc:
            raise ValueError('Install the migration dependencies from backend/requirements-migration.txt.') from exc
        with psycopg.connect(database_url, sslmode='verify-full', connect_timeout=10) as connection:
            apply_resource_plan(connection, plan, mapping, allow_existing=args.allow_existing)
        print('Resource import committed. SQLite files were not changed; the application was not switched.')
        return 0
    except (OSError, sqlite3.Error, ValueError) as exc:
        parser.exit(1, f'Resource migration stopped: {exc}\n')
    except Exception:
        # Driver exceptions can contain credentials or file content.
        parser.exit(1, 'Resource migration stopped: database operation failed; the transaction was rolled back.\n')


if __name__ == '__main__':
    raise SystemExit(main())
