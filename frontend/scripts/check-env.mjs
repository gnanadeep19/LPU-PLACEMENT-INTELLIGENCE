#!/usr/bin/env node
/**
 * Phase 15 deployment guard: validate browser-exposed configuration before a
 * production build. Only VITE_* values reach the bundle, so secrets must never
 * use that prefix.
 */
const MODE = process.env.NODE_ENV || 'production';

function fail(message) {
  console.error(`Environment check failed: ${message}`);
  process.exit(1);
}

const apiBase = process.env.VITE_API_BASE_URL || '/api';
if (apiBase !== '/api' && !/^https?:\/\//.test(apiBase)) {
  fail(`VITE_API_BASE_URL must be an absolute http(s) URL or "/api" (received "${apiBase}").`);
}
// A relative base is valid behind the Nginx reverse proxy used in production.

const telemetryEndpoint = process.env.VITE_TELEMETRY_ENDPOINT;
if (telemetryEndpoint && !/^https:\/\//.test(telemetryEndpoint)) {
  fail('VITE_TELEMETRY_ENDPOINT must use https.');
}

if (process.env.VITE_PILOT_FEEDBACK === 'on' && MODE === 'production') {
  console.log('Pilot feedback widget is enabled for this build.');
}

console.log(`Environment check passed (mode=${MODE}, apiBase=${apiBase}).`);
