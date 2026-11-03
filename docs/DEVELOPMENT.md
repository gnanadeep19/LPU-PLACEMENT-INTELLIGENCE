# Development guide

## Local prerequisites

- Python 3.13 or a compatible supported Python version
- Node.js 22 or newer
- npm
- Docker Desktop (optional, for containerized startup)

## Option 1: Run with local runtimes

From the repository root:

### Backend

```powershell
py -3.13 -m venv backend\.venv
backend\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
backend\.venv\Scripts\python.exe backend\app.py
```

The API is available at `http://127.0.0.1:5000`.

### Frontend

In a second terminal:

```powershell
Set-Location frontend
npm ci
npm run dev
```

The frontend is available at `http://localhost:5173`.

The Vite development proxy sends `/api` requests to the backend configured by
`VITE_API_PROXY_TARGET`.

## Option 2: Run with Docker Compose

From the repository root:

```powershell
docker compose up --build
```

The same local URLs are exposed:

- Frontend: `http://localhost:5173`
- API: `http://localhost:5000`

Stop the services with:

```powershell
docker compose down
```

### Production-like container stack

The development Compose file runs Vite for fast local iteration. For a
production-like container check, use the Nginx frontend and Gunicorn backend:

```powershell
docker compose -f docker-compose.production.yml up --build
```

The production-like frontend is available at `http://localhost:8080`. It
proxies `/api/` requests to the internal backend and serves the built React
application with an unprivileged Nginx image. Backend assessment history is
stored in the named `backend-data` volume.

This stack is a deployment baseline, not a complete institutional production
deployment. TLS termination, identity, authorization, managed database,
secret-management, backups, and monitoring must be supplied by the target
platform.

## Quality checks

Run backend checks from the repository root:

```powershell
backend\.venv\Scripts\ruff.exe check backend
backend\.venv\Scripts\black.exe --check backend
backend\.venv\Scripts\python.exe -m pytest backend\test_app.py
backend\.venv\Scripts\python.exe backend\test_api.py
```

Run frontend checks from `frontend`:

```powershell
npm ci
npm run test:e2e:install   # one-time Chromium download
npm run verify              # lint, format, unit/component/a11y, build budget
npm run test:e2e            # Chromium desktop and mobile
```

`npm run verify` runs ESLint, Prettier, the Vitest suite (including axe scans),
the environment check, the production build, and the gzip bundle budget. The
Playwright suite mocks `/api/**` in the browser, so it does not need the Flask
server or the SQLite history database.

See [FRONTEND_TESTING.md](FRONTEND_TESTING.md) for coverage, and
[FRONTEND_DEPLOYMENT.md](FRONTEND_DEPLOYMENT.md) for the production build,
security headers, caching, and rollback procedure.

The Flask test-client suite is the deterministic API quality gate. The
live-server script remains a smoke test for a manually running backend.
Together, they cover legacy and versioned routes, validation, security
headers, request correlation, history persistence, aggregate privacy, and
oversized requests.

## Environment configuration

Copy `.env.example` to `.env` for local development. Do not commit `.env` or
any file containing secrets. Production values must be supplied by the
deployment environment or a secret manager.

Important settings:

| Variable | Purpose | Local default |
|---|---|---|
| `APP_ENV` | Environment name | `development` |
| `HOST` | Flask bind address | `127.0.0.1` |
| `PORT` | Flask port | `5000` |
| `FLASK_DEBUG` | Flask debug mode | `false` |
| `MODEL_PATH` | Model artifact path | `backend/placement_model.joblib` |
| `HISTORY_DATABASE_PATH` | SQLite history database path | `backend/data/assessment_history.sqlite3` |
| `AUTH_DATABASE_PATH` | SQLite accounts and sessions path | `backend/data/auth.sqlite3` |
| `SESSION_TTL_SECONDS` | Absolute session lifetime | `28800` (8 hours) |
| `AUTH_COOKIE_SECURE` | `Secure` flag on session cookies | `false` in development |
| `COHORT_MIN_GROUP_SIZE` | Minimum profiles before aggregate details show | `5` |
| `LOGIN_MAX_ATTEMPTS` | Failed sign-ins before throttling | `5` |
| `LOGIN_WINDOW_SECONDS` | Throttle window | `300` |
| `CORS_ORIGINS` | Comma-separated allowed browser origins | Local Vite origins |
| `VITE_API_PROXY_TARGET` | Vite proxy target | `http://127.0.0.1:5000` |
| `MAX_CONTENT_LENGTH` | Maximum request body size in bytes | `65536` |

Set `AUTH_COOKIE_SECURE=true` in every HTTPS deployment. The production
Compose stack keeps it `false` only because it is smoke-tested over plain
HTTP on localhost.

Frontend browser configuration lives in `frontend/.env.example`. Only
`VITE_*` variables are exposed; never place a secret behind that prefix.
`VITE_API_BASE_URL` defaults to the same-origin `/api` proxy, telemetry stays
in memory unless `VITE_TELEMETRY_ENDPOINT` is set, and
`VITE_PILOT_FEEDBACK` stays off outside a controlled pilot.

### Provisioning accounts

The application has no self-registration. Create the first accounts with:

```powershell
py -3.13 backend\manage_users.py create-user --username student.demo `
  --display-name "Demo Student" --role student --cohort CSE-2027
py -3.13 backend\manage_users.py create-user --username mentor.cse `
  --display-name "CSE Mentor" --role mentor --cohort CSE-2027
```

Passwords are prompted for and hashed. Use `list-users`, `set-password`, and
`deactivate-user` to administer accounts. See
[AUTHENTICATION.md](AUTHENTICATION.md) for roles, sessions, CSRF, and cohort
scoping.

### Calibrating readiness probabilities

The calibration workflow uses the canonical dataset and requires explicit
duplicate approval:

```powershell
py -3.13 backend\calibrate_model.py --deduplicate-exact
```

It writes `reports/model-evaluation/calibration_evaluation.md`,
`calibration_evaluation.json`, and a separate
`backend/placement_model_calibrated.joblib`. The calibrated artifact is not
activated automatically. After data-owner approval, activate it explicitly:

```powershell
$env:MODEL_PATH = "backend\placement_model_calibrated.joblib"
py -3.13 backend\app.py
```

The API reports whether the loaded artifact provides a calibrated probability.

### Validating model artifacts

Before changing `MODEL_PATH`, validate the candidate artifact and retain the
reported SHA-256 checksum:

```powershell
py -3.13 backend\model_registry.py backend\placement_model.joblib
py -3.13 backend\model_registry.py backend\placement_model_calibrated.joblib
```

See `docs/MLOPS_MODEL_LIFECYCLE.md` for promotion, rollback, and monitoring
controls.

## Security boundary

The prototype applies local credential authentication with hashed passwords,
server-side sessions, CSRF protection, role and cohort authorization,
request-size limits, restricted CORS, security response headers, validated
history snapshots, and generic authentication failures. Mentor analytics are
cohort-scoped and suppressed below the minimum group size. Institutional
SSO/MFA and audit logging are still missing; see
[AUTHENTICATION.md](AUTHENTICATION.md) and [SECURITY_PRIVACY.md](SECURITY_PRIVACY.md).
Never expose the local SQLite databases or run with debug mode in a shared
environment. Run `manage_users.py` only from a trusted administrative shell.

## Dependency updates

When changing Python dependencies, update `backend/requirements.txt` or
`requirements-dev.txt` and rerun the installation and quality checks. When
changing frontend dependencies, run `npm install` from `frontend` so
`package-lock.json` remains synchronized.
