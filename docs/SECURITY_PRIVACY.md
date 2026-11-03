# Security and privacy boundary

The prototype now includes a server-enforced identity and authorization
boundary. See [AUTHENTICATION.md](AUTHENTICATION.md) for the full design.

## Implemented controls

- Local credential provider with scrypt password hashes and a minimum
  12-character password
- Opaque server-side sessions; only SHA-256 session-token digests are stored
- `HttpOnly`, `SameSite=Lax` session cookie, `Secure` by default in production
- CSRF token required on every authenticated state-changing request
- Roles: student, mentor, placement officer, administrator
- Mentor cohort scoping and institution-wide officer/admin aggregates
- Minimum-group-size suppression for cohort analytics
- Assessment ownership: history is bound to the authenticated account
- History reads use `POST /api/history/query`, keeping profile values out of
  URLs, proxy logs, and browser history
- Sign-in throttling (5 failures / 5 minutes per IP + username)
- Session revocation on logout, password change, and account deactivation
- Restricted CORS origins, request body size limit, and security response
  headers
- Validated student inputs and validated persisted prediction fields
- Generic authentication failures that do not disclose whether an account
  exists
- Configurable SQLite history and auth database locations
- Cohort-scoped coaching records, student-visible goals, mentor-only notes,
  evidence review, placement-stage controls, and a basic business access audit

## Remaining gaps before institutional production

- No institutional SSO, MFA, self-service password reset, or account recovery
- No authentication/security audit trail or security alerting; the existing
  audit table records selected product reads and writes only
- Rate limiting is per process; add ingress-level limits for multi-worker
  deployments
- The SQLite credential database is not encrypted at rest
- No data retention or deletion workflow for assessment history
- No legal-hold process; the product audit log is not a replacement for a
  security information/event management system
- No penetration test or privacy impact assessment has been recorded
- Minimum-group suppression protects aggregate views, but a mentor with a
  small assigned cohort can still infer individual readiness from their own
  mentoring relationship; this is an institutional policy matter

Before institution-wide use, replace the local provider with the approved
institutional identity provider (or formally accept local accounts), add
audit logging and retention/deletion controls, and complete a privacy and
threat-model review.
