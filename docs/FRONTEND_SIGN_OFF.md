# Frontend production sign-off

Phase 18 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md).
Evidence captured 2026-10-29 on Windows 11, Node.js 22, npm 11, Chromium
(Playwright 1.64), Vite 5.4.21.

## Decision

**CONDITIONAL GO for a controlled technical pilot.**
**NO-GO for institution-wide production.**

The frontend build, test, accessibility, performance, and deployment
configuration gates pass. Local credential authentication with server-enforced
roles, CSRF-protected sessions, assessment ownership, and cohort-scoped staff
analytics is implemented, so provisioned mentors can use the workspace.
Institution-wide use is still blocked by the absence of institutional
SSO/MFA, an unexecuted usability pilot and staging smoke test, and the absence
of a deployed frontend error collector.

## Product gates

| Gate | Result | Evidence |
|---|---|---|
| Primary student journey is complete | PASS | Assessment → readiness → gaps → roadmap → progress → print covered by component and browser tests |
| Authentication and session UX | PASS | Login, logout, session-expiry recovery, role-aware navigation, and no tokens in storage/URLs. See [AUTHENTICATION.md](AUTHENTICATION.md). |
| Mentor and officer routes are role-protected | PASS | Server `require_auth` enforces roles on cohort analytics and scopes mentors to their own cohort. The UI hides the workspace entry for students, but authorization does not depend on it. Local accounts replace the previous demo session. |
| Readiness wording approved | PARTIAL | Calibrated probability and uncalibrated ranking signal are separated, and "Unavailable" is shown instead of a fabricated value. Institutional content approval is not recorded. |
| Local and global explanations are separated | PASS | Distinct panels and a text table for global importance; local panel states it is not causal |
| Progress and report workflows usable | PARTIAL | Progress history states are implemented; report export is still browser printing. Usability pilot not run. |

## Technical gates

| Gate | Result | Evidence |
|---|---|---|
| Lint | PASS | `npm run lint` — 0 errors, 0 warnings |
| Format | PASS | `npm run format:check` |
| Unit/component/a11y tests | PASS | 54 tests, 8 files |
| Backend auth and API tests | PASS | 17 tests in `backend/test_app.py` |
| Browser tests | PASS | 26 tests (13 scenarios × desktop/Pixel 5) |
| Accessibility scans | PASS (automated) | axe: 0 critical/serious in jsdom and in Chromium with contrast enabled. Manual screen-reader pass outstanding. |
| Mobile and desktop checks | PASS | 320 px overflow gate; a genuine 146 px overflow from a `1fr` grid track was fixed with `minmax(0, 1fr)` during this phase |
| Performance budget | PASS | Initial JS 61.6 kB gzip (baseline 157.56 kB), all JS 163.1 kB, no Vite chunk warning. See [FRONTEND_PERFORMANCE.md](FRONTEND_PERFORMANCE.md) |
| Production build | PASS | `npm run build:check`; two builds produced identical SHA-256 hashes |
| API contract tests | PASS | `py -3 -m pytest backend/test_app.py -q` → 17 passed, including CSRF, role, cohort, expiry, and ownership cases. The frontend tolerates missing calibration metadata, verified by its own tests. |
| Error and offline flows | PASS | Timeout, network, server, validation, offline banner, retry, and cancellation tests |
| Dependency and security scans | PARTIAL | `npm audit --omit=dev`: 0 vulnerabilities. Full audit reports 6 development-only entries (3 moderate, 1 high, 2 critical) in `vite`, `vitest`, `vite-node`, `tinypool`, and `@vitest/mocker`. None ship in the bundle; clearing them requires a major Vite/Vitest upgrade. |

## Operational gates

| Gate | Result | Evidence |
|---|---|---|
| Frontend errors monitored | PARTIAL | Error boundary, correlation reference, and allow-listed error events exist. No collector is deployed, so alerts are not active. |
| Deployment rollback tested | **NOT TESTED** | Docker/Nginx are unavailable in this environment; image was not built or run |
| Browser telemetry privacy-safe | PASS (design) | Allow-list, PII rejection, route stripping, HTTPS-only transport, tests. Collector retention policy still required. |
| Staging smoke test | **NOT RUN** | Requires a staging host |
| Support and incident workflows documented | PARTIAL | Support reference and rollback runbook documented; named owners are not assigned |
| Usability pilot | **NOT RUN** | Protocol ready in [USABILITY_PILOT.md](USABILITY_PILOT.md); no sessions executed |

## Blocking gaps for institutional production

1. **Institutional identity lifecycle.** The credential provider is local and
   lacks SSO/SAML/OIDC, MFA, self-service reset, and auth audit logging.
   Replace it with the approved institutional identity provider or formally
   accept the local provider before institution-wide use.
2. **Usability pilot.** No student, mentor, or accessibility-reviewer results
   are recorded. Phase 17 exit criteria are unmet.
3. **Staging deployment proof.** The Nginx configuration and container were
   not executed here. Deep-link fallback, headers, cookie flags,
   `AUTH_COOKIE_SECURE=true` under TLS, and proxy behaviour must be verified in
   staging.
4. **Telemetry collector.** A frontend telemetry backend with retention and
   access control must be approved before `VITE_TELEMETRY_ENDPOINT` is set.
5. **Manual accessibility review.** Keyboard-only and screen-reader passes
   remain outstanding.
6. **Credentials operations.** Run `manage_users.py` from a trusted shell,
   never with debug mode enabled, and protect the auth database volume.

## Non-blocking follow-ups

- Upgrade Vite (5 → current major) and Vitest (2 → current major) to clear
  the development-only dependency advisories, then re-run `npm run verify` and
  `npm run test:e2e`.
- Add visual snapshot tests for the dashboard, empty, and error states.
- Replace print-based export with a generated PDF if the institution
  requires a branded artifact.
- Self-host the two web fonts to remove the third-party font request.
- Add a staging smoke test against the real Flask API to the release
  pipeline.
- Regenerate the model artifact with the deployed scikit-learn version; the
  backend test run warned that `placement_model.joblib` was pickled with
  scikit-learn 1.9.1 and loaded with 1.9.0.

## Reproduce this evidence

```bash
py -3 -m pytest backend/test_app.py -q
cd frontend
npm ci
npm run test:e2e:install
npm run verify
npm run test:e2e
npm audit --omit=dev
```

Expected: 17 backend tests pass; frontend lint/format clean, 54 tests pass,
bundle budget passes, 26 browser tests pass, runtime audit reports 0
vulnerabilities.

## Approvals

| Role | Name | Decision | Date |
|---|---|---|---|
| Product owner | | | |
| UX/accessibility reviewer | | | |
| Security/privacy reviewer | | | |
| Backend/API owner | | | |
| Operations owner | | | |

Sign-off is not complete until every row above is filled and the six
blocking gaps are closed or explicitly waived by the privacy and product
owners.
