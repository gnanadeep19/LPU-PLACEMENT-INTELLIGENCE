import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import DeleteControl from './DeleteControl';

it('confirms deletion, supports cancel, and reports errors without hiding the item', async () => {
  const onDelete = vi.fn().mockRejectedValueOnce(new Error('Service unavailable')).mockResolvedValueOnce();
  const user = userEvent.setup();
  render(<DeleteControl label="resource" onDelete={onDelete} />);
  await user.click(screen.getByRole('button', { name: 'Delete resource' }));
  await user.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(onDelete).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Delete resource' }));
  await user.click(screen.getByRole('button', { name: 'Yes, remove' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
  await user.click(screen.getByRole('button', { name: 'Yes, remove' }));
  expect(onDelete).toHaveBeenCalledTimes(2);
  expect(await screen.findByRole('button', { name: 'Delete resource' })).toBeInTheDocument();
});
