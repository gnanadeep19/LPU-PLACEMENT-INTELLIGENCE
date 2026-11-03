import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, expect, it, vi } from 'vitest';
import StudyResources from './StudyResources';
import { get, post } from '../services/apiClient';

vi.mock('../services/apiClient', () => ({ get: vi.fn(), post: vi.fn(), request: vi.fn(), download: vi.fn() }));
afterEach(() => vi.resetAllMocks());

it('lets a mentor upload a file for the selected student', async () => {
  get.mockResolvedValue({ data: [] });
  post.mockResolvedValue({ status: 'success' });
  const user = userEvent.setup();
  render(<StudyResources studentId={12} canUpload />);
  await screen.findByText('No resources have been shared with this student yet.');
  await user.type(screen.getByLabelText('Resource title'), 'Study guide');
  await user.upload(screen.getByLabelText('Study file'), new File(['notes'], 'notes.txt', { type: 'text/plain' }));
  expect(screen.getByLabelText('Study file').files).toHaveLength(1);
  await user.click(screen.getByRole('button', { name: 'Share resource' }));
  await waitFor(() => expect(post).toHaveBeenCalled());
  const [path, payload] = post.mock.calls[0];
  expect(path).toBe('/students/12/resources');
  expect(payload.get('title')).toBe('Study guide');
  expect(payload.get('file').name).toBe('notes.txt');
  expect(await screen.findByRole('status')).toHaveTextContent('Resource shared');
});

it('shows the mentor materials to a student without an upload form', async () => {
  get.mockResolvedValue({ data: [{ id: 3, title: 'SQL guide', description: 'Read chapter one', filename: 'guide.pdf', created_at: '2026-11-01T00:00:00Z' }] });
  render(<StudyResources studentId={12} />);
  expect(await screen.findByText('SQL guide')).toBeInTheDocument();
  expect(screen.getByText('Read chapter one')).toBeInTheDocument();
  expect(screen.getByRole('button', { name: 'Download' })).toBeInTheDocument();
  expect(screen.queryByRole('button', { name: 'Share resource' })).not.toBeInTheDocument();
});

it('filters resources by search and subject and clears both filters', async () => {
  get.mockResolvedValue({ data: [
    { id: 1, title: 'SQL practice', filename: 'sql.pdf', category: 'Coding', created_at: '2026-11-01T00:00:00Z' },
    { id: 2, title: 'Interview guide', filename: 'interview.pdf', category: 'Interview', created_at: '2026-11-01T00:00:00Z' },
  ] });
  const user = userEvent.setup();
  render(<StudyResources studentId={12} />);
  expect(await screen.findByText('SQL practice')).toBeInTheDocument();
  expect(screen.getByText('2 of 2 resources')).toBeInTheDocument();
  await user.selectOptions(screen.getByLabelText('Subject'), 'Coding');
  expect(screen.queryByText('Interview guide')).not.toBeInTheDocument();
  await user.type(screen.getByLabelText('Search resources'), 'missing');
  expect(screen.getByText('No resources match your search.')).toBeInTheDocument();
  expect(screen.getByText('0 of 2 resources')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Clear filters' }));
  expect(screen.getByText('SQL practice')).toBeInTheDocument();
  expect(screen.getByText('Interview guide')).toBeInTheDocument();
});

it('lets the uploader retry a pending notification without uploading again', async () => {
  const resource = { id: 3, author_id: 7, title: 'SQL guide', filename: 'guide.pdf', created_at: '2026-11-01T00:00:00Z', notification_status: 'pending' };
  get.mockResolvedValueOnce({ data: [resource] }).mockResolvedValue({ data: [{ ...resource, notification_status: 'sent' }] });
  post.mockResolvedValue({ status: 'success', data: { notification_sent: true } });
  const user = userEvent.setup();
  render(<StudyResources studentId={12} canUpload viewer={{ id: 7, role: 'mentor' }} />);
  expect(await screen.findByText('Student notification pending')).toBeInTheDocument();
  await user.click(screen.getByRole('button', { name: 'Retry notification' }));
  expect(post).toHaveBeenCalledWith('/students/12/resources/3/notification', {});
  expect(await screen.findByRole('status')).toHaveTextContent('Notification sent for SQL guide.');
  expect(screen.queryByText('Student notification pending')).not.toBeInTheDocument();
});

it('reuses the same upload key after an uncertain network failure', async () => {
  get.mockResolvedValue({ data: [] });
  post.mockRejectedValueOnce(new Error('Network unavailable')).mockResolvedValueOnce({ status: 'success', data: { notification_sent: true } });
  const user = userEvent.setup();
  render(<StudyResources studentId={12} canUpload />);
  await screen.findByText('No resources have been shared with this student yet.');
  await user.type(screen.getByLabelText('Resource title'), 'Study guide');
  await user.upload(screen.getByLabelText('Study file'), new File(['notes'], 'notes.txt', { type: 'text/plain' }));
  await user.click(screen.getByRole('button', { name: 'Share resource' }));
  expect(await screen.findByRole('alert')).toHaveTextContent('Failed');
  await user.click(screen.getByRole('button', { name: 'Share resource' }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
  const first = post.mock.calls[0][1].get('upload_key');
  const second = post.mock.calls[1][1].get('upload_key');
  expect(first).toMatch(/^[0-9a-f-]{36}$/);
  expect(second).toBe(first);
});
