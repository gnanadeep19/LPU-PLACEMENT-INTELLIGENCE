# Deployment Baseline

## Local development

Use `docker compose up --build` for the development stack. It exposes Vite on
port 5173 and the API on port 5000. The backend health check gates frontend
startup, and assessment history is persisted in the `backend-data` named
volume.

## Production-like container validation

Use:

```powershell
docker compose -f docker-compose.production.yml up --build
```

The stack uses:

- Gunicorn instead of Flask's development server.
- Two Gunicorn workers and four threads per worker.
- A non-root backend container user.
- An unprivileged Nginx frontend container.
- Nginx SPA fallback routing.
- Nginx `/api/` reverse proxy routing.
- Readiness-gated frontend startup.
- A named volume for the prototype SQLite history database.

## Required platform controls before institutional deployment

The Compose stack does not provide production identity or tenancy. Before a
real rollout, add:

- TLS at the ingress or managed load balancer.
- OIDC or institutional identity-provider integration.
- Role-based authorization for students, mentors, and placement officers.
- A managed database with encryption, backups, retention, and deletion controls.
- Secret management and key rotation.
- Container image scanning and signed image promotion.
- Centralized logs, metrics, traces, and alerting.
- Autoscaling and a tested disaster-recovery procedure.
- Network policies that keep the backend private.

Do not expose the prototype SQLite volume or the backend port directly to the
public internet.
