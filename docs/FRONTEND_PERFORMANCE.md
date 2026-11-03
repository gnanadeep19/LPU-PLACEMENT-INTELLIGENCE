# Frontend performance and bundle optimisation

Phase 13 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md).
Measurements were taken on 2026-10-29 with Node.js 22, Vite 5.4.21, and
`vite build` (gzip level 9 reported by the budget script).

## Baseline

Before this phase the entire dashboard shipped as one chunk:

| Asset | Raw | gzip |
|---|---|---|
| `index-*.js` (application + React + Recharts + icons) | 547.10 kB | 157.56 kB |

Vite emitted its 500 kB chunk-size warning, and any chart dependency was
parsed before the student could fill in the form.

## Changes

1. `App.jsx` was reduced to composition, telemetry calls, and request
   orchestration. Panels live in `src/components/` and are memoised, so
   typing in the form no longer re-renders gap, roadmap, and history panels.
2. The explanation panel, which owns `recharts`, is loaded with
   `React.lazy`/`Suspense`. The chart dependency ships in its own `charts`
   chunk and is fetched only when the student opens "Influential Factors".
3. The mentor overview is lazy loaded and its cohort request is cached for
   60 seconds with in-flight de-duplication.
4. `vite.config.js` splits vendor code into `react-vendor` and `icons`
   chunks, disables production source maps, and keeps the default
   chunk-size warning enabled.
5. `useAssessment` cancels the previous prediction request, ignores stale
   responses, and keeps a successful result when the background history save
   fails. The app no longer fires two competing analyses on mount.
6. `useApiHealth` coalesces concurrent health checks and replaces the
   polling-style status text with a single boot-time check plus explicit
   retry.
7. The global feature-importance chart is paired with a visually hidden data
   table so the chart is never required to read the result.

## Result

| Asset | gzip | Loaded |
|---|---|---|
| `index-*.js` (app, including the sign-in shell) | 13.6 kB | initial |
| `react-vendor-*.js` | 44.3 kB | initial |
| `icons-*.js` | 3.6 kB | initial |
| `index-*.css` | 5.1 kB | initial |
| **Initial JavaScript payload** | **61.6 kB** | initial |
| `charts-*.js` | 98.9 kB | on demand |
| `InfluentialFactorsPanel-*.js` | 1.4 kB | on demand |
| `MentorOverview-*.js` | 1.3 kB | on demand |
| **All JavaScript** | **163.1 kB** | total |

The initial JavaScript payload dropped from 157.56 kB to 61.6 kB gzip
(about 61% less), including the authentication shell. Vite no longer emits a
chunk-size warning.

## Budget gate

`npm run check:budget` runs `scripts/check-bundle-budget.mjs` after a build:

| Metric | Budget |
|---|---|
| Initial payload (entry + react-vendor + icons) | 190 kB gzip |
| Any single chunk | 180 kB gzip |
| All JavaScript | 360 kB gzip |
| Published source maps | zero |

The check also fails when `dist/assets` is missing, has no JavaScript, or
contains a `.map` file. `npm run build:check` chains the environment check,
production build, and budget gate, and is what the production Docker image
runs.

## Request behaviour

- App boot resolves the session before rendering the dashboard, then performs
  one health check and one assessment for the default profile. React
  StrictMode may abort a duplicate request in development; production performs
  a single request per authenticated mount.
- Switching diagnostic tabs performs no API calls. Progress history comes
  from the last assessment; cohort analytics are fetched once per minute at
  most.
- Form inputs and presets stay interactive while an analysis is running; only
  the submit control is disabled to prevent duplicate submissions. If the
  profile changes after a result, the dashboard states that the displayed
  result does not include those edits.
- Prediction requests time out after 30 seconds; health checks after 8
  seconds; history reads after 10 seconds. A slow request surfaces a
  retryable timeout error instead of an indefinite skeleton.

## Known limitations

- Fonts are still requested from Google Fonts, so first paint can depend on
  that request. Self-hosting the two families remains an option if the
  deployment network blocks Google Fonts.
- The `charts` chunk is 101 kB gzip. It is only fetched on demand, but the
  chart is the largest remaining unit. Replacing Recharts with a smaller
  chart renderer is a future option, not a requirement of this phase.
- No throttled-network Lighthouse or WebPageTest run has been recorded yet.
  The numbers above are bundle measurements; field Core Web Vitals require
  the telemetry endpoint described in [FRONTEND_TELEMETRY.md](FRONTEND_TELEMETRY.md).
