# Assessment and progress history

Authenticated assessment snapshots are stored in the local SQLite development
database. Each assessment is associated with its authenticated `user_id` and
cohort; feature values remain in the database and are returned only to that
student's session or to staff permitted to view the student's cohort/profile.

## API

- `POST /api/history` saves `{ student, prediction }` for the authenticated user.
- `POST /api/history/query` returns the caller's saved profile history without
  putting feature values in a URL.
- `GET /api/student/profile` restores the latest saved profile and target roles
  for the signed-in student.

History is returned newest first for the progress view. The UI compares the two
most recent profiles and reports which input values changed; it does not claim
that any input caused a score movement. The API caps requests at 100 records.

The default SQLite database is
`backend/data/assessment_history.sqlite3`. Production retention, deletion,
encryption, and institutional ownership policies must be approved before real
student data is used.
