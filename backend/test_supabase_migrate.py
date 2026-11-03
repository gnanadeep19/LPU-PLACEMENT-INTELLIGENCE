import csv
import sqlite3
import sys
import types

import pytest

import collaboration
import history
from supabase_migrate import _insert_resources, apply_plan, load_mapping, make_plan, verify_target_profiles


STUDENT = '4d9e8e7d-b06c-4c79-8873-8a1d7ba61c08'
MENTOR = '62eecc92-8ed8-4cf6-b0f7-971d6bb76ad6'


@pytest.fixture
def local_data(tmp_path):
    auth_db, history_db = tmp_path / 'auth.sqlite', tmp_path / 'history.sqlite'
    with sqlite3.connect(auth_db) as db:
        db.execute('CREATE TABLE users (id INTEGER, username TEXT, role TEXT, cohort TEXT, is_active INTEGER)')
        db.executemany('INSERT INTO users VALUES (?,?,?,?,?)', [(1, 'student.a', 'student', 'CSE-A', 1), (2, 'mentor.a', 'mentor', 'CSE-A', 1)])
    db = history._connection(history_db)
    db.executemany('INSERT INTO assessments (profile_hash,readiness_score,readiness_category,model_probability,student_json,user_id,cohort) VALUES (?,?,?,?,?,?,?)', [
        ('abc', 50, 'Developing', .5, '{"cgpa": 7}', 1, 'CSE-A'),
        ('def', 30, 'Developing', .3, '{"cgpa": 6}', None, None),
    ])
    db.commit()
    db.close()
    db = collaboration._connect(history_db)
    db.execute("INSERT INTO coaching_records (student_id,author_id,kind,title,visibility,created_at,updated_at) VALUES (1,2,'note','Private','mentor','2026-01-01','2026-01-01')")
    db.commit()
    db.close()
    return auth_db, history_db


def test_plan_maps_accounts_and_keeps_anonymous_assessments_out(local_data):
    auth_db, history_db = local_data
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    assert plan['counts']['assessments'] == {'present': True, 'rows': 2, 'ready': 1, 'unmapped': 1}
    assert plan['records']['assessments'][0]['user_id'] == STUDENT
    assert plan['records']['assessments'][0]['student_json'] == {'cgpa': 7}
    note = plan['records']['coaching_records'][0]
    assert note['student_id'] == STUDENT and note['author_id'] == MENTOR
    assert note['visibility'] == 'mentor' and note['legacy_id'] == 1
    with sqlite3.connect(history_db) as db:
        assert db.execute('SELECT count(*) FROM assessments').fetchone()[0] == 2


def test_plan_does_not_guess_a_missing_reviewer_mapping(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO profile_evidence (student_id,evidence_type,title,submitted_at,verified_by) VALUES (1,'project','Project','2026-01-01',2)")
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT})
    assert plan['counts']['profile_evidence']['unmapped'] == 1
    assert not plan['records']['profile_evidence']


def test_plan_preserves_placement_history_and_staff_identity(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO placement_history(student_id,stage,company,target_role,updated_by,updated_at) VALUES (1,'Applied','Example','Developer',2,'2026-01-01T10:00:00Z')")
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    event = plan['records']['placement_history'][0]
    assert event['legacy_id'] == 1 and event['student_id'] == STUDENT and event['updated_by'] == MENTOR
    assert event['stage'] == 'Applied' and event['updated_at'] == '2026-01-01T10:00:00Z'
    assert plan['counts']['placement_history']['ready'] == 1
    assert 'placement_history' not in plan['unsupported_tables']['history']


def test_plan_does_not_guess_placement_history_author(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO placement_history(student_id,stage,updated_by,updated_at) VALUES (1,'Applied',2,'2026-01-01T10:00:00Z')")
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT})
    assert plan['counts']['placement_history']['unmapped'] == 1
    assert not plan['records']['placement_history']


def test_mapping_rejects_duplicate_users(tmp_path):
    mapping = tmp_path / 'mapping.csv'
    with mapping.open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerows([('legacy_id', 'auth_user_id'), (1, STUDENT), (2, STUDENT)])
    with pytest.raises(ValueError, match='unique'):
        load_mapping(str(mapping))


