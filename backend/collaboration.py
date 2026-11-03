"""Shared coaching and placement workflow records stored beside assessments."""

from __future__ import annotations

import json
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from history import _connection as _assessment_connection


STAGES = ("Eligible", "Preparing", "Applied", "Shortlisted", "Interviewing", "Offered", "Placed", "Opted out")
KINDS = ("goal", "note", "check_in", "referral")
TARGET_ROLES = ("Software Developer", "Data Analyst", "Business Analyst", "UX Designer", "Sales / Marketing Associate")
EVIDENCE_TYPES = ("project", "internship", "certification", "portfolio", "skill")


def _connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    db.executescript("""
        CREATE TABLE IF NOT EXISTS coaching_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            kind TEXT NOT NULL CHECK(kind IN ('goal','note','check_in','referral')),
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            due_date TEXT,
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','in_progress','completed')),
            visibility TEXT NOT NULL DEFAULT 'student' CHECK(visibility IN ('student','mentor')),
            evidence_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_coaching_student ON coaching_records(student_id, created_at);
        CREATE TABLE IF NOT EXISTS study_resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            author_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            filename TEXT NOT NULL,
            content BLOB NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_study_resources_student ON study_resources(student_id, created_at);
        CREATE TABLE IF NOT EXISTS cv_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            content BLOB NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','approved','changes_requested')),
            feedback TEXT NOT NULL DEFAULT '',
            reviewer_id INTEGER,
            submitted_at TEXT NOT NULL,
            reviewed_at TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_cv_student ON cv_submissions(student_id, id DESC);
        CREATE TABLE IF NOT EXISTS resource_notification_outbox (
            resource_id INTEGER PRIMARY KEY REFERENCES study_resources(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','sent')),
            attempts INTEGER NOT NULL DEFAULT 0,
            last_attempt_at TEXT,
            sent_at TEXT
        );
        CREATE TABLE IF NOT EXISTS placement_events (
            student_id INTEGER PRIMARY KEY,
            stage TEXT NOT NULL,
            company TEXT NOT NULL DEFAULT '',
            target_role TEXT NOT NULL DEFAULT '',
            updated_by INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS placement_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            stage TEXT NOT NULL,
            company TEXT NOT NULL DEFAULT '',
            target_role TEXT NOT NULL DEFAULT '',
            updated_by INTEGER NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_placement_history_student ON placement_history(student_id, updated_at);
        CREATE TABLE IF NOT EXISTS staff_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            subject_id INTEGER,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS student_settings (
            student_id INTEGER PRIMARY KEY,
            target_role TEXT NOT NULL,
            target_roles TEXT NOT NULL DEFAULT '[]',
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS profile_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            evidence_type TEXT NOT NULL CHECK(evidence_type IN ('project','internship','certification','portfolio','skill')),
            title TEXT NOT NULL,
            detail TEXT NOT NULL DEFAULT '',
            evidence_url TEXT,
            source TEXT NOT NULL DEFAULT 'self-reported',
            verification_status TEXT NOT NULL DEFAULT 'pending' CHECK(verification_status IN ('pending','verified','rejected')),
            submitted_at TEXT NOT NULL,
            verified_by INTEGER,
            verified_at TEXT
        );
        CREATE TABLE IF NOT EXISTS profile_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            current_value TEXT NOT NULL DEFAULT '',
            requested_value TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','reviewed','declined')),
            submitted_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewer_id INTEGER,
            resolution TEXT NOT NULL DEFAULT ''
        );
        CREATE INDEX IF NOT EXISTS idx_profile_corrections_status ON profile_corrections(status,submitted_at);
        CREATE INDEX IF NOT EXISTS idx_evidence_student ON profile_evidence(student_id, submitted_at);
    """)
    settings_columns = {row["name"] for row in db.execute("PRAGMA table_info(student_settings)").fetchall()}
    if "target_roles" not in settings_columns:
        db.execute("ALTER TABLE student_settings ADD COLUMN target_roles TEXT NOT NULL DEFAULT '[]'")
    resource_columns = {row["name"] for row in db.execute("PRAGMA table_info(study_resources)").fetchall()}
    if "category" not in resource_columns:
        db.execute("ALTER TABLE study_resources ADD COLUMN category TEXT NOT NULL DEFAULT 'General'")
    return db


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def list_records(path: str | Path, student_id: int, *, include_private: bool) -> list[dict[str, Any]]:
    db = _connect(path)
    try:
        sql = "SELECT * FROM coaching_records WHERE student_id = ?"
        args: list[Any] = [student_id]
        if not include_private:
            sql += " AND visibility = 'student'"
        rows = db.execute(sql + " ORDER BY created_at DESC, id DESC", args).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def list_evidence(path: str | Path, student_id: int) -> list[dict[str, Any]]:
    db = _connect(path)
    try:
        return [dict(row) for row in db.execute("SELECT * FROM profile_evidence WHERE student_id=? ORDER BY submitted_at DESC,id DESC",(student_id,)).fetchall()]
    finally:
        db.close()


