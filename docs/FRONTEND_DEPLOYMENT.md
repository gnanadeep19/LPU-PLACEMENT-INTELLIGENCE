# Frontend deployment hardening

Phase 15 of the [frontend production plan](FRONTEND_PRODUCTION_PLAN.md). This
document covers the static browser bundle. TLS termination, identity, and
secret management remain platform responsibilities.

## Build pipeline

`npm run build:check` is the required production build command. It runs:

1. `scripts/check-env.mjs` — validates browser-visible configuration.
2. `vite build` — production bundle, no source maps, vendor and lazy chunks.
3. `scripts/check-bundle-budget.mjs` — enforces the performance budget and
   fails if any `.map` file was published.

`frontend/Dockerfile.production` runs exactly this command, then copies only
`dist` into an unprivileged Nginx image.

Verified locally on 2026-10-29: two consecutive builds produced identical
SHA-256 hashes for every file in `dist/`, so the bundle is reproducible for a
fixed dependency lockfile and toolchain.

## Environment configuration

Only `VITE_*` variables reach the browser. Never place a secret behind that
prefix.

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `/api` | Absolute API origin, or the same-origin `/api` proxy path |
| `VITE_TELEMETRY_ENDPOINT` | unset | HTTPS collector URL; telemetry stays in memory when unset |
| `VITE_PILOT_FEEDBACK` | `off` | Shows the coded pilot feedback widget when `on` |
| `VITE_BUILD_ID` | `dev` | Build label attached to telemetry events |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:5000` | Development proxy target only |

`check-env.mjs` rejects a relative or non-HTTP API base, a non-HTTPS
telemetry endpoint, and missing required values. The Dockerfile accepts these
as build arguments with safe defaults.

Authentication is configured on the backend, not the browser bundle. The
production deployment must set `AUTH_COOKIE_SECURE=true` behind TLS, mount a
persistent `AUTH_DATABASE_PATH` volume, and provision accounts with
`backend/manage_users.py`. The local Compose stack keeps the cookie flag
`false` only because it is smoke-tested over plain HTTP; see
[AUTHENTICATION.md](AUTHENTICATION.md).

## Nginx configuration

`frontend/nginx.conf` plus `frontend/nginx-security-headers.conf` provide:

| Control | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `no-referrer` |
| `Permissions-Policy` | geolocation, microphone, camera, payment, usb disabled |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-origin` |
| Content Security Policy | `default-src 'self'`, no inline scripts, fonts limited to Google Fonts, `connect-src 'self'`, `frame-ancestors 'none'` |
| `server_tokens` | `off` |
| Request body limit | 64 kB |
| Compression | gzip for text, CSS, JSON, JavaScript, SVG |

CSP note: `connect-src 'self'` covers the `/api` proxy. If
`VITE_TELEMETRY_ENDPOINT` points at a different origin, that exact origin must
be added to `connect-src`, otherwise the browser blocks telemetry.

### Caching

| Path | Header | Reason |
|---|---|---|
| `/assets/*` | `Cache-Control: public, max-age=31536000, immutable` | Content-hashed filenames |
| `/index.html` | `Cache-Control: no-store` | New deploys must be picked up immediately |
| `/api/*` | proxied, no static cache | Dynamic responses |
| `/healthz` | plain `ok`, access log off | Container health probe |

Nginx does not merge inherited `add_header` directives once a location
declares one, so the security header include is repeated in the asset and
index locations.

### Routing

`try_files $uri $uri/ /index.html` serves the SPA shell for deep links.
`/api/` is matched first, so an unknown API path returns the backend's JSON
404 instead of HTML. The Docker image healthcheck probes `/healthz` every
30 seconds.

## Verification checklist

Run before promoting a build:

```bash
cd frontend
npm ci
npm run verify          # lint, format, unit/component/a11y, env, build, budget
npm run test:e2e        # Chromium desktop and mobile
npm audit --omit=dev    # runtime dependency audit
```

Then, on the target host:

1. `GET /healthz` returns `200 ok`.
2. `GET /` returns the shell with the expected security headers.
3. `GET /assets/<hashed>.js` returns `immutable` cache headers.
4. Deep links such as `/mentor/cohort` return the shell, not a 404.
5. `GET /api/v1/health` succeeds through the proxy.
6. Sign-in succeeds, the session cookie is `HttpOnly`/`SameSite=Lax` (and
   `Secure` under TLS), and an unauthenticated `/api/predict` returns 401.
7. A stale `index.html` is not served after a deploy (hard refresh once).

## Rollback

The bundle is immutable per deploy: keep the previous image tag or `dist`
directory. To roll back, redeploy the previous image and keep
`Cache-Control: no-store` on `index.html`. Assets from both versions may be
cached, but the new shell references only its own hashed files, so no
cache-busting step is required.

## Not verified in this environment

Docker and Nginx are not installed on the development machine, so the image
was not built and the configuration was not syntax-checked by
`nginx -t` here. The configuration has been reviewed rule by rule, but a
staging deploy must run the checklist above before production promotion.
