import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import ProgressPanel from './ProgressPanel';

describe('assessment history', () => {
  it('shows recent records first and preserves access to older loaded assessments', async () => {
    const history = Array.from({ length: 7 }, (_, index) => ({
      id: index + 1,
      created_at: '2026-10-29 19:25:01',
      readiness_score: 42,
      readiness_category: 'Developing',
      model_probability: 0.42,
      model_version: 'v1',
    }));
    const user = userEvent.setup();
    render(<ProgressPanel history={history} loading={false} />);
    const section = screen.getByRole('region', { name: 'Assessment history' });
    expect(within(section).getAllByRole('article')).toHaveLength(5);
    expect(within(section).getAllByText('Model signal: 42.0%')).toHaveLength(5);
    const localDate = new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(new Date('2026-10-29T19:25:01Z'));
    expect(within(section).getAllByText(localDate)).toHaveLength(5);
    await user.click(within(section).getByRole('button', { name: /show all 7 loaded/i }));
    expect(within(section).getAllByRole('article')).toHaveLength(7);
    await user.click(within(section).getByRole('button', { name: /show fewer/i }));
    expect(within(section).getAllByRole('article')).toHaveLength(5);
  });

  it('does not describe history as empty when loading it failed', () => {
    render(<ProgressPanel history={[]} historyError="History unavailable" loading={false} />);
    expect(screen.getByText('History unavailable')).toBeInTheDocument();
    expect(screen.queryByText(/no saved assessments yet/i)).not.toBeInTheDocument();
  });
});
