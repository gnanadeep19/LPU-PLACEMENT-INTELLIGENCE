# Authentication and role-based access

Implements the identity and authorization boundary previously missing from the
prototype. The provider is a **local credential store** (accounts provisioned
by the placement office), not an institutional SSO integration. It is a real
server-enforced boundary that can later be replaced behind the same session
API.

## Roles

| Role | Student workspace | Mentor workspace | Cohort scope |
|---|---|---|---|
| `student` | Yes | No | Own assessment history only |
| `mentor` | Yes | Yes | Own assigned cohort only |
| `placement_officer` | Yes | Placement workspace | Institution-wide analytics; may update placement stages |
| `admin` | Yes | Admin workspace | Institution-wide views, model info, placement stages + audit log |

Accounts are created with `backend/manage_users.py`:

```bash
py backend/manage_users.py create-user \
  --username mentor.cse --display-name "CSE Mentor" \
  --role mentor --cohort CSE-2027

py backend/manage_users.py list-users
py backend/manage_users.py set-password --username mentor.cse
py backend/manage_users.py deactivate-user --username mentor.cse
py backend/manage_users.py purge-sessions
```

Passwords are hashed with Werkzeug scrypt and must be at least 12 characters.
There is no self-registration. A mentor account cannot be created without a
cohort. Inside the production container, run
`docker compose exec backend python backend/manage_users.py ...`.

## Session design

- `POST /api/auth/login` verifies credentials and creates an opaque
  256-bit session token. Only its SHA-256 digest is stored in
  `auth.sqlite3`; the raw token exists only in the browser cookie.
- Cookies: `lpu_session` (`HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure`
  when `AUTH_COOKIE_SECURE=true`) and the readable `lpu_csrf` token.
- Sessions expire absolutely after `SESSION_TTL_SECONDS` (default 8 hours).
  Expired and deactivated-account sessions are rejected and deleted.
- Logout revokes the server record and clears both cookies.
- Changing a password or deactivating an account revokes all of that
  account's sessions.
- The frontend schedules a local notice at the server expiry time and also
  returns to the sign-in screen on any `401`, so an expired session is never a
  silent failure.

## CSRF

Every state-changing authenticated request (`POST`, `PUT`, `PATCH`, `DELETE`)
must send `X-CSRF-Token` equal to the session's CSRF token. The SPA reads the
`lpu_csrf` cookie and `apiClient` attaches the header automatically. Login is
exempt because no session exists yet. A missing or mismatched token returns
`403` before the route runs. Cookie session plus CSRF plus same-origin CSP
keeps the browser flow free of tokens in storage or URLs.

## Endpoint protection

| Endpoint | Protection |
|---|---|
| `GET /api/health`, `GET /api/v1/readiness` | Public probes |
| `POST /api/auth/login` | Public, rate limited |
| `GET /api/auth/me`, `POST /api/auth/logout` | Any authenticated session (logout requires CSRF) |
| `POST /api/predict` | Any authenticated session + CSRF |
| `POST /api/history` | Authenticated owner + CSRF |
| `POST /api/history/query` | Authenticated owner + CSRF; feature values stay out of URLs |
| `GET /api/history` | Authenticated owner (deprecated GET form retained) |
| `GET /api/cohort-analytics` | `mentor`, `placement_officer`, `admin` |
| `GET /api/mentor/students` | `mentor`, `placement_officer`, `admin`; mentor cohort-scoped |
| `GET /api/student/profile`, `PUT /api/student/profile` | Student account only; own saved profile and target role(s) |
| `GET/POST /api/students/<id>/coaching` | Student self or authorized staff; mentor is cohort-scoped |
| `PATCH /api/students/<id>/coaching/<record>` | Student self or assigned-cohort staff; goal records only |
| `GET/POST /api/students/<id>/evidence` | Student self or authorized staff; student submits evidence |
| `PATCH /api/students/<id>/evidence/<evidence-id>` | `admin`; verify/reject submitted evidence |
| `GET /api/placement-pipeline` | Staff roles; mentor sees own cohort |
| `POST /api/placement-pipeline` | `placement_officer`, `admin` |
| `GET /api/staff/audit` | `admin` |
| `GET /api/model-info` | Any authenticated session |
| `GET /api/v1/metrics` | `admin` |

Unauthenticated requests return `401` with `Authentication required.` or
`Your session has expired. Please sign in again.` Role failures return a
generic `403` that does not disclose whether data exists.

## Data scoping

- Assessments now store `user_id` and a snapshot of the user's `cohort`.
  History reads filter by the authenticated owner; a student cannot query
  another account's profile history even with identical feature values.
  Assessments created before this change have `user_id = NULL`; they remain in
  the database but are not shown to students.
- Mentor aggregates filter by the mentor's cohort. Placement officers and
  administrators see the institution-wide aggregate.
- Student profile reads and coaching writes are scoped to the account owner;
  mentors must share the student's assigned cohort. Student-visible goals are
  readable by the student, while mentor-only notes remain staff-only.
- Placement pipeline edits are limited to placement officers and admins.
- Students submit project, internship, certification, portfolio, and skill
  evidence as pending review. Only admins can change its verification status.
- Staff student-detail access and key record changes are audit-logged in the
  assessment database.
- Aggregates are suppressed entirely when fewer than
  `COHORT_MIN_GROUP_SIZE` profiles exist. The suppressed response contains no
  scores, distribution, or gaps.
- The cohort cache in the frontend is keyed by role and cohort, so switching
  accounts in one browser session cannot surface another scope's cached data.

## Rate limiting

Five failed sign-ins per IP + username within five minutes return `429` with
`Retry-After`. The counter is in-process; a multi-worker or multi-instance
deployment must also rate limit at the ingress. The client address is read
from `X-Real-IP`/`X-Forwarded-For`, so only trust those headers behind the
Nginx proxy; do not expose Flask directly.

## Frontend behaviour

- The app is login-gated: no assessment, chart, or cohort request is made
  before `/auth/me` resolves.
- Header shows the signed-in name, role, and cohort, with a sign-out action.
- The mentor workspace entry is rendered only for staff roles; the server
  independently enforces the same rule.
- `401` responses anywhere return the user to sign-in with the server's
  explanation. `403` stays on the current screen with a permission message.
- No token is written to `localStorage`, `sessionStorage`, a URL, or
  telemetry.

## Remaining identity gaps

- Not an institutional SSO/SAML/OIDC integration; accounts are local.
- No MFA, self-service password reset, email verification, or account
  recovery. The placement office administers accounts.
- No authentication audit log, impossible-travel or lockout alerting.
- No password history, rotation policy, or breach-list check.
- The local credential database is not encrypted at rest; protect the
  deployment volume and database access.
- Session revocation is per account/session, not global "sign out
  everywhere" for a user beyond password change/deactivation.

These gaps must be closed or formally accepted before institution-wide
production use; see [FRONTEND_SIGN_OFF.md](FRONTEND_SIGN_OFF.md).
