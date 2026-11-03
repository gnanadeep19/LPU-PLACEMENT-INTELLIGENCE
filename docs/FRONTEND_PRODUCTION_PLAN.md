# Frontend Production Development Plan

## Objective

Transform the current React/Vite dashboard into a production-ready,
accessible, responsive, explainable, and role-aware frontend for the LPU
Placement Intelligence platform.

The frontend must present the backend as a diagnostic decision-support system.
It must never imply placement guarantees, automatic eligibility decisions, or
causal conclusions from model explanations.

## Current frontend baseline

Already available:

- React 18 and Vite.
- Student competency form with presets.
- Readiness score display.
- Skill-gap matrix.
- Action roadmap.
- Local explanations and counterfactual scenarios.
- Progress history.
- Aggregate mentor overview prototype.
- Print-based report export.
- API health indicator.
- Accessible labels, skip navigation, tabs, focus states, and reduced-motion
  support.
- Production build and lint commands.

Current frontend limitations:

- Most UI is implemented in one large `App.jsx`.
- Student and mentor workflows are not separated.
- Authentication and authorization are not available.
- The default running artifact may return an uncalibrated probability.
- Charts and result sections need stronger visual hierarchy and accessibility.
- Loading, offline, timeout, empty, and retry states need improvement.
- Frontend component and browser tests are limited.
- The production bundle exceeds the recommended Vite chunk-size threshold.
- Report export is browser printing rather than a complete report workflow.
- The existing React Hook dependency warning remains.

## Frontend principles

1. Make the user journey obvious: profile → analyze → understand → improve →
   track progress.
2. Show the top actionable information first; keep advanced analytics secondary.
3. Use calibrated probability wording only when the loaded model supports it.
4. Clearly separate local student explanations from global model importance.
5. Keep mentor functionality hidden or unavailable until authorization exists.
6. Preserve keyboard, screen-reader, zoom, contrast, and reduced-motion support.
7. Never put student payloads, profile hashes, or tokens in browser logs,
   analytics events, URLs, or error reports.
8. Every feature must have loading, empty, validation, error, and retry states.
9. Prefer small typed components and tested API services over logic in views.
10. Every phase ends with measurable acceptance criteria.

## Phase 0 — Frontend discovery and UX requirements

### Goals

- Document user journeys and frontend assumptions.
- Identify student, mentor, placement-officer, and administrator workflows.
- Confirm backend response contracts and error shapes.
- Define the visual language and content terminology.

### Deliverables

- Student journey map.
- Mentor journey map.
- Information architecture.
- Page and route inventory.
- Content glossary.
- Responsive breakpoint strategy.
- Accessibility requirements.
- Frontend API contract inventory.

### Acceptance criteria

- Product owner approves the navigation model.
- Every screen has a defined user, purpose, data source, and empty state.
- Technical model terms have approved student-friendly wording.

## Phase 1 — Frontend architecture and component split

### Goals

Reduce the current monolithic `App.jsx` and create maintainable boundaries.

### Target structure

```text
frontend/src/
  app/
    App.jsx
    routes.jsx
    providers.jsx
  components/
    layout/
      AppHeader.jsx
      PageShell.jsx
      StatusIndicator.jsx
    assessment/
      StudentForm.jsx
      PresetSelector.jsx
      InputField.jsx
      AnalyzeButton.jsx
    readiness/
      ReadinessScoreCard.jsx
      ReadinessCategory.jsx
      ProbabilityNote.jsx
    diagnostics/
      SkillGapMatrix.jsx
      ActionRoadmap.jsx
      InfluentialFactors.jsx
      CounterfactualScenarios.jsx
    progress/
      ProgressHistory.jsx
      ProgressSummary.jsx
    mentor/
      MentorOverview.jsx
      CohortSummary.jsx
    feedback/
      ErrorBanner.jsx
      LoadingState.jsx
      EmptyState.jsx
  hooks/
    useHealth.js
    usePrediction.js
    useHistory.js
    useCohortAnalytics.js
  services/
    apiClient.js
    predictionService.js
    historyService.js
  state/
    assessmentStore.js
  styles/
    tokens.css
    globals.css
  test/
```

### Deliverables

- Reusable form controls.
- Reusable cards, badges, tabs, alerts, and empty states.
- API service layer with consistent error handling.
- Hooks for loading, cancellation, retry, and stale-request prevention.
- Route-level or feature-level code splitting.

### Acceptance criteria

- No feature logic is duplicated across components.
- `App.jsx` is primarily composition and routing.
- Components can be tested independently.
- API errors have one consistent representation.

## Phase 2 — Design system and visual hierarchy

### Goals

Make the product feel like a focused institutional application rather than a
prototype dashboard.

### Deliverables

