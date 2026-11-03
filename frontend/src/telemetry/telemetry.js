/**
 * Privacy-safe frontend telemetry.
 *
 * Rules enforced here (see docs/FRONTEND_TELEMETRY.md):
 * - Only allow-listed event names are recorded.
 * - Only allow-listed, non-identifying property keys and primitive values pass.
 * - Free-text, names, emails, student IDs, profile values, tokens, scores and
 *   API payloads are rejected by the sanitizer.
 * - Nothing is sent unless VITE_TELEMETRY_ENDPOINT is configured.
 */

const EVENT_SCHEMAS = Object.freeze({
  app_boot: [],
  assessment_submitted: [],
  assessment_succeeded: ['duration_ms'],
  assessment_failed: ['error_kind', 'status_class'],
  api_error: ['error_kind', 'status_class'],
  tab_viewed: ['tab'],
  workspace_viewed: ['workspace'],
  report_export_requested: [],
  cohort_viewed: ['outcome'],
  chunk_load_failed: ['chunk'],
  web_vital: ['metric', 'rating'],
  pilot_feedback_submitted: ['task', 'ease', 'friction'],
  error_boundary_caught: ['error_type'],
});

const BLOCKED_KEY_PATTERN =
  /(name|email|phone|student|profile|token|password|secret|hash|feature|value|score|comment|feedback|answer|identity|input|payload)/i;
const SAFE_STRING_PATTERN = /^[a-z0-9_.:-]{1,48}$/i;

const buffer = [];
const MAX_BUFFER = 20;
let sink = null;
let sessionId = createId();
let routePath = '/';

export function createId() {
  try {
    if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
      return crypto.randomUUID();
    }
  } catch {
    // Fall through to a non-cryptographic identifier.
  }
  return `anon-${Math.random().toString(36).slice(2, 10)}`;
}

export function getSessionId() {
  return sessionId;
}

export function setTelemetrySink(nextSink) {
  sink = nextSink;
}

export function setTelemetrySession(id) {
  sessionId = id;
}

export function sanitizeProps(event, props = {}) {
  const allowed = EVENT_SCHEMAS[event];
  if (!allowed) return null;

  const clean = {};
  for (const key of allowed) {
    if (!Object.prototype.hasOwnProperty.call(props, key)) continue;
    if (BLOCKED_KEY_PATTERN.test(key)) continue;
    const value = props[key];
    if (typeof value === 'number') {
      clean[key] = Number.isFinite(value) ? Math.round(value) : 0;
    } else if (typeof value === 'boolean') {
      clean[key] = value;
    } else if (typeof value === 'string' && SAFE_STRING_PATTERN.test(value)) {
      clean[key] = value;
    }
  }
  return clean;
}

function telemetryEnabled() {
  try {
    return Boolean(import.meta.env?.VITE_TELEMETRY_ENDPOINT);
  } catch {
    return false;
  }
}

function transport(event) {
  const endpoint = import.meta.env?.VITE_TELEMETRY_ENDPOINT;
  if (!endpoint) return;
  const body = JSON.stringify(event);
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const sent = navigator.sendBeacon(endpoint, new Blob([body], { type: 'application/json' }));
      if (sent) return;
    }
    fetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body,
      keepalive: true,
    }).catch(() => {});
  } catch {
    // Telemetry must never break the product.
  }
}

export function recordEvent(name, props = {}) {
  const clean = sanitizeProps(name, props);
  if (clean === null) return null;

  const event = {
    event: name,
    props: clean,
    route: routePath,
    session: sessionId,
    build: import.meta.env?.VITE_BUILD_ID || 'dev',
    ts: Date.now(),
  };

  buffer.push(event);
  if (buffer.length > MAX_BUFFER) buffer.shift();

  if (typeof sink === 'function') {
    try {
      sink(event);
    } catch {
      // Never let a sink failure affect the UI.
    }
  }

  if (telemetryEnabled()) transport(event);
  return event;
}

export function getTelemetryBuffer() {
  return [...buffer];
}

export function clearTelemetryBuffer() {
  buffer.length = 0;
}

export function setTelemetryRoute(pathname) {
  if (typeof pathname !== 'string' || !pathname) return;
  // Store the path only: query strings can carry student data.
  routePath = pathname.split('?')[0].split('#')[0].slice(0, 80);
}

/** Support-facing correlation ID for a failed request or render. */
export function createCorrelationId() {
  return createId();
}

export function reportFrontendError(error, context = {}) {
  const errorType =
    error && typeof error.name === 'string' && error.name
      ? error.name
      : context.errorType || 'Error';
  return recordEvent('error_boundary_caught', {
    error_type: errorType.replace(/[^a-z0-9_]/gi, '').slice(0, 32) || 'Error',
  });
}

/**
 * Collect coarse Web Vitals observations. Values are bucketed, never exact
 * timings, so they cannot be joined to an individual assessment.
 */
export function startWebVitals({ observe } = {}) {
  if (typeof window === 'undefined' || typeof PerformanceObserver === 'undefined') {
    return () => {};
  }
  const observerFactory = observe || ((callback) => new PerformanceObserver(callback));

  const rate = (metric, value) => {
    let rating = 'poor';
    if (metric === 'CLS')
      rating = value < 0.1 ? 'good' : value < 0.25 ? 'needs-improvement' : 'poor';
    if (metric === 'LCP')
      rating = value < 2500 ? 'good' : value < 4000 ? 'needs-improvement' : 'poor';
    if (metric === 'INP')
      rating = value < 200 ? 'good' : value < 500 ? 'needs-improvement' : 'poor';
    recordEvent('web_vital', { metric, rating });
  };

  const observers = [];
  try {
    observers.push(
      observerFactory((list) => {
        const entries = list.getEntries();
        const last = entries[entries.length - 1];
        if (last) rate('LCP', last.startTime);
      }),
    );
    observers[0].observe({ type: 'largest-contentful-paint', buffered: true });
  } catch {
    // Unsupported observer type.
  }

  try {
    let cls = 0;
    const clsObserver = observerFactory((list) => {
      for (const entry of list.getEntries()) {
        if (!entry.hadRecentInput) cls += entry.value;
      }
      rate('CLS', cls);
    });
    clsObserver.observe({ type: 'layout-shift', buffered: true });
    observers.push(clsObserver);
  } catch {
    // Unsupported observer type.
  }

  return () => {
    for (const observer of observers) {
      try {
        observer.disconnect();
      } catch {
        // Ignore disconnect failures.
      }
    }
  };
}
