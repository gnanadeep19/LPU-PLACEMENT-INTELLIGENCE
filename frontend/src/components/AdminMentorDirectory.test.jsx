import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, describe, expect, it, vi } from 'vitest';
import AdminMentorDirectory from './AdminMentorDirectory';
import { get } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({ get: vi.fn() }));
afterEach(() => vi.resetAllMocks());

describe('admin mentor directory', () => {
  it('shows local mentor accounts and filters by name and cohort', async () => {
    get.mockResolvedValue({ data: [
      { id: 1, username: 'mentor.cse', display_name: 'Mentor CSE', cohort: 'CSE-2027', is_active: true },
      { id: 2, username: 'mentor.ece', display_name: 'Mentor ECE', cohort: 'ECE-2027', is_active: false },
    ] });
    const user = userEvent.setup();
    render(<AdminMentorDirectory />);
    expect(await screen.findByText('mentor.cse')).toBeInTheDocument();
    expect(screen.getByText(/does not confirm that a Supabase login/i)).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Cohort'), 'ECE-2027');
    expect(screen.queryByText('mentor.cse')).not.toBeInTheDocument();
    expect(within(screen.getByRole('table')).getByText('Inactive')).toBeInTheDocument();
    await user.selectOptions(screen.getByLabelText('Cohort'), 'All cohorts');
    await user.type(screen.getByLabelText('Find a mentor'), 'cse');
    expect(screen.getByText('mentor.cse')).toBeInTheDocument();
    expect(screen.queryByText('mentor.ece')).not.toBeInTheDocument();
  });

  it('shows a retry message if the directory is unavailable', async () => {
    get.mockRejectedValue(new Error('Service unavailable'));
    render(<AdminMentorDirectory />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Service unavailable');
  });

  it('shows all student accounts from the student directory and supports search', async () => {
    get.mockResolvedValue({ data: [
      { id: 1, username: 'student.a', display_name: 'Student A', cohort: 'CSE-2027', is_active: true },
      { id: 2, username: 'student.b', display_name: 'Student B', cohort: 'ECE-2027', is_active: false },
    ] });
    const user = userEvent.setup();
    render(<AdminMentorDirectory kind="student" />);
    expect(await screen.findByText('student.a')).toBeInTheDocument();
    expect(get).toHaveBeenCalledWith('/admin/students');
    expect(screen.getByText(/including students without an assessment/i)).toBeInTheDocument();
    await user.type(screen.getByLabelText('Find a student'), 'student.b');
    expect(screen.queryByText('student.a')).not.toBeInTheDocument();
    expect(screen.getByText('student.b')).toBeInTheDocument();
  });
});