def create_evidence(path: str | Path, *, student_id: int, evidence_type: str,
                    title: str, detail: str = "", evidence_url: str = "") -> dict[str, Any]:
    if evidence_type not in EVIDENCE_TYPES:
        raise ValueError("Choose a supported evidence type.")
    title, detail, evidence_url = str(title).strip(), str(detail).strip(), str(evidence_url).strip()
    if not 1 <= len(title) <= 140 or len(detail) > 2000:
        raise ValueError("Enter a title (1–140 characters) and keep details under 2,000 characters.")
    parsed_url = urlparse(evidence_url) if evidence_url else None
    if evidence_url and (len(evidence_url)>500 or parsed_url.scheme not in {"http","https"} or not parsed_url.netloc):
        raise ValueError("Evidence must be a valid HTTP or HTTPS link.")
    db = _connect(path)
    try:
        duplicate = db.execute("""SELECT id FROM profile_evidence
            WHERE student_id=? AND evidence_type=? AND title=? COLLATE NOCASE
              AND evidence_url IS ? AND verification_status='pending' LIMIT 1""",
            (student_id,evidence_type,title,evidence_url or None)).fetchone()
        if duplicate:
            raise ValueError("This evidence item is already awaiting review.")
        cursor=db.execute("""INSERT INTO profile_evidence(student_id,evidence_type,title,detail,evidence_url,submitted_at)
            VALUES(?,?,?,?,?,?)""",(student_id,evidence_type,title,detail,evidence_url or None,_now()))
        db.commit()
        return dict(db.execute("SELECT * FROM profile_evidence WHERE id=?",(cursor.lastrowid,)).fetchone())
    finally:
        db.close()


def verify_evidence(path: str | Path, evidence_id: int, *, status: str, verifier_id: int) -> dict[str, Any] | None:
    if status not in {"verified","rejected","pending"}:
        raise ValueError("Choose a valid verification status.")
    db = _connect(path)
    try:
        row=db.execute("SELECT * FROM profile_evidence WHERE id=?",(evidence_id,)).fetchone()
        if row is None: return None
        db.execute("UPDATE profile_evidence SET verification_status=?,verified_by=?,verified_at=? WHERE id=?",
                   (status,verifier_id,_now() if status != "pending" else None,evidence_id))
        db.commit()
        return dict(db.execute("SELECT * FROM profile_evidence WHERE id=?",(evidence_id,)).fetchone())
    finally:
        db.close()


