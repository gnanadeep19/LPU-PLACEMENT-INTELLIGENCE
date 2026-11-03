import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, onUnauthorized, post, request } from './apiClient';

function jsonResponse(body, status = 200, headers = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: { get: (key) => headers[key] ?? null },
    json: async () => body,
  };
}

afterEach(() => {
  vi.unstubAllGlobals();
  document.cookie = 'lpu_csrf=; Max-Age=0; path=/';
});

describe('apiClient', () => {
  it('sends a correlation header and returns parsed JSON', async () => {
    const fetchMock = vi.fn(async () => jsonResponse({ status: 'success', data: { ok: true } }));
    vi.stubGlobal('fetch', fetchMock);

    const payload = await post('/predict', { cgpa: 8 });

    expect(payload.data).toEqual({ ok: true });
    const [url, options] = fetchMock.mock.calls[0];
    expect(url).toBe('/api/predict');
    expect(options.method).toBe('POST');
    expect(options.headers['X-Request-ID']).toBeTruthy();
    expect(options.headers['Content-Type']).toBe('application/json');
  });

  it('sends the CSRF cookie value on unsafe methods only', async () => {
    document.cookie = 'lpu_csrf=csrf-from-cookie; path=/';
    const fetchMock = vi.fn(async () => jsonResponse({ status: 'success', data: {} }));
    vi.stubGlobal('fetch', fetchMock);

    await post('/predict', { cgpa: 8 });
    await request('/history/query', { method: 'GET' });

    const postOptions = fetchMock.mock.calls[0][1];
    const getOptions = fetchMock.mock.calls[1][1];
    expect(postOptions.headers['X-CSRF-Token']).toBe('csrf-from-cookie');
    expect(postOptions.credentials).toBe('include');
    expect(getOptions.headers['X-CSRF-Token']).toBeUndefined();
  });

  it('notifies session listeners on 401 but not for sign-in failures', async () => {
    const handler = vi.fn();
    const unsubscribe = onUnauthorized(handler);
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse({ status: 'error', message: 'Your session has expired.' }, 401),
      ),
    );

    await expect(request('/predict', { method: 'POST', body: {} })).rejects.toMatchObject({
      kind: 'unauthorized',
    });
    expect(handler).toHaveBeenCalledWith('Your session has expired.');

    handler.mockClear();
    await expect(post('/auth/login', { username: 'a', password: 'b' })).rejects.toMatchObject({
      kind: 'unauthorized',
    });
    await expect(request('/auth/me')).rejects.toMatchObject({ kind: 'unauthorized' });
    expect(handler).not.toHaveBeenCalled();
    unsubscribe();
  });

  it('normalizes server errors and keeps the backend request id', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () =>
        jsonResponse({ status: 'error', message: 'Model unavailable' }, 500, {
          'X-Request-ID': 'req-123',
        }),
      ),
    );

    await expect(request('/predict', { method: 'POST', body: {} })).rejects.toMatchObject({
      name: 'ApiError',
      kind: 'server',
      status: 500,
      requestId: 'req-123',
      message: 'Model unavailable',
    });
  });

  it('maps authorization and not-found statuses to safe messages', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({}, 403)),
    );
    await expect(request('/cohort-analytics')).rejects.toMatchObject({
      kind: 'forbidden',
      message: 'You do not have permission to view this information.',
    });

    vi.stubGlobal(
      'fetch',
      vi.fn(async () => jsonResponse({}, 404)),
    );
    await expect(request('/missing')).rejects.toMatchObject({
      kind: 'not_found',
      message: 'The requested information is not available.',
    });
  });

  it('falls back to a generic message when the error body is not JSON', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        ok: false,
        status: 400,
        headers: { get: () => null },
        json: async () => {
          throw new Error('not json');
        },
      })),
    );

    await expect(request('/predict')).rejects.toBeInstanceOf(ApiError);
    await expect(request('/predict')).rejects.toMatchObject({
      kind: 'validation',
      message: 'The request could not be completed. Check the entered values and retry.',
    });
  });

  it('reports network failures separately', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch');
      }),
    );

    await expect(request('/health')).rejects.toMatchObject({
      kind: 'network',
      message: 'The readiness service could not be reached. Check your connection and retry.',
    });
  });

  it('times out a slow request', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url, options) =>
          new Promise((_resolve, reject) => {
            options.signal.addEventListener('abort', () => {
              const error = new Error('aborted');
              error.name = 'AbortError';
              reject(error);
            });
          }),
      ),
    );

    await expect(request('/health', { timeoutMs: 20 })).rejects.toMatchObject({
      kind: 'timeout',
    });
  });

  it('propagates caller cancellation instead of masking it as an error', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(
        (_url, options) =>
          new Promise((_resolve, reject) => {
            options.signal.addEventListener('abort', () => {
              const error = new Error('aborted');
              error.name = 'AbortError';
              reject(error);
            });
          }),
      ),
    );

    const controller = new AbortController();
    const promise = request('/predict', { signal: controller.signal, timeoutMs: 5000 });
    controller.abort();
    await expect(promise).rejects.toMatchObject({ name: 'AbortError' });
  });
});
