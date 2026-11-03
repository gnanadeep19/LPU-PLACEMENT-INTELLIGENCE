import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';
import StudentEvidencePanel from './StudentEvidencePanel';
import { getStudentEvidence, getProfileCorrections, deleteStudentEvidence } from '../services/assessmentService';

vi.mock('../services/assessmentService', () => ({ getStudentEvidence: vi.fn(), getProfileCorrections: vi.fn(), deleteStudentEvidence: vi.fn(), addStudentEvidence: vi.fn(), requestProfileCorrection: vi.fn() }));

it('confirms deletion, permits cancellation, and removes evidence only after success', async () => {
  getStudentEvidence.mockResolvedValue([{ id: 5, title: 'Certificate', evidence_type: 'certification', verification_status: 'pending', source: 'self-reported', submitted_at: '2026-11-02' }]);
  getProfileCorrections.mockResolvedValue([]);
  deleteStudentEvidence.mockResolvedValue({ status: 'success' });
  const user = userEvent.setup();
  render(<StudentEvidencePanel studentId={1} />);
  await user.click(await screen.findByRole('button', { name: 'Delete Certificate' }));
  await user.click(screen.getByRole('button', { name: 'Cancel' }));
  expect(deleteStudentEvidence).not.toHaveBeenCalled();
  await user.click(screen.getByRole('button', { name: 'Delete Certificate' }));
  await user.click(screen.getByRole('button', { name: 'Yes, remove' }));
  expect(deleteStudentEvidence).toHaveBeenCalledWith(1, 5);
  expect(screen.queryByText('Certificate')).not.toBeInTheDocument();
  expect(await screen.findByText(/Evidence removed from your profile/)).toBeInTheDocument();
});