def create_profile_correction(path: str | Path, *, student_id: int, field_name: str,
                              current_value: str, requested_value: str, reason: str) -> dict[str, Any]:
    field_name, current_value = str(field_name).strip()[:80], str(current_value).strip()[:300]
    requested_value, reason = str(requested_value).strip()[:300], str(reason).strip()[:1000]
    if not field_name or not requested_value or not reason:
        raise ValueError("Enter the field, corrected value, and reason for the correction.")
    db = _connect(path)
    try:
        cursor = db.execute("""INSERT INTO profile_corrections
            (student_id,field_name,current_value,requested_value,reason,submitted_at)
            VALUES(?,?,?,?,?,?)""", (student_id,field_name,current_value,requested_value,reason,_now()))
        db.commit()
        return dict(db.execute("SELECT * FROM profile_corrections WHERE id=?", (cursor.lastrowid,)).fetchone())
    finally:
        db.close()


def list_profile_corrections(path: str | Path, *, student_id: int | None = None) -> list[dict[str, Any]]:
    db = _connect(path)
    try:
        if student_id is None:
            rows = db.execute("SELECT * FROM profile_corrections ORDER BY submitted_at DESC,id DESC").fetchall()
        else:
            rows = db.execute("SELECT * FROM profile_corrections WHERE student_id=? ORDER BY submitted_at DESC,id DESC", (student_id,)).fetchall()
        return [dict(row) for row in rows]
    finally:
        db.close()


def review_profile_correction(path: str | Path, correction_id: int, *, status: str,
                              reviewer_id: int, resolution: str = "") -> dict[str, Any] | None:
    if status not in {"reviewed", "declined"}:
        raise ValueError("Choose reviewed or declined for the correction request.")
    resolution = str(resolution).strip()[:1000]
    db = _connect(path)
    try:
        db.execute("UPDATE profile_corrections SET status=?,reviewed_at=?,reviewer_id=?,resolution=? WHERE id=?",
                   (status,_now(),reviewer_id,resolution,correction_id))
        db.commit()
        row = db.execute("SELECT * FROM profile_corrections WHERE id=?", (correction_id,)).fetchone()
        return dict(row) if row else None
    finally:
        db.close()


def validate_record(*, kind: str, title: str, detail: str = "", due_date: str | None = None,
                    visibility: str = "student") -> tuple[str, str, str | None, str]:
    if kind not in KINDS:
        raise ValueError("Choose a supported coaching record type.")
    title = str(title).strip()
    detail = str(detail).strip()
    if not 1 <= len(title) <= 140 or len(detail) > 2000:
        raise ValueError("Enter a title (1–140 characters) and keep details under 2,000 characters.")
    if due_date:
        try:
            date.fromisoformat(due_date)
        except (TypeError, ValueError) as exc:
            raise ValueError("Due date must be a valid ISO date.") from exc
    if visibility not in {"student", "mentor"}:
        raise ValueError("Choose student-visible or mentor-only visibility.")
    return title, detail, due_date or None, visibility


def create_record(path: str | Path, *, student_id: int, author_id: int, kind: str,
                  title: str, detail: str = "", due_date: str | None = None,
                  visibility: str = "student") -> dict[str, Any]:
    title, detail, due_date, visibility = validate_record(
        kind=kind, title=title, detail=detail, due_date=due_date, visibility=visibility)
    now = _now()
    db = _connect(path)
    try:
        cursor = db.execute("""INSERT INTO coaching_records
            (student_id,author_id,kind,title,detail,due_date,visibility,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)""",
            (student_id, author_id, kind, title, detail, due_date or None, visibility, now, now))
        db.commit()
        return dict(db.execute("SELECT * FROM coaching_records WHERE id=?", (cursor.lastrowid,)).fetchone())
    finally:
        db.close()


def validate_record_update(*, status: str | None = None, evidence_url: str | None = None) -> str | None:
    if status is not None and status not in {"open", "in_progress", "completed"}:
        raise ValueError("Choose a valid action status.")
    evidence = None if evidence_url is None else str(evidence_url).strip()
    parsed_url = urlparse(evidence) if evidence else None
    if evidence and (len(evidence) > 500 or parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc):
        raise ValueError("Evidence must be a valid HTTP or HTTPS link.")
    return evidence


