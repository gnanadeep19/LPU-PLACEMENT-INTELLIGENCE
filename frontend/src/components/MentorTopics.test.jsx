import React from 'react';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import MentorOverview from './MentorOverview';
import { getMentorStudents } from '../services/assessmentService';

vi.mock('../services/assessmentService', () => ({ getMentorStudents: vi.fn(), createCoachingRecord: vi.fn(), updateCoachingRecord: vi.fn() }));
vi.mock('./StudyResources', () => ({ default: () => <div><h3>Shared study materials</h3><label>Resource draft<input /></label></div> }));
vi.mock('./CvReview', () => ({ default: () => <div>CV review panel</div> }));

it('separates student details into topics and keeps drafts when switching', async () => {
  getMentorStudents.mockResolvedValue([{ user_id: 1, display_name: 'Demo Student', username: 'student.demo', cohort: 'CSE-A', created_at: '2026-11-01', readiness_score: 60, readiness_category: 'Developing', profile: {}, coaching_records: [] }]);
  const user = userEvent.setup();
  render(<MentorOverview authorized viewer={{ id: 2, role: 'mentor', cohort: 'CSE-A' }} />);
  const detail = await screen.findByRole('region', { name: 'Selected mentee detail' });
  const profile = await within(detail).findByRole('button', { name: 'Profile' });
  expect(profile).toHaveAttribute('aria-pressed', 'true');
  expect(within(detail).getByText('Profile evidence and skill gaps')).toBeVisible();
  expect(within(detail).getByText('Shared study materials')).not.toBeVisible();
  await user.click(within(detail).getByRole('button', { name: 'Study resources' }));
  expect(within(detail).getByText('Shared study materials')).toBeVisible();
  expect(within(detail).getByText('Profile evidence and skill gaps')).not.toBeVisible();
  await user.type(within(detail).getByLabelText('Resource draft'), 'SQL guide');
  await user.click(within(detail).getByRole('button', { name: 'Goals & follow-up' }));
  expect(within(detail).getByText('Action plan and mentor timeline')).toBeVisible();
  await user.click(within(detail).getByRole('button', { name: 'Study resources' }));
  expect(within(detail).getByLabelText('Resource draft')).toHaveValue('SQL guide');
});

it('puts a pending CV in the follow-up queue and opens its review panel', async () => {
  getMentorStudents.mockResolvedValue([{ user_id: 1, display_name: 'Demo Student', username: 'student.demo', cohort: 'CSE-A', created_at: null, readiness_score: null, readiness_category: 'Not assessed', profile: {}, coaching_records: [], cv_status: 'pending' }]);
  const user = userEvent.setup();
  render(<MentorOverview authorized viewer={{ id: 2, role: 'mentor', cohort: 'CSE-A' }} />);
  const queueItem = (await screen.findByText('CV awaiting review')).closest('article');
  await user.click(within(queueItem).getByRole('button', { name: /Open student/ }));
  expect(screen.getByText('CV review panel')).toBeVisible();
});
