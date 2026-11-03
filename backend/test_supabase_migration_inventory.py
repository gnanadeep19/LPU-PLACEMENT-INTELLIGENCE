import sqlite3

import pytest

from supabase_migration_inventory import inspect_databases


def test_inventory_counts_unmapped_references_without_creating_missing_tables(tmp_path):
    auth_path, history_path = tmp_path / "auth.sqlite", tmp_path / "history.sqlite"
    with sqlite3.connect(auth_path) as db:
        db.execute("CREATE TABLE users (id INTEGER, role TEXT)")
        db.execute("INSERT INTO users VALUES (1, 'student')")
    with sqlite3.connect(history_path) as db:
        db.execute("CREATE TABLE assessments (user_id INTEGER)")
        db.executemany("INSERT INTO assessments VALUES (?)", [(1,), (None,), (7,)])
    result = inspect_databases(str(auth_path), str(history_path))
    assert result["users"] == 1
    assert result["tables"]["assessments"]["rows"] == 3
    assert result["tables"]["assessments"]["references"]["user_id"] == {"null": 1, "unknown_user": 1}
    assert result["tables"]["coaching_records"] == {"present": False}


def test_inventory_does_not_create_missing_databases(tmp_path):
    missing = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        inspect_databases(str(missing), str(missing))
    assert not missing.exists()


def test_inventory_covers_resources_assignments_and_outbox_without_exporting_content(tmp_path):
    auth_path, history_path = tmp_path / 'auth.sqlite', tmp_path / 'history.sqlite'
    with sqlite3.connect(auth_path) as db:
        db.execute('CREATE TABLE users (id INTEGER, role TEXT)')
        db.executemany('INSERT INTO users VALUES (?,?)', [(1, 'student'), (2, 'mentor')])
        db.execute('CREATE TABLE mentor_assignments (student_id INTEGER, mentor_id INTEGER, assigned_by INTEGER)')
        db.execute('INSERT INTO mentor_assignments VALUES (1,2,9)')
        db.execute('CREATE TABLE sessions (token_hash TEXT)')
        db.execute("INSERT INTO sessions VALUES ('secret-token')")
        db.execute('CREATE TABLE future_table (value TEXT)')
        db.execute("INSERT INTO future_table VALUES ('private')")
    with sqlite3.connect(history_path) as db:
        db.execute('CREATE TABLE study_resources (id INTEGER, student_id INTEGER, author_id INTEGER, content BLOB)')
        db.execute('INSERT INTO study_resources VALUES (1,1,2,?)', (b'private content',))
        db.execute('CREATE TABLE placement_history (student_id INTEGER, updated_by INTEGER)')
        db.execute('INSERT INTO placement_history VALUES (1,2)')
        db.execute('CREATE TABLE resource_notification_outbox (resource_id INTEGER, status TEXT)')
        db.executemany('INSERT INTO resource_notification_outbox VALUES (?,?)', [(1, 'pending'), (9, 'sent')])
    result = inspect_databases(str(auth_path), str(history_path))
    assert result['auth_tables']['mentor_assignments']['references']['assigned_by']['unknown_user'] == 1
    assert result['tables']['study_resources']['total_bytes'] == len(b'private content')
    assert result['tables']['placement_history']['rows'] == 1
    assert result['tables']['resource_notification_outbox']['status_counts'] == {'pending': 1, 'sent': 1}
    assert result['tables']['resource_notification_outbox']['missing_resource'] == 1
    assert result['unrecognized_tables']['auth'] == {'future_table': 1}
    assert 'secret-token' not in str(result) and 'private content' not in str(result)