def update_record(path: str | Path, record_id: int, *, status: str | None = None,
                  evidence_url: str | None = None, actor_id: int | None = None) -> dict[str, Any] | None:
    evidence = validate_record_update(status=status, evidence_url=evidence_url)
    db = _connect(path)
    try:
        row = db.execute("SELECT * FROM coaching_records WHERE id=?", (record_id,)).fetchone()
        if row is None:
            return None
        db.execute("""UPDATE coaching_records SET status=COALESCE(?,status),
            evidence_url=COALESCE(?,evidence_url), updated_at=? WHERE id=?""",
            (status, evidence, _now(), record_id))
        db.commit()
        return dict(db.execute("SELECT * FROM coaching_records WHERE id=?", (record_id,)).fetchone())
    finally:
        db.close()


def latest_students(history_path: str | Path, auth_path: str | Path, *, cohort: str | None) -> list[dict[str, Any]]:
    history = _assessment_connection(history_path)
    try:
        where = "WHERE cohort = ?" if cohort else ""
        args = (cohort,) if cohort else ()
        rows = history.execute(f"""SELECT a.user_id,a.cohort,a.student_json,a.readiness_score,
            a.readiness_category,a.created_at,
            (SELECT p.readiness_score FROM assessments p WHERE p.user_id=a.user_id
             ORDER BY p.id DESC LIMIT 1 OFFSET 1) AS previous_score
            FROM assessments a
            JOIN (SELECT user_id,MAX(id) AS latest_id FROM assessments
              WHERE user_id IS NOT NULL {('AND cohort = ?' if cohort else '')}
              GROUP BY user_id) latest ON latest.latest_id=a.id
            {where} ORDER BY a.readiness_score ASC""", args + args).fetchall()
        records = [dict(row) for row in rows]
    finally:
        history.close()
    auth = sqlite3.connect(auth_path, timeout=10)
    auth.row_factory = sqlite3.Row
    try:
        users = {row["id"]: dict(row) for row in auth.execute(
            "SELECT id,username,display_name,role,cohort FROM users WHERE is_active=1").fetchall()}
    finally:
        auth.close()
    db = _connect(history_path)
    try:
        settings = {}
        for row in db.execute("SELECT student_id,target_role,target_roles FROM student_settings").fetchall():
            roles = json.loads(row["target_roles"] or "[]")
            settings[row["student_id"]] = roles or [row["target_role"]]
        evidence_by_student: dict[int, list[dict[str, Any]]] = {}
        for row in db.execute("SELECT * FROM profile_evidence ORDER BY submitted_at DESC,id DESC").fetchall():
            evidence_by_student.setdefault(row["student_id"], []).append(dict(row))
    finally:
        db.close()
    result = []
    for item in records:
        user = users.get(item["user_id"])
        if not user or user["role"] != "student" or (cohort and user["cohort"] != cohort):
            continue
        profile = json.loads(item.pop("student_json"))
        item.update({"username": user["username"], "display_name": user["display_name"],
                     "cohort": user["cohort"], "profile": profile,
                     "target_roles": settings.get(item["user_id"], []),
                     "target_role": (settings.get(item["user_id"]) or ["Not selected"])[0]})
        item["evidence"] = evidence_by_student.get(item["user_id"], [])
        result.append(item)
    return result


def save_target_role(path: str | Path, student_id: int, target_roles: Any) -> dict[str, Any]:
    if isinstance(target_roles, str):
        target_roles = [target_roles]
    if not isinstance(target_roles, list) or not 1 <= len(target_roles) <= len(TARGET_ROLES) or any(role not in TARGET_ROLES for role in target_roles):
        raise ValueError("Choose one or more supported target roles.")
    target_roles = list(dict.fromkeys(target_roles))
    updated_at = _now()
    db = _connect(path)
    try:
        db.execute("""INSERT INTO student_settings(student_id,target_role,target_roles,updated_at) VALUES(?,?,?,?)
            ON CONFLICT(student_id) DO UPDATE SET target_role=excluded.target_role,
            target_roles=excluded.target_roles,updated_at=excluded.updated_at""",
            (student_id,target_roles[0],json.dumps(target_roles),updated_at))
        db.commit()
        return {"target_role": target_roles[0], "target_roles": target_roles, "updated_at": updated_at}
    finally:
        db.close()


