# Frontend usability pilot

Phase 17 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md).

## Status

**Protocol ready; pilot not yet executed.** No student or mentor sessions
have been run against this build. The tables below are the instrument to use;
results must be filled in before Phase 18 sign-off can claim usability
evidence.

## Pilot scope

A controlled technical pilot, not an institutional rollout. The platform
remains a diagnostic prototype and must not be used for eligibility
decisions.

| Group | Size | Preconditions |
|---|---|---|
| Students | 5–8 | Informed consent; awareness that results are diagnostic |
| Mentors | 2–3 | Provision a local mentor account with `manage_users.py --role mentor --cohort <name>`; the server scopes analytics to that cohort |
| Accessibility reviewers | 1–2 | Keyboard-only and one screen-reader pass (NVDA or VoiceOver) |
| Product/support owners | 1–2 | Observe and own the incident/support path |

## Session protocol

- 30 minutes per participant, think-aloud, moderator does not coach.
- Record task success, time on task, and friction category. Do not record
  student profile values, names, or screens.
- Consent covers anonymous coded feedback and screen-recording of the UI only
  if approved by the privacy owner. Recording is off by default.
- Stop the session if a participant discloses distressed reliance on the
  prediction; restate that it is not an eligibility decision.

## Tasks

1. Enter a realistic profile and produce a readiness result.
2. Explain what the readiness score does and does not mean.
3. Name the top gap and the next action you would take.
4. Find progress history and compare two assessments.
5. Export or print the diagnostic report.
6. Repeat task 1 on a phone at 375 px.
7. Recover from a simulated backend failure using the retry action.

## Measures and targets

| Measure | Target | Instrument |
|---|---|---|
| Assessment completion rate | ≥ 90% | Moderator log |
| Time to first useful action | ≤ 5 minutes | Moderator log |
| Correct explanation of diagnostic limits | ≥ 80% of participants | Coded answers |
| Gap/action rated useful | ≥ 4 of 5 mean | Feedback widget rating |
| Mobile completion success | ≥ 90% | Moderator log on 375 px |
| Error recovery success | 100% of participants | Simulated failure task |
| Accessibility blockers | 0 critical, ≤ 2 minor per reviewer | Reviewer log |

## Instrumentation

Enable the coded feedback widget for pilot builds only:

```bash
VITE_PILOT_FEEDBACK=on VITE_BUILD_ID=pilot-1 npm run build
```

The widget records only a task name, a 1–5 ease rating, and a friction
category. It never accepts free text, so a participant cannot accidentally
submit names or profile values. Qualitative notes stay in the moderator's
consent-approved template, outside the application.

Telemetry adds aggregate counts (`assessment_submitted`,
`assessment_succeeded`, `assessment_failed`, `tab_viewed`,
`pilot_feedback_submitted`, `web_vital`) under the rules in
[FRONTEND_TELEMETRY.md](FRONTEND_TELEMETRY.md). With no
`VITE_TELEMETRY_ENDPOINT`, nothing leaves the browser.

## Friction log template

| ID | Task | Observation | Severity | Category | Fix owner | Status |
|---|---|---|---|---|---|---|
| P-01 | | | | | | |

Severity: blocker (task cannot be completed), major (wrong outcome or
significant confusion), minor (delay or wording issue).

## Exit criteria

- No blocker or major friction remains in the student assessment, readiness
  interpretation, gap/action, or mobile flow.
- At least one accessibility reviewer completes tasks 1–7 with a keyboard
  only.
- Friction fixes are re-tested with at least two participants.
- Results and unresolved items are attached to
  [FRONTEND_SIGN_OFF.md](FRONTEND_SIGN_OFF.md) before production approval.

## Restrictions

- No institution-wide exposure before authentication and authorization exist.
- No automated eligibility decisions based on the readiness score.
- No identity-linked data without approved privacy controls.
- Mentor sessions require a provisioned staff account; role and cohort
  enforcement is server-side.