def test_rejects_mismatched_target_role(local_data):
    auth_db, history_db = local_data
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT})
    target = {'id': STUDENT, 'legacy_id': 1, 'username': 'student.a', 'role': 'admin', 'cohort': 'CSE-A', 'is_active': True}
    with pytest.raises(ValueError, match='does not match'):
        verify_target_profiles(plan['users'], {1: STUDENT}, [target])


def test_refuses_unmapped_data_before_opening_target_cursor(local_data):
    auth_db, history_db = local_data
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    with pytest.raises(ValueError, match='Unmapped records'):
        apply_plan(None, plan, {1: STUDENT, 2: MENTOR})


def test_import_refuses_unmigrated_assignments_and_unknown_tables(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(auth_db) as db:
        db.execute('CREATE TABLE mentor_assignments (student_id INTEGER, mentor_id INTEGER)')
        db.execute('INSERT INTO mentor_assignments VALUES (1,2)')
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?, '2026-01-01')", (b'notes',))
        db.execute('CREATE TABLE future_feature (value TEXT)')
        db.execute("INSERT INTO future_feature VALUES ('not exported')")
    mapping = {1: STUDENT, 2: MENTOR}
    plan = make_plan(str(auth_db), str(history_db), mapping)
    assert plan['unsupported_tables']['auth']['mentor_assignments'] == 1
    assert plan['counts']['study_resources']['ready'] == 1
    assert plan['unsupported_tables']['history']['future_feature'] == 1
    with pytest.raises(ValueError, match='Unsupported source tables'):
        apply_plan(None, plan, mapping, allow_unmapped=True)


def test_full_import_refuses_to_silently_leave_cv_submissions_behind(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO cv_submissions(student_id,filename,content,submitted_at) VALUES (1,'cv.pdf',?,'2026-01-01')", (b'%PDF-test',))
    mapping = {1: STUDENT, 2: MENTOR}
    plan = make_plan(str(auth_db), str(history_db), mapping)
    assert plan['unsupported_tables']['history']['cv_submissions'] == 1
    with pytest.raises(ValueError, match='Unsupported source tables'):
        apply_plan(None, plan, mapping, allow_unmapped=True)


def test_resource_plan_imports_exact_bytes_without_storing_them_in_the_plan(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,description,filename,category,content,created_at) VALUES (1,2,'Guide','Practice','guide.txt','Coding',?,'2026-01-01')", (b'sample notes',))
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    assert plan['counts']['study_resources'] == {'present': True, 'rows': 1, 'ready': 1, 'unmapped': 0}
    assert b'sample notes' not in repr(plan['resources']).encode()
    class Cursor:
        def __init__(self): self.inserts = []
        def executemany(self, statement, rows): self.inserts.append((statement, rows))
    cursor = Cursor()
    _insert_resources(cursor, str(history_db), plan['resources'], plan['resource_ids'])
    assert len(cursor.inserts) == 1
    row = cursor.inserts[0][1][0]
    assert row[1:3] == (STUDENT, MENTOR)
    assert row[6] == 'Coding' and row[7] == b'sample notes'


def test_resource_import_refuses_changes_after_dry_run(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'original',))
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    with sqlite3.connect(history_db) as db:
        db.execute('UPDATE study_resources SET content=? WHERE id=1', (b'modified',))
    class Cursor:
        def executemany(self, *_args): pytest.fail('Changed content must not be imported')
    with pytest.raises(ValueError, match='content changed'):
        _insert_resources(Cursor(), str(history_db), plan['resources'], plan['resource_ids'])


def test_resource_plan_never_guesses_missing_author_mapping(local_data):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT})
    assert plan['counts']['study_resources']['unmapped'] == 1
    assert plan['resources'] == []


def test_resource_plan_rejects_file_larger_than_import_limit(local_data, monkeypatch):
    auth_db, history_db = local_data
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
    monkeypatch.setattr('supabase_migrate.RESOURCE_MAX_BYTES', 4)
    with pytest.raises(ValueError, match='exceeds'):
        make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})


def test_resource_import_detects_new_file_after_empty_plan(local_data):
    auth_db, history_db = local_data
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
    with pytest.raises(ValueError, match='inventory changed'):
        _insert_resources(None, str(history_db), plan['resources'], plan['resource_ids'])


