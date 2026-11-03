# Production release criteria

The platform may be released to institutional users only after all applicable gates below are satisfied and evidence is attached to the release record.

## Product and data

- [ ] Prediction target and label construction are documented.
- [ ] Dataset provenance, license, consent, and retention are documented.
- [ ] Data validation passes for required columns, ranges, missing values, duplicates, and unexpected categories.
- [ ] Leakage audit is complete.
- [ ] Synthetic, curated, and verified outcome data are clearly separated.

## Machine learning

- [ ] Benchmarking uses the same canonical dataset pipeline as production training.
- [ ] Repeated stratified cross-validation or an equivalent justified evaluation is complete.
- [ ] Baselines are included.
- [ ] Confidence intervals or uncertainty estimates are reported.
- [ ] Calibration is evaluated and acceptable.
- [ ] Subgroup performance and fairness review are complete.
- [ ] Model card records data, features, metrics, limitations, and intended use.
- [ ] Model artifact is versioned, checksummed, and rollback-ready.
- [ ] Student-specific explanations are implemented and validated.

## Backend and data protection

- [ ] API is versioned and documented with OpenAPI.
- [ ] Authentication and role-based authorization are enabled.
- [ ] Student data access is restricted and audited.
- [ ] Input validation, rate limiting, secure headers, and safe error handling are enabled.
- [ ] Database migrations, backups, and restoration have been tested.
- [ ] Secrets are supplied through the deployment environment, not source control.

## Frontend

- [ ] Student and mentor workflows are complete.
- [ ] Readiness probability is not labelled as uncalibrated confidence.
- [ ] Global and local explanations are clearly separated.
- [ ] Loading, empty, validation, and API failure states are covered.
- [ ] Accessibility checks pass for critical workflows.
- [ ] Production build and performance checks pass.

## Operations

- [ ] CI runs formatting, linting, type checks, tests, security scans, and builds.
- [ ] Health checks, logs, metrics, and alerts are configured.
- [ ] Model drift and prediction distribution monitoring are configured.
- [ ] Incident response and rollback runbooks exist.
- [ ] Staging smoke tests pass.
- [ ] Pilot feedback and outcome validation are reviewed.

## Approval

Required approvals:

1. Product owner
2. Data owner or placement office
3. ML reviewer
4. Security/privacy reviewer
5. Operations owner

## Pilot gate

Before any controlled pilot, complete the [pilot rollout plan](./PILOT_ROLLOUT_PLAN.md),
[pilot readiness checklist](./PILOT_READINESS_CHECKLIST.md), and
[feedback and incident workflow](./PILOT_FEEDBACK_WORKFLOW.md). A pilot does
not waive the authentication, authorization, provenance, label-ownership, or
verified-outcome requirements for institutional production release.
