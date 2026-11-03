# Connected student, mentor, and placement workspaces

The student, mentor, and placement views now share the Flask API and local
SQLite stores. Accounts are provisioned by an administrator; roles are never
selected by the user in the browser.

## Student workspace

- Restores the latest assessment saved for the authenticated account.
- Stores one or more target roles with that account.
- Compares the profile against project-defined starter role requirements.
- Explains model factors, shows input coverage and freshness, and keeps a
  history of assessments.
- Saves personal goals, due dates, progress, and evidence links.
- Stores separate student-submitted project, internship, certification, portfolio,
  and skill evidence records. Evidence is pending review until an admin verifies
  it.
- Shows a notice that assessment data is self-reported and the project uses
  local authentication rather than LPU SSO.

Role requirements are provisional project choices, not official placement-cell
or employer requirements. They do not change the model prediction.

## Mentor workspace

- `GET /api/mentor/students` returns each assessed student's latest profile in
  the authenticated mentor's assigned cohort. Other staff roles have their
  institution-wide scope.
- `GET/POST /api/students/<id>/coaching` reads or records goals, meeting notes,
  check-ins, and referrals. `PATCH` on a record updates a goal's status or
  evidence link.
- `GET/POST /api/students/<id>/evidence` reads or submits portfolio/evidence
  records. `PATCH /api/students/<id>/evidence/<evidence-id>` is admin-only and
  records verification status.
- Mentors may add student-visible records or private-to-mentor-team notes.
  Students can read and update their own student-visible goals only.
- The roster includes score change, target role, data coverage, support signals,
  and the shared action timeline. Aggregate gap analytics remain subject to
  `COHORT_MIN_GROUP_SIZE` suppression.
- Mentor assignment is cohort-based. There is no individual mentor-student
  assignment table yet.

## Placement and admin workspaces

- `GET /api/cohort-analytics` returns the latest cohort aggregate; mentors are
  restricted to their own cohort, while placement officers and admins receive
  institution-level aggregates.
- `GET/POST /api/placement-pipeline` reads or updates a manually recorded
  placement stage. Only placement officers and admins may change outcomes.
- `GET /api/model-info` exposes the active artifact's version, training date,
  feature thresholds, and available evaluation metadata.
- `GET /api/staff/audit` is admin-only. Assessment updates, target-role changes,
  staff roster/profile views, coaching changes, and placement stage changes are
  recorded without storing note text in the audit table.

The admin view starts with aggregated metrics and separates readiness estimates
from actual placement stages. Its student detail tables are available to
authenticated admin/placement staff, and the roster contains only accounts with
a saved assessment.

## Storage and limits

Assessment snapshots, target roles, coaching records, placement events, and the
audit log are stored in `HISTORY_DATABASE_PATH` (default:
`backend/data/assessment_history.sqlite3`). Account identity and cohort are in
`AUTH_DATABASE_PATH` (default: `backend/data/auth.sqlite3`). The current backend
uses local SQLite; it does not require Supabase.

The prediction model captures nine numeric fields only. Separate profile
evidence can hold project/portfolio links, internship details, certification
details, and skill evidence, but the app does not automatically check link
reachability or verify contents. Detailed course records, school/program/year,
consent receipts, and a retention schedule are not stored. The admin UI calls
these omissions out rather than treating them as verified.
Placement outcomes are manually recorded and must be checked against official
placement records.

This implementation is a project prototype, not an institutional deployment.
Review [`GOVERNANCE_BASELINE.md`](GOVERNANCE_BASELINE.md),
[`SECURITY_PRIVACY.md`](SECURITY_PRIVACY.md), and
[`FINAL_RELEASE_READINESS.md`](FINAL_RELEASE_READINESS.md) before any real
student-data use.
