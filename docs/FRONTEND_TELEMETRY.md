# Frontend telemetry and privacy

Phase 16 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md).
Implementation: `frontend/src/telemetry/telemetry.js`, enforced by
`telemetry.test.js`.

## Principle

The frontend records **event shapes, not student data**. Telemetry is opt-in:
when `VITE_TELEMETRY_ENDPOINT` is unset, events stay in a 20-entry in-memory
buffer and are never transmitted.

## Events

| Event | Allowed properties | Purpose |
|---|---|---|
| `app_boot` | — | Count starts |
| `assessment_submitted` | — | Count analysis attempts |
| `assessment_succeeded` | `duration_ms` | Latency |
| `assessment_failed` | `error_kind`, `status_class` | Failure class |
| `api_error` | `error_kind`, `status_class` | Transport failures |
| `tab_viewed` | `tab` | Section usage |
| `workspace_viewed` | `workspace` | Role surface usage |
| `report_export_requested` | — | Export intent |
| `cohort_viewed` | `outcome` | Aggregate view outcome |
| `chunk_load_failed` | `chunk` | Lazy-load reliability |
| `web_vital` | `metric`, `rating` | Bucketed Core Web Vitals |
| `pilot_feedback_submitted` | `task`, `ease`, `friction` | Coded pilot feedback |
| `error_boundary_caught` | `error_type` | Render error class |

Each event carries only `event`, `props`, `route` (pathname without query or
hash), an opaque per-page `session` UUID, `build`, and `ts`. The session ID is
random per page load, is not persisted, and is never joined to a student,
profile, or account.

## What the sanitizer rejects

- Unknown event names.
- Any property not listed for that event.
- Property names matching identity or payload patterns (`name`, `email`,
  `student`, `profile`, `token`, `hash`, `feature`, `value`, `score`,
  `comment`, `payload`, and similar).
- Free-text strings. Strings must match `[a-z0-9_.:-]{1,48}`; anything with
  spaces, emails, names, or long text is dropped.
- Non-finite numbers; numbers are rounded to integers.

`telemetry.test.js` asserts that an email, a student name, a profile hash, and
a request body are removed, and that a sentence under an allow-listed key
(`task`) is dropped.

## Transport

- Only HTTPS endpoints pass the build-time environment check.
- Events use `navigator.sendBeacon` with a `fetch(..., {keepalive: true})`
  fallback.
- Failures are swallowed; telemetry can never block the UI.
- The collector is **not** part of this repository. It must implement
  access control, retention (recommended maximum 90 days), and no cross-site
  identifier joining before it is enabled.

## Web Vitals

`startWebVitals()` observes largest contentful paint and cumulative layout
shift, rates them as `good` / `needs-improvement` / `poor`, and emits
`web_vital`. Exact timings are discarded deliberately so performance data
cannot be correlated with an individual assessment. This is a coarse trend
signal, not a substitute for a field-performance dashboard.

## Error correlation

Each API request sends an `X-Request-ID` generated with
`crypto.randomUUID()`. The response header is retained, and a failed request
shows an eight-character support reference in the error banner. Render
failures are caught by `ErrorBoundary`, which records only the error type and
shows the same eight-character reference on screen.

The correlation ID is deliberately visible to the user for support, but it is
not transmitted to telemetry and contains no personal data.

## Adding an event

1. Add the event and its minimal property list to `EVENT_SCHEMAS`.
2. Add a test proving forbidden properties are dropped.
3. Add the event to the table above.
4. Confirm the collector's schema accepts it and that the property cannot
   identify a student.

## Explicitly never collected

Form values, CGPA or any other score, profile hashes, API request or response
bodies, student names, emails, roll numbers, usernames, roles, cohort names,
session or CSRF tokens, cookies, URLs with query strings, free-text feedback,
and DOM content.
