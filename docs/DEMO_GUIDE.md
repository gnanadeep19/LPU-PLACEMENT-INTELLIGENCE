# Local demonstration guide

## Demo accounts

Generate an isolated synthetic demo workspace from the repository root:

```powershell
py -3 backend\seed_demo_data.py
```

The script prompts you to choose one password for the local demo accounts. It
creates the accounts below and saves records only under `backend/data/demo/`.
No password is stored in this repository.

| Username | Role | Cohort |
|---|---|---|
| `admin.demo` | Administrator | Institution |
| `placement.demo` | Placement officer | Institution |
| `mentor.cse` | Mentor | `CSE-2027` |
| `mentor.it` | Mentor | `IT-2027` |
| `student.cse01`–`student.cse08` | Student | `CSE-2027` |
| `student.it01`–`student.it08` | Student | `IT-2027` |

The same password chosen during seeding works for the accounts. It is for a
local demonstration only. Never reuse it on an internet-facing deployment.
The 16 student profiles are generated synthetic examples. Each cohort has
enough records to demonstrate cohort filters and the default minimum-size
aggregate suppression behavior.

Before starting Flask in the same PowerShell session, point it to the isolated
demo databases:

```powershell
$env:APP_ENV = 'development'
$env:AUTH_DATABASE_PATH = 'backend/data/demo/auth.sqlite3'
$env:HISTORY_DATABASE_PATH = 'backend/data/demo/assessment_history.sqlite3'
py backend\app.py
```

Start the frontend separately using `cd frontend; npm run dev`. The app banner
identifies demo data and reminds users that readiness is advisory and is not a
placement guarantee.

## Reset demo data

Stop the backend process first. Then run:

```powershell
py -3 backend\seed_demo_data.py --reset
```

The script asks you to type `RESET DEMO DATA`; it deletes only the demo
authentication and assessment SQLite files under the fixed
`backend/data/demo/` directory, then recreates the demo. It does not touch the
default project databases, source datasets, model reports, or model artifact.

## Walkthroughs

- **Student:** inspect the readiness estimate and evidence coverage, open role
  gaps, add one prioritized action, submit project evidence, and send a
  correction request.
- **Mentor:** open the support queue, review a student’s signal and assessment
  age, record a check-in, set a student-visible goal with a due date, and review
  completion at the next check-in.
- **Admin:** compare cohorts with coverage denominators, review placement stages
  separately from readiness, inspect model limitations, and process evidence or
  profile-correction requests.

## Data and model note

The demo model's label is the project dataset field `placement_ready`. Its
meaning and source provenance are unverified for LPU placement outcomes. The
evaluation workflow reports row counts and metrics, but current results do not
establish generalization to LPU students. Use only synthetic demo data in public
presentations.
