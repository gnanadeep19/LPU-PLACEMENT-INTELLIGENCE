import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import CvReview from './CvReview';
import { get, post, request } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({ get: vi.fn(), post: vi.fn(), request: vi.fn(), download: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('lets a student submit a CV and shows its pending review', async () => {
  get.mockResolvedValueOnce({ data: [] }).mockResolvedValue({ data: [{ id: 1, filename: 'cv.pdf', status: 'pending', submitted_at: '2026-11-03T10:00:00Z' }] });
  post.mockResolvedValue({ data: { id: 1 } });
  const user = userEvent.setup();
  render(<CvReview studentId={12} />);
  await screen.findByText('You have not submitted a CV yet.');
  await user.upload(screen.getByLabelText('Choose your CV'), new File(['%PDF-test'], 'cv.pdf', { type: 'application/pdf' }));
  await user.click(screen.getByRole('button', { name: 'Submit for review' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  expect(post.mock.calls[0][0]).toBe('/students/12/cv');
  expect(post.mock.calls[0][1].get('file').name).toBe('cv.pdf');
  expect(await screen.findByText('Awaiting mentor review')).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Approve CV' })).not.toBeInTheDocument();
});

it('requires mentor feedback for changes and sends approval for the current CV', async () => {
  get.mockResolvedValueOnce({ data: [{ id: 4, filename: 'cv.pdf', status: 'pending', submitted_at: '2026-11-03T10:00:00Z' }] })
    .mockResolvedValue({ data: [{ id: 4, filename: 'cv.pdf', status: 'approved', submitted_at: '2026-11-03T10:00:00Z', feedback: 'Clear and concise' }] });
  request.mockResolvedValue({ status: 'success' });
  const user = userEvent.setup();
  render(<CvReview studentId={12} mentor />);
  await screen.findByText('Awaiting mentor review');
  await user.click(screen.getByRole('button', { name: 'Request changes' }));
  expect(screen.getByRole('alert')).toHaveTextContent('Add feedback');
  expect(request).not.toHaveBeenCalled();
  await user.type(screen.getByLabelText('Feedback to student'), 'Clear and concise');
  await user.click(screen.getByRole('button', { name: 'Approve CV' }));
  expect(request).toHaveBeenCalledWith('/students/12/cv/4/review', { method: 'PATCH', body: { status: 'approved', feedback: 'Clear and concise' } });
  expect(await screen.findByText('Approved by mentor')).toBeInTheDocument();
});
