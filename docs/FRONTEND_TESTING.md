# Frontend testing and quality automation

Phase 14 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md).

## Stack

| Layer | Tooling |
|---|---|
| Unit and component tests | Vitest 2, jsdom, Testing Library, jest-dom, user-event |
| Accessibility automation | axe-core (jsdom scan and a real-browser Chromium scan) |
| Browser tests | Playwright 1.64, Chromium desktop and Pixel 5 profiles |
| Build and bundle gates | `scripts/check-env.mjs`, `scripts/check-bundle-budget.mjs` |
| Lint and format | ESLint 9, Prettier 3 |

Browser tests mock `/api/**` with Playwright routing, so they run without the
Flask backend and without writing to the SQLite history database. Backend
contract tests remain in `backend/test_app.py`.

## Commands

```bash
cd frontend
npm ci
npm run test:e2e:install   # one-time Chromium download
npm run verify             # lint + format + unit/component/a11y + build budget
npm run test:e2e           # browser tests on desktop and mobile
npm run verify:full        # everything above
```

`.github/workflows/frontend-ci.yml` runs the same gates on Node 22 for every
change under `frontend/`: lint, format, unit/component/axe tests, environment
check, production build, bundle budget, runtime dependency audit, and
Chromium desktop/mobile tests, with failure traces uploaded for 7 days.

## Coverage map

| Requirement | Test |
|---|---|
| Sign-in, logout, session expiry | `src/App.test.jsx`, `e2e/auth.spec.js` |
| Role-aware staff workspace | `src/App.test.jsx`, `e2e/auth.spec.js` |
| CSRF header and 401 handling | `src/services/apiClient.test.js` |
| Form value conversion | `src/utils/validation.test.js` |
| Range validation and focus recovery | `src/utils/validation.test.js`, `src/App.test.jsx`, `e2e/student-flow.spec.js` |
| Score bands, deltas, probability wording | `src/utils/format.test.js`, `src/components/results.test.jsx` |
| API error normalization, timeout, cancellation | `src/services/apiClient.test.js` |
| Telemetry allow-list and PII rejection | `src/telemetry/telemetry.test.js` |
| Readiness card (calibrated and uncalibrated) | `src/components/results.test.jsx` |
| Skill-gap empty and filter states | `src/components/results.test.jsx` |
| Mentor authorization states | `src/components/results.test.jsx` |
| Tabs with roving focus and arrow keys | `src/App.test.jsx`, browser test |
| Loading, offline, failure, retry | `src/App.test.jsx`, browser test |
| Lazy chunk loading on demand | `src/App.test.jsx`, browser test (asserts the chunk request) |
| SPA deep link | browser test |
| 320 px horizontal overflow | browser test |
| Unauthenticated access to staff data | `backend/test_app.py` (403 for students, 401 without session) |
| Cohort scoping and small-group suppression | `backend/test_app.py`, `src/components/results.test.jsx` |
| Accessibility scan | axe in jsdom; axe with color contrast in Chromium |
| Pilot feedback privacy | `src/components/FeedbackWidget.test.jsx` |
| Render failure boundary | `src/components/ErrorBoundary.test.jsx` |

Current totals: **54 unit/component tests** in 8 files and **26 browser
tests** (13 scenarios × 2 device profiles). Backend authorization tests live
in `backend/test_app.py` (17 tests).

## Deliberate test design

- Both accessibility scans fail on `critical` or `serious` violations. The
  jsdom scan disables `color-contrast` (jsdom has no layout engine) and
  `region` (the skip link intentionally sits outside landmarks). The
  Chromium scan runs the full default rule set, including contrast.
- Browser tests assert the lazy chunk URL, so a regression that folds the
  chart back into the entry bundle fails a test as well as the budget.
- The test API mock returns backend-shaped envelopes, so service response
  handling is exercised rather than bypassed.

## Known gaps

- No visual snapshot or pixel-diff tests. Layout regressions are caught by
  the overflow assertion and axe only.
- No automated screen-reader run. NVDA/VoiceOver passes remain part of the
  manual accessibility protocol in [USABILITY_PILOT.md](USABILITY_PILOT.md).
- Browser tests use a mocked API. A staging smoke test against the real
  Flask service is still required before sign-off.
- No coverage threshold is enforced; tests target user-visible behaviour
  rather than line coverage.
- `npm audit` reports 6 development-only entries (including critical ones in
  `vitest`/`tinypool` that require a major upgrade), while
  `npm audit --omit=dev` is clean. CI gates on the runtime audit only. See
  [FRONTEND_SIGN_OFF.md](FRONTEND_SIGN_OFF.md).