def get_student_profile(path: str | Path, student_id: int) -> dict[str, Any]:
    db = _assessment_connection(path)
    try:
        row = db.execute("""SELECT student_json,readiness_score,readiness_category,created_at
            FROM assessments WHERE user_id=? ORDER BY id DESC LIMIT 1""", (student_id,)).fetchone()
    finally:
        db.close()
    store = _connect(path)
    try:
        settings = store.execute("SELECT target_role,target_roles,updated_at FROM student_settings WHERE student_id=?", (student_id,)).fetchone()
    finally:
        store.close()
    return {
        "profile": json.loads(row["student_json"]) if row else None,
        "last_assessed_at": row["created_at"] if row else None,
        "latest_readiness": row["readiness_score"] if row else None,
        "readiness_category": row["readiness_category"] if row else None,
        "target_role": settings["target_role"] if settings else TARGET_ROLES[0],
        "target_roles": (json.loads(settings["target_roles"] or "[]") or [settings["target_role"]]) if settings else [TARGET_ROLES[0]],
        "target_role_updated_at": settings["updated_at"] if settings else None,
    }


def save_placement(path: str | Path, *, student_id: int, stage: str, company: str,
                   target_role: str, updated_by: int) -> dict[str, Any]:
    if stage not in STAGES:
        raise ValueError("Choose a supported placement stage.")
    company, target_role = str(company).strip()[:120], str(target_role).strip()[:120]
    db = _connect(path)
    try:
        previous = db.execute("SELECT * FROM placement_events WHERE student_id=?", (student_id,)).fetchone()
        if previous and not db.execute("SELECT 1 FROM placement_history WHERE student_id=? LIMIT 1", (student_id,)).fetchone():
            db.execute("INSERT INTO placement_history(student_id,stage,company,target_role,updated_by,updated_at) VALUES(?,?,?,?,?,?)",
                       (previous['student_id'], previous['stage'], previous['company'], previous['target_role'], previous['updated_by'], previous['updated_at']))
        updated_at = _now()
        db.execute("""INSERT INTO placement_events(student_id,stage,company,target_role,updated_by,updated_at)
            VALUES(?,?,?,?,?,?) ON CONFLICT(student_id) DO UPDATE SET stage=excluded.stage,
            company=excluded.company,target_role=excluded.target_role,updated_by=excluded.updated_by,
            updated_at=excluded.updated_at""",
            (student_id, stage, company, target_role, updated_by, updated_at))
        db.execute("INSERT INTO placement_history(student_id,stage,company,target_role,updated_by,updated_at) VALUES(?,?,?,?,?,?)",
                   (student_id, stage, company, target_role, updated_by, updated_at))
        db.commit()
        return dict(db.execute("SELECT * FROM placement_events WHERE student_id=?", (student_id,)).fetchone())
    finally:
        db.close()


def list_placements(path: str | Path) -> list[dict[str, Any]]:
    db = _connect(path)
    try:
        return [dict(row) for row in db.execute("SELECT * FROM placement_events ORDER BY updated_at DESC").fetchall()]
    finally:
        db.close()


def audit(path: str | Path, *, actor_id: int, action: str, subject_id: int | None = None) -> None:
    db = _connect(path)
    try:
        db.execute("INSERT INTO staff_audit(actor_id,action,subject_id,created_at) VALUES(?,?,?,?)",
                   (actor_id, action[:80], subject_id, _now()))
        db.commit()
    finally:
        db.close()


def list_audit(path: str | Path, limit: int = 100) -> list[dict[str, Any]]:
    db = _connect(path)
    try:
        return [dict(row) for row in db.execute("SELECT * FROM staff_audit ORDER BY id DESC LIMIT ?", (max(1, min(limit, 500)),)).fetchall()]
    finally:
        db.close()
