# Operations and Observability Baseline

The API records process-local operational metrics without logging request
payloads or student profiles.

## Metrics endpoint

The internal metrics endpoint is:

```text
GET /api/v1/metrics
```

It reports:

- Process uptime.
- Request count.
- Average request duration.
- HTTP status classes.
- Endpoint activity by method and path.

The counters are intentionally in-memory and reset when a worker restarts.
Gunicorn workers therefore have independent counters. A production deployment
must export these values to a central metrics system rather than treating this
endpoint as a durable time series.

Protect this endpoint at the ingress or service network boundary before
institutional deployment. It must not be exposed publicly without
authentication.

## Recommended dashboards

Track:

- Readiness and liveness probe success rate.
- 5xx rate and prediction-validation 4xx rate.
- Prediction latency percentiles.
- API request volume by route.
- Loaded model version and artifact checksum.
- Container restarts and resource saturation.
- Database write failures and storage capacity.

## Recommended alerts

- Readiness probe unavailable for two consecutive intervals.
- Sustained 5xx responses.
- Elevated prediction latency.
- Model artifact checksum or version differs from the approved release.
- History database unavailable or approaching storage limits.
- Sudden increase in rejected payloads.

Request logs contain method, path, status, duration, and correlation ID only.
Do not add request bodies, query-string student features, profile hashes, or
prediction payloads to logs or metrics.
