"""Create an isolated, synthetic local demo with all four user roles.

The script writes only under backend/data/demo. It never touches the default
auth or history databases. Pass --reset to replace the two demo SQLite files.
"""

from __future__ import annotations

import argparse
import getpass
import os
from pathlib import Path

import auth
import collaboration
import history
import model

BACKEND_DIR = Path(__file__).resolve().parent
DEMO_DIR = (BACKEND_DIR / "data" / "demo").resolve()
AUTH_DB = DEMO_DIR / "auth.sqlite3"
HISTORY_DB = DEMO_DIR / "assessment_history.sqlite3"
MODEL_FILE = DEMO_DIR / "placement_model.joblib"


def _password() -> str:
    first = getpass.getpass("Choose a local demo password (12+ characters): ")
    second = getpass.getpass("Confirm demo password: ")
    if first != second:
        raise SystemExit("Passwords did not match.")
    if len(first) < 12:
        raise SystemExit("Use at least 12 characters.")
    return first


def _reset_demo_files() -> None:
    if not DEMO_DIR.exists():
        return
    expected_parent = (BACKEND_DIR / "data").resolve()
    if DEMO_DIR.parent != expected_parent or DEMO_DIR.name != "demo":
        raise SystemExit("Refusing reset because the demo path did not match its fixed location.")
    confirmation = input("Type RESET DEMO DATA to delete the isolated demo accounts and activity: ")
    if confirmation != "RESET DEMO DATA":
        raise SystemExit("Reset cancelled; no files were changed.")
    for filename in ("auth.sqlite3", "auth.sqlite3-wal", "auth.sqlite3-shm",
                     "assessment_history.sqlite3", "assessment_history.sqlite3-wal",
                     "assessment_history.sqlite3-shm"):
        target = (DEMO_DIR / filename).resolve()
        if target.parent != DEMO_DIR:
            raise SystemExit("Refusing to remove a file outside the demo directory.")
        if target.exists():
            target.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reset", action="store_true", help="Confirm and reset only the isolated demo databases before seeding")
    args = parser.parse_args()
    if os.environ.get("APP_ENV", "development").lower() == "production":
        raise SystemExit("Demo seeding is disabled when APP_ENV=production.")
    if args.reset:
        _reset_demo_files()
    elif AUTH_DB.exists() or HISTORY_DB.exists():
        raise SystemExit("Demo data already exists. Use --reset to confirm a clean reseed.")
    DEMO_DIR.mkdir(parents=True, exist_ok=True)
    password = _password()

    roles = [
        ("admin.demo", "Demo Administrator", "admin", None),
        ("placement.demo", "Demo Placement Officer", "placement_officer", None),
        ("mentor.cse", "Demo CSE Mentor", "mentor", "CSE-2027"),
        ("mentor.it", "Demo IT Mentor", "mentor", "IT-2027"),
    ]
    students = []
    for cohort, prefix in (("CSE-2027", "cse"), ("IT-2027", "it")):
        for index in range(1, 9):
            students.append((f"student.{prefix}{index:02d}", f"{cohort} Demo Student {index:02d}", "student", cohort))
    account_ids: dict[str, int] = {}
    for username, display_name, role, cohort in roles + students:
        existing = next((item for item in auth.list_users(AUTH_DB) if item["username"] == username), None)
        if existing:
            account_ids[username] = existing["id"]
            continue
        user = auth.create_user(AUTH_DB, username=username, password=password,
                                display_name=display_name, role=role, cohort=cohort)
        account_ids[username] = user["id"]

    if MODEL_FILE.exists():
        payload = model.load_model(str(MODEL_FILE))
    else:
        payload = model.train_placement_model(save_path=str(MODEL_FILE))
    profiles = model.generate_synthetic_student_data(len(students), random_state=2027)
    stages = ("Preparing", "Applied", "Shortlisted", "Interviewing", "Offered", "Placed")
    student_rows = iter(students)
    for index, (_, row) in enumerate(profiles.iterrows()):
        username, _, _, cohort = next(student_rows)
        profile = {feature: row[feature].item() if hasattr(row[feature], "item") else row[feature]
                   for feature in model.FEATURE_NAMES}
        prediction = model.predict_student_readiness(payload, profile)
        history.save_assessment(profile, prediction, HISTORY_DB,
                                user_id=account_ids[username], cohort=cohort)
        if index % 3 == 0:
            collaboration.create_record(HISTORY_DB, student_id=account_ids[username],
                author_id=account_ids["mentor.cse" if cohort == "CSE-2027" else "mentor.it"],
                kind="goal", title="Complete a role-aligned practice assessment",
                detail="Retake a comparable assessment and attach your result link.",
                due_date=None, visibility="student")
        collaboration.save_placement(HISTORY_DB, student_id=account_ids[username],
            stage=stages[index % len(stages)], company="Demo employer", target_role="Software Developer",
            updated_by=account_ids["placement.demo"])

    print(f"Seeded {len(students)} synthetic students across CSE-2027 and IT-2027.")
    print(f"Accounts use the password you entered. Demo databases: {DEMO_DIR}")
    print("Set AUTH_DATABASE_PATH and HISTORY_DATABASE_PATH to the two demo files before starting the API.")
    print("Demo data is synthetic and must not be copied into a production environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