- Design tokens for color, spacing, typography, radius, elevation, and motion.
- Consistent card and section hierarchy.
- Consistent success, warning, danger, and informational states.
- Light/dark theme decision.
- Button, input, tab, table, chart, modal, toast, and tooltip standards.
- Content-width and grid rules.

### Main dashboard hierarchy

1. Page title and assessment context.
2. Student profile input.
3. Primary readiness result.
4. Top three priority gaps.
5. Recommended next actions.
6. Progress and advanced explanation sections.

### Acceptance criteria

- A new student can understand what to do next without reading technical
  documentation.
- Primary action and primary result are visually dominant.
- Color is never the only way to communicate status.
- Contrast meets WCAG AA for normal text and interactive controls.

## Phase 3 — Student assessment workflow

### Goals

Improve data entry accuracy, explainability, and completion rate.

### Deliverables

- Numeric value alongside every range slider.
- Current value, target value, unit, and valid range.
- Contextual help for CGPA, technical, aptitude, communication, coding,
  projects, internships, certifications, and backlogs.
- Field-level validation and correction messages.
- Form dirty-state tracking.
- Reset form action.
- Preset replacement confirmation.
- Duplicate-submit prevention.
- Submit cancellation or stale-request protection.
- Clear assessment date and readiness-profile context.

### Form behavior

- Do not silently coerce invalid or empty values into `NaN`.
- Preserve valid user input when another field fails validation.
- Keep keyboard input and slider input synchronized.
- Announce validation errors to assistive technology.
- Show an explicit “Analyzing your profile…” state.

### Acceptance criteria

- Every field is usable by keyboard and screen reader.
- Invalid values are blocked before submission where appropriate.
- The user knows whether the displayed result matches current unsaved values.
- A failed request can be retried without losing entered data.

## Phase 4 — Readiness result experience

### Goals

Make the result understandable, trustworthy, and actionable.

### Readiness card requirements

Display:

- Readiness score from 0 to 100.
- Readiness category.
- Calibrated readiness probability when available.
- Clear fallback wording when probability is not calibrated.
- Selected readiness profile and version.
- Assessment timestamp.
- Model version.
- Short interpretation.
- Non-guarantee and human-review notice.

### Comparison requirements

- Previous score.
- Current score.
- Score change.
- Probability change where comparable.
- Strongest improvement.
- Largest remaining gap.

### Acceptance criteria

- “Confidence” is not used for uncalibrated values.
- A student understands that the result is diagnostic, not a placement
  guarantee.
- The card has a meaningful skeleton, error, and unavailable-probability state.

## Phase 5 — Skill gaps and action roadmap

### Goals

Convert model output into a practical preparation plan.

### Skill-gap card

Each gap should show:

- Skill name.
- Current value.
- Target value.
- Difference.
- Severity and priority.
- Why it matters.
- Suggested action.
- Unit and measurement method.
- Estimated effort.
- Suggested due date.
- Progress state.

### Roadmap interactions

- Mark action as not started, in progress, or completed.
- Add a target date.
- Show completed action count.
- Show progress toward target.
- Allow mentor adjustments only in authorized mentor workflows.
- Preserve recommendation provenance and model version.

### Acceptance criteria

- A student can identify the top three actions within 30 seconds.
- Recommendations are measurable rather than generic.
- Empty and all-targets-met states are useful.
- Model explanations are not presented as causal claims.

## Phase 6 — Charts and data visualization

### Required visualizations

- Current-versus-target horizontal bars.
- Skill radar chart.
- Readiness trend chart.
- Gap severity distribution.
- Cohort readiness distribution for authorized mentors.
- Improvement completion summary.

### Accessibility requirements

- Every chart has a text summary or accessible data table.
- Tooltips include labels, values, units, and target context.
- Color palettes work for color-vision differences.
- Chart legends are keyboard reachable where interactive.
- Charts have useful empty and insufficient-data states.

### Acceptance criteria

- Charts support the decision the user needs to make.
- No chart is required to understand the primary result.
- Mobile charts remain readable without clipping or horizontal overflow.

## Phase 7 — Progress history and reporting

### Goals

Make improvement visible while respecting the backend’s identity and privacy
boundaries.

### Deliverables

- Progress summary on the main student dashboard.
- Historical score and probability trend.
- Assessment comparison view.
- “What improved?” and “What remains?” summaries.
- Branded printable/PDF report.
- Report date, model version, profile version, gaps, actions, and disclaimers.
- Export loading and failure states.

### Privacy requirements

- Do not place student features in query strings after authentication is added.
- Do not place profile hashes in visible URLs or browser analytics.
- Do not export identity data unless explicitly authorized.
- Show retention and deletion information where required.

### Acceptance criteria

