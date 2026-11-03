import { expect, test } from '@playwright/test';
import { expectNoSeriousAxeViolations, mockApi } from './helpers.js';

async function waitForReadiness(page) {
  await expect(page.getByRole('img', { name: 'Readiness score 68 out of 100' })).toBeVisible();
}

test('completes the student assessment flow and switches diagnostic tabs', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');

  await expect(
    page.getByRole('heading', { name: 'Student placement readiness dashboard' }),
  ).toBeAttached();
  await waitForReadiness(page);
  await expect(page.getByText('Coding Practice', { exact: true })).toBeVisible();
  await expect(page.getByText('Model ranking signal', { exact: true })).toBeVisible();

  await page.getByRole('tab', { name: /action roadmap/i }).click();
  await expect(
    page.getByRole('heading', { name: /strengthen data structures and algorithms/i }),
  ).toBeVisible();

  await page.getByRole('tab', { name: /skill gap matrix/i }).focus();
  await page.keyboard.press('ArrowRight');
  await expect(page.getByRole('tab', { name: /action roadmap/i })).toHaveAttribute(
    'aria-selected',
    'true',
  );

  await expect(page.getByText(/placement guarantee/i)).toBeVisible();
  expect(page.url()).not.toContain('cgpa');
});

test('blocks an out-of-range profile with a specific validation message', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await waitForReadiness(page);

  const backlogs = page.getByRole('spinbutton', { name: 'Active Backlogs', exact: true });
  await backlogs.fill('12');
  await page.getByRole('button', { name: /analyze placement readiness/i }).click();

  await expect(page.getByText('Number of active backlogs must be between 0 and 10.')).toBeVisible();
  await expect(backlogs).toBeFocused();
});

test('recovers from a backend failure with a retry that keeps the form', async ({ page }) => {
  const state = await mockApi(page, { failPredict: true });
  await page.goto('/');

  await expect(page.getByText(/upstream model unavailable/i)).toBeVisible();
  await expect(page.getByRole('slider', { name: 'Academic CGPA' })).toBeVisible();

  state.failPredict = false;
  await page.getByRole('button', { name: /^retry$/i }).click();
  await waitForReadiness(page);
  await expect(page.getByText(/upstream model unavailable/i)).toHaveCount(0);
});

test('loads the explanation panel as a separate chunk on demand', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await waitForReadiness(page);

  const chunkRequest = page.waitForRequest((request) =>
    request.url().includes('InfluentialFactorsPanel'),
  );
  await page.getByRole('tab', { name: /influential factors/i }).click();

  await chunkRequest;
  await expect(
    page.getByRole('heading', { name: /global model feature importance/i }),
  ).toBeVisible();
  await expect(
    page.getByRole('table', { name: /global model feature importance/i }),
  ).toBeAttached();
});

test('serves direct deep links without a 404', async ({ page }) => {
  await mockApi(page);
  const response = await page.goto('/mentor/cohort');
  expect(response?.status()).toBe(200);
  await expect(page.getByText('LPU Placement Intelligence')).toBeVisible();
});

test('has no horizontal page overflow at a narrow phone width', async ({ page }) => {
  await mockApi(page);
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('/');
  await waitForReadiness(page);

  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(1);
});

test('passes an axe scan in a real browser', async ({ page }) => {
  await mockApi(page);
  await page.goto('/');
  await waitForReadiness(page);

  await expectNoSeriousAxeViolations(page);
});
