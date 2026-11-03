import { expect, test } from '@playwright/test';
import { mentorUser } from '../src/test/fixtures.js';
import { expectNoSeriousAxeViolations, mockApi, signIn } from './helpers.js';

async function waitForReadiness(page) {
  await expect(page.getByRole('img', { name: 'Readiness score 68 out of 100' })).toBeVisible();
}

test('requires sign-in before any assessment data is shown', async ({ page }) => {
  await mockApi(page, { user: null });
  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Sign in', level: 2 })).toBeVisible();
  await expect(page.getByLabel('Username')).toBeVisible();
  await expect(page.getByRole('button', { name: /analyze placement readiness/i })).toHaveCount(0);
  await expectNoSeriousAxeViolations(page);
});

test('signs in with provisioned credentials', async ({ page }) => {
  await mockApi(page, { user: null });
  await page.goto('/');
  await signIn(page);

  await waitForReadiness(page);
  await expect(page.getByText('Student A · Student')).toBeVisible();
});

test('rejects a wrong password without revealing account state', async ({ page }) => {
  await mockApi(page, { user: null });
  await page.goto('/');
  await signIn(page, 'student.a', 'wrong-password');

  await expect(page.getByRole('alert')).toHaveText('Invalid username or password.');
  await expect(page.getByRole('heading', { name: 'Sign in', level: 2 })).toBeVisible();
});

test('returns to sign-in when the server session expires', async ({ page }) => {
  await mockApi(page, { sessionExpires: true });
  await page.goto('/');

  await expect(page.getByText(/session has expired/i)).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Sign in', level: 2 })).toBeVisible();
});

test('student accounts have no mentor workspace entry', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await waitForReadiness(page);

  await expect(page.getByRole('button', { name: /mentor workspace/i })).toHaveCount(0);
});

test('mentor accounts can open the cohort-scoped workspace', async ({ page }) => {
  await mockApi(page, { user: mentorUser });
  await page.goto('/');
  await waitForReadiness(page);

  await page.getByRole('button', { name: /mentor workspace/i }).click();

  await expect(page.getByRole('heading', { name: 'Mentor overview' })).toBeVisible();
  await expect(page.getByText('Cohort CSE-A')).toBeVisible();
  await expect(page.getByText('Profiles tracked')).toBeVisible();
  await expect(page.getByText('12', { exact: true })).toBeVisible();
  await expectNoSeriousAxeViolations(page);
});