- A student can compare two assessments.
- A report is usable when printed or saved as PDF.
- Report content matches the visible assessment state.

## Phase 8 — Student, mentor, and placement-officer workspaces

### Goals

Stop presenting mentor analytics as an ordinary student tab.

### Student workspace

- My assessment.
- My readiness.
- My gaps.
- My roadmap.
- My progress.
- My reports.
- My privacy controls.

### Mentor workspace

- Assigned students.
- Cohort readiness.
- Common gaps.
- At-risk support queue.
- Student detail view.
- Mentor notes.
- Assigned actions.

### Placement-officer workspace

- Versioned readiness profiles.
- Deterministic eligibility criteria.
- Cohort analytics.
- Outcome comparison after verified data exists.

### Authorization behavior

- Hide routes that the user cannot access.
- Enforce authorization on the backend; frontend hiding is not security.
- Show clear unauthorized and forbidden states.
- Handle expired sessions and reauthentication.

### Acceptance criteria

- A student cannot access mentor or officer data.
- A mentor sees only assigned cohorts.
- Navigation reflects the authenticated role.
- Unauthorized API responses do not leak data.

## Phase 9 — Authentication, session, and security UX

### Goals

Integrate the approved institutional identity provider once backend identity
and RBAC are available.

### Deliverables

- Login and logout flow.
- Session expiry handling.
- Reauthentication flow.
- Loading state while identity is resolved.
- Unauthorized and forbidden pages.
- Role-aware navigation.
- Safe redirect handling.
- No tokens in local storage unless explicitly approved by the security design.

### Browser security

- Avoid sensitive data in URLs.
- Avoid logging request bodies.
- Configure secure cookie behavior if cookie sessions are used.
- Handle CSRF according to the backend session strategy.
- Do not trust client-side role claims for authorization.

### Acceptance criteria

- Session expiry is understandable and recoverable.
- Logout removes local sensitive state.
- Deep links respect authorization.
- Security and privacy review approves the browser data flow.

## Phase 10 — Accessibility and inclusive design

### Required testing

- Keyboard-only navigation.
- Screen-reader testing.
- Automated axe scans.
- 200% browser zoom.
- High-contrast mode.
- Reduced-motion mode.
- Focus restoration after dialogs and route changes.
- Touch target validation on mobile.

### Required features

- Semantic landmarks.
- Correct heading hierarchy.
- Accessible tabs and tab panels.
- Accessible form errors.
- Accessible modal and confirmation dialogs.
- Accessible charts and tables.
- Visible focus indicators.
- No keyboard traps.

### Acceptance criteria

- Critical student workflows pass WCAG 2.2 AA-oriented checks.
- Every interactive control has an accessible name.
- Error and success changes are announced appropriately.
- Focus moves predictably after navigation and submission.

## Phase 11 — Responsive and mobile experience

### Test widths

- 320px.
- 375px.
- 768px.
- 1024px.
- 1440px.

### Deliverables

- Mobile-first layout review.
- Compact header.
- Stacked form and result cards.
- Full-width critical actions on small screens.
- No clipped charts or tables.
- Better mobile navigation than a long horizontal tab strip.
- Touch-friendly controls.

### Acceptance criteria

- The complete assessment flow works on a small phone.
- Result cards remain readable without zooming.
- No horizontal page overflow except intentionally scrollable data regions.

## Phase 12 — Loading, offline, and failure-state design

### States required for every data-driven feature

- Initial loading.
- Background refresh.
- Empty.
- Validation failure.
- Unauthorized.
- Forbidden.
- Not found.
- Timeout.
- Offline.
- Server failure.
- Retry success.

### Deliverables

- Skeleton components.
- Retry actions.
- Offline banner.
- Last-updated timestamps.
- Non-blocking background refresh.
- Request cancellation.
- Error boundary for rendering failures.

### Acceptance criteria

- A temporary backend failure does not erase the student form.
- The user knows whether data is stale.
- Retry behavior is predictable and accessible.

## Phase 13 — Performance and bundle optimization

### Goals

Reduce the current large JavaScript bundle and improve perceived speed.

### Deliverables

- Lazy-load mentor analytics.
- Lazy-load charts and report features.
- Dynamic import for secondary tabs.
- Memoize expensive chart and list components.
- Prevent duplicate health and analytics requests.
- Avoid unnecessary full-dashboard rerenders.
- Image and icon review.
- Performance budget in CI.

### Targets

- No Vite chunk-size warning without an approved exception.
- Fast first contentful render on the target network.
- Responsive input interaction while analysis is running.
- No unnecessary API request on every tab switch.

## Phase 14 — Frontend testing and quality automation

### Test layers

#### Unit tests

