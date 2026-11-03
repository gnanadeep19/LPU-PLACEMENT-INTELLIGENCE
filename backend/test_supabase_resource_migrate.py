"""Resource-only migration never merges or silently drops pending work."""
import sqlite3
import types

import pytest

from supabase_resource_migrate import apply_resource_plan, make_resource_plan
from test_supabase_migrate import local_data, STUDENT, MENTOR  # noqa: F401


@pytest.fixture
def resource_plan(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
        db.execute("INSERT INTO resource_notification_outbox(resource_id,status) VALUES (1,'sent')")
    mapping = {1: STUDENT, 2: MENTOR}
    return make_resource_plan(str(auth_db), str(history_db), mapping), mapping, history_db


class Cursor:
    def __init__(self, *, target_count=0, existing=None):
        self.commands, self.inserts = [], []
        self.target_count, self.existing = target_count, existing or []
    def __enter__(self): return self
    def __exit__(self, *_args): pass
    def execute(self, command): self.commands.append(command)
    def fetchall(self):
        if 'sha256(content)' in self.commands[-1]: return self.existing
        return [(STUDENT, 1, 'student.a', 'student', 'CSE-A', True), (MENTOR, 2, 'mentor.a', 'mentor', 'CSE-A', True)]
    def fetchone(self): return (self.target_count,)
    def executemany(self, statement, values): self.inserts.append((statement, values))


def test_resource_only_import_preserves_content_and_does_not_touch_other_tables(resource_plan):
    plan, mapping, _ = resource_plan
    cursor = Cursor()
    apply_resource_plan(types.SimpleNamespace(cursor=lambda: cursor), plan, mapping)
    assert plan['counts']['ready'] == 1
    assert len(cursor.inserts) == 1 and cursor.inserts[0][1][0][7] == b'notes'
    assert all('coaching_records' not in command for command in cursor.commands)


def test_resource_import_refuses_nonempty_target(resource_plan):
    plan, mapping, _ = resource_plan
    cursor = Cursor(target_count=1)
    with pytest.raises(ValueError, match='not empty'):
        apply_resource_plan(types.SimpleNamespace(cursor=lambda: cursor), plan, mapping)
    assert not cursor.inserts


def test_resource_import_can_preserve_distinct_nonimported_target(resource_plan):
    plan, mapping, _ = resource_plan
    cursor = Cursor(target_count=1, existing=[(None, STUDENT, MENTOR, 'a' * 64)])
    apply_resource_plan(types.SimpleNamespace(cursor=lambda: cursor), plan, mapping, allow_existing=True)
    assert len(cursor.inserts) == 1
    assert not any('DELETE' in command or 'UPDATE' in command for command in cursor.commands)


def test_resource_import_refuses_matching_content_and_previous_imports(resource_plan):
    plan, mapping, _ = resource_plan
    duplicate = Cursor(target_count=1, existing=[(None, STUDENT, MENTOR, plan['resources'][0]['sha256'])])
    with pytest.raises(ValueError, match='matching target resource'):
        apply_resource_plan(types.SimpleNamespace(cursor=lambda: duplicate), plan, mapping, allow_existing=True)
    assert not duplicate.inserts
    previous = Cursor(target_count=1, existing=[(99, STUDENT, MENTOR, 'a' * 64)])
    with pytest.raises(ValueError, match='previous import'):
        apply_resource_plan(types.SimpleNamespace(cursor=lambda: previous), plan, mapping, allow_existing=True)
    assert not previous.inserts


def test_resource_import_rejects_pending_notification_added_after_plan(resource_plan):
    plan, mapping, history_db = resource_plan
    with sqlite3.connect(history_db) as db:
        db.execute("UPDATE resource_notification_outbox SET status='pending'")
    with pytest.raises(ValueError, match='Pending resource notifications'):
        apply_resource_plan(None, plan, mapping)


def test_resource_import_rejects_unmapped_author(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
    with pytest.raises(ValueError, match='unmapped'):
        make_resource_plan(str(auth_db), str(history_db), {1: STUDENT})


def test_resource_import_rechecks_source_content(resource_plan):
    plan, mapping, history_db = resource_plan
    with sqlite3.connect(history_db) as db:
        db.execute("UPDATE study_resources SET content=? WHERE id=1", (b'other',))
    cursor = Cursor()
    with pytest.raises(ValueError, match='content changed'):
        apply_resource_plan(types.SimpleNamespace(cursor=lambda: cursor), plan, mapping)
    assert not cursor.inserts