def test_import_refuses_a_different_identity_mapping(local_data):
    auth_db, history_db = local_data
    plan = make_plan(str(auth_db), str(history_db), {1: STUDENT, 2: MENTOR})
    with pytest.raises(ValueError, match='mapping changed'):
        apply_plan(None, plan, {1: STUDENT}, allow_unmapped=True)


def test_import_refuses_a_plan_without_unsupported_table_inventory(local_data):
    auth_db, history_db = local_data
    mapping = {1: STUDENT, 2: MENTOR}
    plan = make_plan(str(auth_db), str(history_db), mapping)
    del plan['unsupported_tables']
    with pytest.raises(ValueError, match='inventory is missing'):
        apply_plan(None, plan, mapping, allow_unmapped=True)


def test_import_disables_historical_notifications_inside_transaction(local_data, monkeypatch):
    auth_db, history_db = local_data
    mapping = {1: STUDENT, 2: MENTOR}
    with sqlite3.connect(history_db) as db:
        db.execute("INSERT INTO study_resources(student_id,author_id,title,filename,content,created_at) VALUES (1,2,'Guide','guide.txt',?,'2026-01-01')", (b'notes',))
    plan = make_plan(str(auth_db), str(history_db), mapping)
    json_module = types.ModuleType('psycopg.types.json')
    json_module.Jsonb = lambda value: value
    monkeypatch.setitem(sys.modules, 'psycopg', types.ModuleType('psycopg'))
    monkeypatch.setitem(sys.modules, 'psycopg.types', types.ModuleType('psycopg.types'))
    monkeypatch.setitem(sys.modules, 'psycopg.types.json', json_module)

    class Cursor:
        def __init__(self): self.commands, self.inserts, self.last = [], [], ''
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, command): self.commands.append(command); self.last = command
        def fetchall(self): return [(STUDENT, 1, 'student.a', 'student', 'CSE-A', True), (MENTOR, 2, 'mentor.a', 'mentor', 'CSE-A', True)]
        def fetchone(self): return ('O',) if 'pg_catalog.pg_trigger' in self.last else (0,)
        def executemany(self, statement, values): self.inserts.append((statement, values))

    cursor = Cursor()
    connection = types.SimpleNamespace(cursor=lambda: cursor)
    apply_plan(connection, plan, mapping, allow_unmapped=True)
    disable = cursor.commands.index('ALTER TABLE public.coaching_records DISABLE TRIGGER coaching_notifications')
    enable = cursor.commands.index('ALTER TABLE public.coaching_records ENABLE TRIGGER coaching_notifications')
    assert disable < enable
    assert any('INSERT INTO public."coaching_records"' in statement for statement, _ in cursor.inserts)
    assert any('INSERT INTO public.study_resources' in statement and values[0][7] == b'notes' for statement, values in cursor.inserts)


def test_import_refuses_nonempty_target_before_any_write(local_data, monkeypatch):
    auth_db, history_db = local_data
    mapping = {1: STUDENT, 2: MENTOR}
    plan = make_plan(str(auth_db), str(history_db), mapping)
    json_module = types.ModuleType('psycopg.types.json')
    json_module.Jsonb = lambda value: value
    monkeypatch.setitem(sys.modules, 'psycopg', types.ModuleType('psycopg'))
    monkeypatch.setitem(sys.modules, 'psycopg.types', types.ModuleType('psycopg.types'))
    monkeypatch.setitem(sys.modules, 'psycopg.types.json', json_module)

    class Cursor:
        def __init__(self): self.commands = []
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def execute(self, command): self.commands.append(command)
        def fetchall(self): return [(STUDENT, 1, 'student.a', 'student', 'CSE-A', True), (MENTOR, 2, 'mentor.a', 'mentor', 'CSE-A', True)]
        def fetchone(self): return (1,)
        def executemany(self, *_args): pytest.fail('No insert should be attempted')

    cursor = Cursor()
    with pytest.raises(ValueError, match='not empty'):
        apply_plan(types.SimpleNamespace(cursor=lambda: cursor), plan, mapping, allow_unmapped=True)
    assert not any('DISABLE TRIGGER' in command for command in cursor.commands)