- Form value conversion.
- Validation.
- Category and status rendering.
- API error normalization.
- Score and delta calculations.

#### Component tests

- Student form.
- Readiness card.
- Skill-gap cards.
- Roadmap interactions.
- Tabs.
- History states.
- Mentor authorization states.

#### Browser tests

- Complete student assessment flow.
- Invalid input flow.
- Backend offline flow.
- History and progress flow.
- Report export flow.
- Keyboard navigation.
- Authenticated role routing when enabled.

#### Visual tests

- Desktop dashboard.
- Mobile dashboard.
- Loading states.
- Error states.
- Empty states.
- Print layout.

### CI gates

- ESLint.
- Prettier.
- Unit/component tests.
- Browser tests.
- Accessibility scans.
- Production build.
- Bundle-size budget.
- Dependency audit.

## Phase 15 — API integration and contract safety

### Deliverables

- Typed API response models.
- Central API client.
- Request ID propagation.
- Versioned endpoint configuration.
- Contract tests against `/api/v1`.
- Backward-compatibility policy.
- Safe handling of missing optional fields such as calibration metadata.

### Acceptance criteria

- Frontend does not assume calibrated probability is always present.
- API validation messages render safely.
- Schema changes fail tests before deployment.
- API base URL is configurable by environment.

## Phase 16 — Deployment and release engineering

### Deliverables

- Production frontend build.
- Nginx or managed static hosting configuration.
- SPA fallback routing.
- API reverse proxy configuration.
- HTTPS-only deployment.
- Cache headers for immutable assets.
- No source maps exposed unless approved.
- Environment-specific configuration.
- Staging and production build checks.

### Acceptance criteria

- Direct navigation to every frontend route works.
- Refreshing a deep link does not return 404.
- API proxy works in staging.
- Build artifacts are reproducible.
- Deployment can be rolled back to the previous frontend version.

## Phase 17 — Frontend observability and privacy

### Safe telemetry

Allowed:

- Route performance.
- API status class.
- Request latency.
- Anonymous feature usage counts.
- Frontend error type and correlation ID.

Not allowed:

- Student form values.
- Profile hashes.
- Full API responses.
- Tokens.
- Names, emails, student IDs, or credentials.

### Deliverables

- Frontend error boundary.
- Centralized redacted error reporting.
- Correlation ID display for support.
- Route and API performance dashboards.
- Alerting for frontend error spikes and failed deployments.

## Phase 18 — Usability pilot and feedback

### Pilot groups

- Small student group.
- Small mentor group after authorization is available.
- Accessibility reviewers.
- Product and support owners.

### Measures

- Assessment completion rate.
- Time to first useful action.
- Understanding of probability and limitations.
- Gap and recommendation usefulness.
- Accessibility issues.
- Mobile completion success.
- Error recovery success.

### Restrictions

- No institution-wide exposure before authentication and authorization.
- No automated eligibility decisions.
- No real identity-linked data without approved privacy controls.

## Phase 19 — Frontend production sign-off

### Product gates

- Primary student journey is complete.
- Mentor and officer routes are role-protected.
- Readiness wording is approved.
- Local and global explanations are separated.
- Progress and report workflows are usable.

### Technical gates

- Component and browser tests pass.
- Accessibility scans pass.
- Mobile and desktop checks pass.
- Performance budget passes.
- Production build passes.
- API contract tests pass.
- Error and offline flows pass.
- Dependency and security scans pass.

### Operational gates

- Frontend errors are monitored.
- Deployment rollback is tested.
- Browser telemetry is privacy-safe.
- Staging smoke test passes.
- Support and incident workflows are documented.

### Approval gates

- Product owner.
- UX/accessibility reviewer.
- Security/privacy reviewer.
- Backend/API owner.
- Operations owner.

## Recommended implementation order

1. Component architecture and API service layer.
2. Readiness-card and dashboard hierarchy redesign.
3. Assessment form and validation improvements.
4. Skill-gap and roadmap interaction improvements.
5. Progress history and report redesign.
6. Student/mentor workspace separation.
7. Authentication and role-aware routing.
8. Accessibility automation and browser tests.
9. Mobile and performance optimization.
10. Deployment, telemetry, pilot, and final sign-off.

## Final frontend status

Phases 13–18 are implemented and evidenced in
[FRONTEND_SIGN_OFF.md](FRONTEND_SIGN_OFF.md): production chunking and bundle
budgets, automated component/accessibility/browser tests, hardened deployment
configuration, privacy-safe telemetry, a pilot protocol, and a role-aware
authentication shell backed by local credentials, sessions, CSRF, and
cohort-scoped authorization. Institutional SSO, the usability pilot, staging
deployment proof, and a deployed telemetry collector remain before
institution-wide release.
