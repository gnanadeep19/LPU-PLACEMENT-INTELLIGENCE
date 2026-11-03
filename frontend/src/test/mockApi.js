import { vi } from 'vitest';
import {
  PASSWORD,
  cohortFixture,
  mentorUser,
  officerUser,
  predictionFixture,
  studentUser,
} from './fixtures';

export { PASSWORD, mentorUser, officerUser, studentUser };

export function deferred() {
  let resolve;
  const promise = new Promise((next) => {
    resolve = next;
  });
  return { promise, resolve };
}

function response(body, status = 200, headers = {}) {
  return {
    ok: status >= 200 && status < 300,
    status,
    headers: {
      get: (key) => headers[key] ?? null,
    },
    json: async () => body,
  };
}

export function installMockApi(options = {}) {
  const state = {
    user: Object.prototype.hasOwnProperty.call(options, 'user') ? options.user : studentUser,
    loginUser: options.loginUser || studentUser,
    password: options.password || PASSWORD,
    failPredict: Boolean(options.failPredict),
    unauthorizedPredict: Boolean(options.unauthorizedPredict),
    failHistory: Boolean(options.failHistory),
    holdPredict: options.holdPredict || null,
    history: options.history || [],
    prediction: options.prediction || predictionFixture,
    cohort: options.cohort || cohortFixture,
    predictCalls: 0,
    historyReads: 0,
    saves: 0,
    cohortCalls: 0,
    loginCalls: 0,
    logoutCalls: 0,
  };

  global.fetch = vi.fn(async (url, requestOptions = {}) => {
    const target = String(url);
    const method = requestOptions.method || 'GET';
    const body = requestOptions.body ? JSON.parse(requestOptions.body) : null;

    if (target.includes('/auth/me')) {
      if (!state.user) {
        return response({ status: 'error', message: 'Authentication required.' }, 401);
      }
      return response({
        status: 'success',
        data: {
          user: state.user,
          csrf_token: 'test-csrf',
          expires_at: new Date(Date.now() + 3_600_000).toISOString(),
          expires_in: 3600,
        },
      });
    }

    if (target.includes('/auth/login')) {
      state.loginCalls += 1;
      if (!body?.username || body.password !== state.password) {
        return response({ status: 'error', message: 'Invalid username or password.' }, 401);
      }
      state.user = state.loginUser;
      return response({
        status: 'success',
        data: {
          user: state.user,
          csrf_token: 'test-csrf',
          expires_at: new Date(Date.now() + 3_600_000).toISOString(),
          expires_in: 3600,
        },
      });
    }

    if (target.includes('/auth/logout')) {
      state.logoutCalls += 1;
      state.user = null;
      return response({ status: 'success', data: { signed_out: true } });
    }

    if (target.includes('/health')) {
      return response({ status: 'ok' });
    }

    if (target.includes('/predict')) {
      state.predictCalls += 1;
      if (state.unauthorizedPredict) {
        return response(
          { status: 'error', message: 'Your session has expired. Please sign in again.' },
          401,
        );
      }
      if (state.holdPredict) {
        await state.holdPredict.promise;
      }
      if (state.failPredict) {
        return response({ status: 'error', message: 'Upstream model unavailable.' }, 500);
      }
      return response({ status: 'success', data: state.prediction });
    }

    if (target.includes('/history/query')) {
      state.historyReads += 1;
      return response({ status: 'success', data: state.history });
    }

    if (target.includes('/history')) {
      if (method === 'POST') {
        state.saves += 1;
        if (state.failHistory) {
          return response({ status: 'error', message: 'Unable to save assessment history.' }, 500);
        }
        return response({ status: 'success', data: { id: 1 } }, 201);
      }
      state.historyReads += 1;
      return response({ status: 'success', data: state.history });
    }

    if (target.includes('/cohort-analytics')) {
      state.cohortCalls += 1;
      return response({ status: 'success', data: state.cohort });
    }

    return response({ status: 'error', message: 'Endpoint not found' }, 404);
  });

  return state;
}
