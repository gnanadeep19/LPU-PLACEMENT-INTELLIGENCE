import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import LoginScreen from './LoginScreen';

it('toggles password visibility without submitting or changing the password', async () => {
  const onLogin = vi.fn();
  const user = userEvent.setup();
  render(<LoginScreen onLogin={onLogin} />);
  const field = screen.getByLabelText('Password');
  await user.type(field, 'sample-password');
  expect(field).toHaveAttribute('type', 'password');
  await user.click(screen.getByRole('button', { name: 'Show password' }));
  expect(field).toHaveAttribute('type', 'text');
  expect(field).toHaveValue('sample-password');
  await user.click(screen.getByRole('button', { name: 'Hide password' }));
  expect(field).toHaveAttribute('type', 'password');
  expect(onLogin).not.toHaveBeenCalled();
});
