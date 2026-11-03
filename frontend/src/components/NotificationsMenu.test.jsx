import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import NotificationsMenu from './NotificationsMenu';

const mocks = vi.hoisted(() => ({ from: vi.fn() }));
vi.mock('../services/supabaseClient', () => ({ getSupabaseClient: () => ({ from: mocks.from }) }));

describe('NotificationsMenu', () => {
  beforeEach(() => {
    const rows = [{ id: 7, title: 'New goal', message: 'Review your goal.', created_at: '2026-10-31T00:00:00Z', read_at: null }];
    mocks.from.mockReset().mockImplementation(() => ({
      select: (_fields, options) => options?.head
        ? { is: () => Promise.resolve({ count: 1, error: null }) }
        : { order: () => ({ limit: () => Promise.resolve({ data: rows, error: null }) }) },
      update: () => ({ eq: () => ({ select: () => { rows[0].read_at = '2026-10-31T01:00:00Z'; return Promise.resolve({ data: [{ id: 7 }], error: null }); } }) }),
    }));
  });

  it('shows a notification and lets the recipient mark it as read', async () => {
    const user = userEvent.setup();
    render(<NotificationsMenu />);
    await waitFor(() => expect(screen.getByRole('button', { name: 'Notifications, 1 unread' })).toBeInTheDocument());
    await user.click(screen.getByRole('button', { name: 'Notifications, 1 unread' }));
    expect(await screen.findByText('Review your goal.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Mark New goal as read' }));
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Mark New goal as read' })).not.toBeInTheDocument());
  });

  it('closes on outside click or Escape, but stays open when interacting inside', async () => {
    const user = userEvent.setup();
    render(<><NotificationsMenu /><button type="button">Outside</button></>);
    const toggle = await screen.findByRole('button', { name: 'Notifications, 1 unread' });
    await user.click(toggle);
    await user.click(screen.getByText('Review your goal.'));
    expect(screen.getByRole('region', { name: 'Notifications' })).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Outside' }));
    expect(screen.queryByRole('region', { name: 'Notifications' })).not.toBeInTheDocument();
    await user.click(toggle);
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('region', { name: 'Notifications' })).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });
});
