import React from 'react';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import axe from 'axe-core';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';
import { PASSWORD, deferred, installMockApi, mentorUser } from './test/mockApi';

function renderApp() {
  return render(<App />);
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('authentication', () => {
  it('shows the sign-in screen when no session exists', async () => {
    installMockApi({ user: null });
    renderApp();

    expect(await screen.findByRole('heading', { name: 'Sign in', level: 2 })).toBeInTheDocument();
    expect(screen.getByLabelText('Username')).toBeInTheDocument();
    expect(screen.queryByText(/session has expired/i)).not.toBeInTheDocument();
    expect(
      screen.queryByRole('button', { name: /analyze placement readiness/i }),
    ).not.toBeInTheDocument();
  });

  it('signs in and reaches the student dashboard', async () => {
    installMockApi({ user: null });
    const user = userEvent.setup();
    renderApp();

    await user.type(await screen.findByLabelText('Username'), 'student.a');
    await user.type(screen.getByLabelText('Password'), PASSWORD);
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(
      await screen.findByRole('img', { name: 'Readiness score 68 out of 100' }),
    ).toBeInTheDocument();
    expect(screen.getByText(/Student A · Student/)).toBeInTheDocument();
  });

  it('rejects invalid credentials without revealing account details', async () => {
    const api = installMockApi({ user: null });
    const user = userEvent.setup();
    renderApp();

    await user.type(await screen.findByLabelText('Username'), 'student.a');
    await user.type(screen.getByLabelText('Password'), 'wrong-password');
    await user.click(screen.getByRole('button', { name: 'Sign in' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Invalid username or password.');
    expect(api.loginCalls).toBe(1);
    expect(
      screen.queryByRole('button', { name: /analyze placement readiness/i }),
    ).not.toBeInTheDocument();
  });

  it('returns to sign-in when a session expires mid-request', async () => {
    installMockApi({ unauthorizedPredict: true });
    renderApp();

    expect(await screen.findByText(/session has expired/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'Sign in', level: 2 })).toBeInTheDocument();
  });

  it('signs out and clears the dashboard', async () => {
    const api = installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });

    await user.click(screen.getByRole('button', { name: /sign out/i }));

    expect(await screen.findByRole('heading', { name: 'Sign in', level: 2 })).toBeInTheDocument();
    expect(api.logoutCalls).toBe(1);
  });

  it('gates the mentor workspace by the authenticated staff role', async () => {
    const api = installMockApi({ user: mentorUser });
    renderApp();
    expect(await screen.findByRole('heading', { name: 'Mentor workspace' })).toBeInTheDocument();
    expect(screen.getByText(/Mentor A · Mentor/)).toBeInTheDocument();
    expect(await screen.findByText('Profiles in cohort')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(api.cohortCalls).toBe(1);
  });
});

describe('student assessment flow', () => {
  it('analyzes the default profile and renders readiness plus priority gaps', async () => {
    const api = installMockApi();
    const user = userEvent.setup();
    renderApp();

    expect(
      await screen.findByRole('img', { name: 'Readiness score 68 out of 100' }),
    ).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /analyze placement readiness/i })).toBeEnabled();
    expect(screen.getByText('Developing readiness')).toBeInTheDocument();
    expect(screen.getByText('Coding Practice')).toBeInTheDocument();
    expect(screen.getByText('Model ranking signal')).toBeInTheDocument();
    expect(screen.getByText('62.0%')).toBeInTheDocument();
    expect(screen.getByText(/placement guarantee/i)).toBeInTheDocument();

    await waitFor(() => expect(api.saves).toBe(1));
    expect(api.predictCalls).toBe(1);

    const backlogs = screen.getByLabelText('Active Backlogs', { selector: 'input' });
    await user.clear(backlogs);
    await user.type(backlogs, '1');
    expect(
      screen.getByText(/profile changes are not included in the displayed result/i),
    ).toBeInTheDocument();
  });

  it('keeps the form editable while an analysis is in flight', async () => {
    const gate = deferred();
    installMockApi({ holdPredict: gate });
    renderApp();

    expect(
      await screen.findByRole('button', { name: /calculating placement readiness/i }),
    ).toBeDisabled();
    expect(screen.getByLabelText('Active Backlogs', { selector: 'input' })).toBeEnabled();

    gate.resolve();
    expect(
      await screen.findByRole('img', { name: 'Readiness score 68 out of 100' }),
    ).toBeInTheDocument();
  });

  it('blocks invalid numeric input with a specific message and focuses the field', async () => {
    const api = installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });

    const backlogs = screen.getByLabelText('Active Backlogs', { selector: 'input' });
    await user.clear(backlogs);
    await user.type(backlogs, '12');
    await user.click(screen.getByRole('button', { name: /analyze placement readiness/i }));

    expect(
      await screen.findByText('Number of active backlogs must be between 0 and 10.'),
    ).toBeInTheDocument();
    expect(backlogs).toHaveFocus();
    expect(api.predictCalls).toBe(1);
  });

  it('shows a retryable error banner and recovers without losing the form', async () => {
    const api = installMockApi({ failPredict: true });
    const user = userEvent.setup();
    renderApp();

    expect(await screen.findByText(/upstream model unavailable/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/academic cgpa/i)).toBeInTheDocument();

    api.failPredict = false;
    await user.click(screen.getByRole('button', { name: /^retry$/i }));

    expect(
      await screen.findByRole('img', { name: 'Readiness score 68 out of 100' }),
    ).toBeInTheDocument();
    expect(screen.queryByText(/upstream model unavailable/i)).not.toBeInTheDocument();
  });

  it('supports roving keyboard navigation across diagnostic tabs', async () => {
    installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });
    await user.click(screen.getByRole('button', { name: 'Preparation & progress' }));

    const gapsTab = screen.getByRole('tab', { name: /skill gap matrix/i });
    gapsTab.focus();
    fireEvent.keyDown(gapsTab, { key: 'ArrowRight' });

    const roadmapTab = screen.getByRole('tab', { name: /action roadmap/i });
    await waitFor(() => expect(roadmapTab).toHaveAttribute('aria-selected', 'true'));
    expect(roadmapTab).toHaveFocus();
    expect(screen.getByText('Strengthen data structures and algorithms')).toBeInTheDocument();
  });

  it('lazy-loads the explanation panel without refetching the assessment', async () => {
    const api = installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });

    expect(screen.queryByText(/global model feature importance/i)).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Preparation & progress' }));
    await user.click(screen.getByRole('tab', { name: /influential factors/i }));
    expect(screen.getByRole('tab', { name: /influential factors/i })).toHaveAttribute(
      'aria-selected',
      'true',
    );

    expect(
      await screen.findByRole(
        'heading',
        { name: /global model feature importance/i },
        { timeout: 5000 },
      ),
    ).toBeInTheDocument();
    expect(screen.getByText('Reduces readiness')).toBeInTheDocument();
    expect(
      screen.getByRole('table', { name: /global model feature importance/i }),
    ).toBeInTheDocument();
    expect(api.predictCalls).toBe(1);
  });

  it('keeps unsaved inputs when switching student workspace sections', async () => {
    installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });
    const backlog = screen.getByLabelText('Active Backlogs', { selector: 'input' });
    await user.clear(backlog);
    await user.type(backlog, '1');

    await user.click(screen.getByRole('button', { name: 'Evidence & corrections' }));
    const title = screen.getByLabelText('Title', { selector: 'input' });
    await user.type(title, 'Portfolio draft');
    await user.click(screen.getByRole('button', { name: 'Target roles' }));
    expect(screen.getByRole('heading', { name: /target-role gap analysis/i })).toBeVisible();
    await user.click(screen.getByRole('button', { name: 'Evidence & corrections' }));
    expect(title).toHaveValue('Portfolio draft');
    await user.click(screen.getByRole('button', { name: 'Assessment & overview' }));
    expect(backlog).toHaveValue(1);
  });

  it('offers no mentor workspace entry to a student account', async () => {
    const api = installMockApi();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });

    expect(screen.queryByRole('button', { name: /mentor workspace/i })).not.toBeInTheDocument();
    expect(screen.getByText(/Student A · Student/)).toBeInTheDocument();
    expect(api.cohortCalls).toBe(0);
  });

  it('reports offline status and requests a print export', async () => {
    installMockApi();
    const user = userEvent.setup();
    renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });

    fireEvent(window, new Event('offline'));
    expect(await screen.findByText(/you are offline/i)).toBeInTheDocument();
    fireEvent(window, new Event('online'));

    await user.click(screen.getByRole('button', { name: /export report/i }));
    expect(window.print).toHaveBeenCalledTimes(1);
  });
});

describe('accessibility automation', () => {
  async function expectNoSeriousViolations(container) {
    const results = await axe.run(container, {
      rules: {
        'color-contrast': { enabled: false },
        region: { enabled: false },
      },
    });
    const serious = results.violations.filter((violation) =>
      ['critical', 'serious'].includes(violation.impact),
    );
    expect(serious.map((violation) => `${violation.id}: ${violation.help}`)).toEqual([]);
  }

  it('has no critical or serious axe violations on the sign-in screen', async () => {
    installMockApi({ user: null });
    const { container } = renderApp();
    await screen.findByRole('heading', { name: 'Sign in', level: 2 });
    await expectNoSeriousViolations(container);
  });

  it('has no critical or serious axe violations on the student workflow', async () => {
    installMockApi();
    const { container } = renderApp();
    await screen.findByRole('img', { name: 'Readiness score 68 out of 100' });
    await expectNoSeriousViolations(container);
  });
});
