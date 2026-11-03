import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import AdminMentorAssignments from './AdminMentorAssignments';
import { get, post } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({ get: vi.fn(), post: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('allows an active mentor from a different cohort to be assigned', async () => {
  get.mockImplementation((path) => Promise.resolve({ data: path === '/admin/students'
    ? [{ id: 1, username: 'student.a', display_name: 'Student A', cohort: 'CSE', is_active: true }]
    : path === '/admin/mentors' ? [{ id: 2, username: 'mentor.a', display_name: 'Mentor A', cohort: 'CSE', is_active: true }, { id: 3, username: 'mentor.b', display_name: 'Mentor B', cohort: 'ECE', is_active: true }] : [] }));
  post.mockResolvedValue({ status: 'success' });
  const user = userEvent.setup();
  render(<AdminMentorAssignments />);
  await user.selectOptions(await screen.findByLabelText('Student'), '1');
  expect(screen.getByRole('option', { name: /Mentor B/ })).toBeEnabled();
  expect(screen.getByRole('option', { name: /Mentor A/ })).toBeEnabled();
  await user.selectOptions(screen.getByLabelText('Mentor'), '3');
  await user.click(screen.getByRole('button', { name: 'Save assignment' }));
  expect(post).toHaveBeenCalledWith('/admin/students/1/mentor', { mentor_id: 3 });
  expect(await screen.findByRole('status')).toHaveTextContent('Mentor assignment saved');
});

it('shows unlinked mentors but does not allow assignments to them', async () => {
  get.mockImplementation((path) => Promise.resolve(path === '/admin/students' ? { data: [{ id: 1, username: 'student.a', display_name: 'Student A', cohort: 'CSE', is_active: true }] }
    : path === '/admin/mentors' ? { data: [{ id: 2, username: 'mentor.a', display_name: 'Mentor A', cohort: 'CSE', is_active: true }, { id: 3, username: 'mentor.b', display_name: 'Mentor B', cohort: 'ECE', is_active: true }] }
      : { data: [], mapped_mentor_ids: [2], mapped_student_ids: [1] }));
  const user = userEvent.setup();
  render(<AdminMentorAssignments />);
  await user.selectOptions(await screen.findByLabelText('Student'), '1');
  expect(screen.getByRole('option', { name: /Mentor A/ })).toBeEnabled();
  expect(screen.getByRole('option', { name: /Mentor B.*not linked/ })).toBeDisabled();
});
