import { createCorrelationId, recordEvent } from '../telemetry/telemetry';
import { getSupabaseAccessToken, usesSupabaseAuth } from './supabaseClient';

const DEFAULT_BASE = '/api';
const DEFAULT_TIMEOUT_MS = 15000;

export const API_BASE = (import.meta.env?.VITE_API_BASE_URL || DEFAULT_BASE).replace(/\/+$/, '');

const unauthorizedListeners = new Set();

/** Subscribe to session expiry so the auth shell can return to the sign-in screen. */
export function onUnauthorized(handler) {
  unauthorizedListeners.add(handler);
  return () => unauthorizedListeners.delete(handler);
}

function notifyUnauthorized(message) {
  for (const handler of unauthorizedListeners) {
    try {
      handler(message);
    } catch {
      // A listener must never break the request flow.
    }
  }
}

function readCookie(name) {
  if (typeof document === 'undefined' || !document.cookie) return null;
  const prefix = `${name}=`;
  for (const part of document.cookie.split(';')) {
    const entry = part.trim();
    if (entry.startsWith(prefix)) return decodeURIComponent(entry.slice(prefix.length));
  }
  return null;
}

export class ApiError extends Error {
  constructor(message, { kind = 'server', status = 0, requestId = null } = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind; // offline | timeout | network | unauthorized | forbidden | not_found | rate_limited | server | validation
    this.status = status;
    this.requestId = requestId;
    this.correlationId = requestId || createCorrelationId();
  }
}

function classifyStatus(status) {
  if (status === 401) return 'unauthorized';
  if (status === 403) return 'forbidden';
  if (status === 404) return 'not_found';
  if (status === 408 || status === 504) return 'timeout';
  if (status === 422) return 'validation';
  if (status === 429) return 'rate_limited';
  if (status >= 500) return 'server';
  return 'validation';
}

function statusClass(status) {
  return status ? `${Math.floor(status / 100)}xx` : 'none';
}

function safeMessage(payload, fallback) {
  const message = payload && typeof payload.message === 'string' ? payload.message : null;
  if (!message) return fallback;
  // Backend validation may return an object; only render short plain strings.
  return message.replace(/\s+/g, ' ').slice(0, 240);
}

export async function request(
  path,
  { method = 'GET', body, signal, timeoutMs = DEFAULT_TIMEOUT_MS, headers = {}, responseType = 'json' } = {},
) {
  const requestId = createCorrelationId();
  const controller = typeof AbortController !== 'undefined' ? new AbortController() : null;
  let timedOut = false;
  let timer = null;

  const abortFromCaller = () => controller?.abort();
  if (signal) {
    if (signal.aborted) abortFromCaller();
    else signal.addEventListener?.('abort', abortFromCaller, { once: true });
  }

  if (controller) {
    timer = setTimeout(() => {
      timedOut = true;
      controller.abort();
    }, timeoutMs);
  }

  const unsafeMethod = !['GET', 'HEAD', 'OPTIONS'].includes(method.toUpperCase());
  const csrfToken = unsafeMethod ? readCookie('lpu_csrf') : null;
  const isFormData = typeof FormData !== 'undefined' && body instanceof FormData;

  let response;
  try {
    const accessToken = usesSupabaseAuth ? await getSupabaseAccessToken() : null;
    response = await fetch(`${API_BASE}${path}`, {
      method,
      signal: controller?.signal,
      credentials: 'include',
      headers: {
        Accept: 'application/json',
        ...(body && !isFormData ? { 'Content-Type': 'application/json' } : {}),
        ...(csrfToken ? { 'X-CSRF-Token': csrfToken } : {}),
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        'X-Request-ID': requestId,
        ...headers,
      },
      body: body ? (isFormData ? body : JSON.stringify(body)) : undefined,
    });
  } catch (error) {
    clearTimeout(timer);
    signal?.removeEventListener?.('abort', abortFromCaller);
    if (error?.name === 'AbortError') {
      if (timedOut) {
        recordEvent('api_error', { error_kind: 'timeout' });
        throw new ApiError('The service took too long to respond. Please retry.', {
          kind: 'timeout',
          requestId,
        });
      }
      throw error; // Caller-initiated cancellation: let the caller ignore it.
    }
    recordEvent('api_error', { error_kind: 'network' });
    throw new ApiError(
      typeof navigator !== 'undefined' && navigator.onLine === false
        ? 'You appear to be offline. Check your connection and retry.'
        : 'The readiness service could not be reached. Check your connection and retry.',
      { kind: 'network', requestId },
    );
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener?.('abort', abortFromCaller);
  }

  const responseRequestId = response.headers?.get?.('X-Request-ID') || requestId;

  if (response.ok && responseType === 'blob') return response.blob();

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const kind = classifyStatus(response.status);
    // Sign-in and session bootstrap handle their own 401 messaging.
    if (kind === 'unauthorized' && !path.includes('/auth/login') && !path.includes('/auth/me')) {
      notifyUnauthorized(
        payload && typeof payload.message === 'string'
          ? payload.message
          : 'Your session expired. Please sign in again.',
      );
    }
    recordEvent('assessment_failed', {
      error_kind: kind,
      status_class: statusClass(response.status),
    });
    const fallback =
      kind === 'forbidden'
        ? 'You do not have permission to view this information.'
        : kind === 'unauthorized'
          ? 'Your session has expired. Please sign in again.'
          : kind === 'not_found'
            ? 'The requested information is not available.'
            : kind === 'server'
              ? 'The readiness service is temporarily unavailable. Please retry.'
              : 'The request could not be completed. Check the entered values and retry.';
    throw new ApiError(safeMessage(payload, fallback), {
      kind,
      status: response.status,
      requestId: responseRequestId,
    });
  }

  return payload;
}

export function get(path, options = {}) {
  return request(path, { ...options, method: 'GET' });
}

export function post(path, body, options = {}) {
  return request(path, { ...options, method: 'POST', body });
}

export function download(path, options = {}) {
  return request(path, { ...options, method: 'GET', responseType: 'blob' });
}
