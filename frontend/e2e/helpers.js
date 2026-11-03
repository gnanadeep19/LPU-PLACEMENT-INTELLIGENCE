import { createRequire } from 'node:module';
import { expect } from '@playwright/test';
import {
  PASSWORD,
  cohortFixture,
  mentorUser,
  predictionFixture,
  studentUser,
} from '../src/test/fixtures.js';

const require = createRequire(import.meta.url);

export async function mockApi(page, options = {}) {
  const state = {
    user: Object.prototype.hasOwnProperty.call(options, 'user') ? options.user : studentUser,
    loginUser: options.loginUser || studentUser,
    password: options.password || PASSWORD,
    failPredict: Boolean(options.failPredict),
    sessionExpires: Boolean(options.sessionExpires),
  };

  await page.route('**/api/auth/me', (route) =>
    state.user
      ? route.fulfill({
          json: {
            status: 'success',
            data: {
              user: state.user,
              csrf_token: 'e2e-csrf',
              expires_at: new Date(Date.now() + 3_600_000).toISOString(),
              expires_in: 3600,
            },
          },
        })
      : route.fulfill({
          status: 401,
          json: { status: 'error', message: 'Authentication required.' },
        }),
  );

  await page.route('**/api/auth/login', (route) => {
    const body = route.request().postDataJSON();
    if (!body?.username || body.password !== state.password) {
      return route.fulfill({
        status: 401,
        json: { status: 'error', message: 'Invalid username or password.' },
      });
    }
    state.user = state.loginUser;
    return route.fulfill({
      json: {
        status: 'success',
        data: {
          user: state.user,
          csrf_token: 'e2e-csrf',
          expires_at: new Date(Date.now() + 3_600_000).toISOString(),
          expires_in: 3600,
        },
      },
    });
  });

  await page.route('**/api/auth/logout', (route) => {
    state.user = null;
    return route.fulfill({ json: { status: 'success', data: { signed_out: true } } });
  });

  await page.route('**/api/health', (route) => route.fulfill({ json: { status: 'ok' } }));

  await page.route('**/api/predict', (route) => {
    if (state.sessionExpires) {
      return route.fulfill({
        status: 401,
        json: { status: 'error', message: 'Your session has expired. Please sign in again.' },
      });
    }
    if (state.failPredict) {
      return route.fulfill({
        status: 500,
        json: { status: 'error', message: 'Upstream model unavailable.' },
      });
    }
    return route.fulfill({ json: { status: 'success', data: predictionFixture } });
  });

  await page.route('**/api/history**', (route) => {
    if (route.request().url().includes('/history/query')) {
      return route.fulfill({ json: { status: 'success', data: [] } });
    }
    if (route.request().method() === 'POST') {
      return route.fulfill({ status: 201, json: { status: 'success', data: { id: 1 } } });
    }
    return route.fulfill({ json: { status: 'success', data: [] } });
  });

  await page.route('**/api/cohort-analytics', (route) =>
    route.fulfill({ json: { status: 'success', data: cohortFixture } }),
  );

  return state;
}

export async function signIn(page, username = 'student.a', password = PASSWORD) {
  await page.getByLabel('Username').fill(username);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: 'Sign in' }).click();
}

export async function expectNoSeriousAxeViolations(page) {
  await page.addScriptTag({ path: require.resolve('axe-core/axe.min.js') });
  const results = await page.evaluate(async () => {
    // eslint-disable-next-line no-undef
    return axe.run(document, { rules: { region: { enabled: false } } });
  });
  const serious = results.violations.filter((violation) =>
    ['serious', 'critical'].includes(violation.impact),
  );
  expect(
    serious.map(
      (violation) => `${violation.id}: ${violation.help} (${violation.nodes.length} nodes)`,
    ),
  ).toEqual([]);
}
