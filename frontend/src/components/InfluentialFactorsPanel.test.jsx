import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import InfluentialFactorsPanel from './InfluentialFactorsPanel';
import { explainWithShap } from '../services/assessmentService';

vi.mock('../services/assessmentService', () => ({ explainWithShap: vi.fn() }));

const prediction = { model_version: 'v1', student_profile: { cgpa: 8.1 }, local_explanations: [] };

describe('SHAP explanation', () => {
  beforeEach(() => vi.resetAllMocks());

  it('requests the displayed assessment and labels SHAP units clearly', async () => {
    explainWithShap.mockResolvedValue({ note: 'Model explanation only.', factors: [
      { feature: 'cgpa', label: 'Academic CGPA', value: 8.1, impact_log_odds: -0.5 },
    ] });
    render(<InfluentialFactorsPanel prediction={prediction} />);
    await userEvent.click(screen.getByRole('button', { name: 'Show SHAP explanation' }));
    expect(explainWithShap).toHaveBeenCalledWith(prediction.student_profile, 'v1', expect.objectContaining({ signal: expect.any(AbortSignal) }));
    expect(await screen.findByText(/Lowers the model score by 0.50 log-odds/)).toBeInTheDocument();
    expect(screen.getByText(/not percentage points/i)).toBeInTheDocument();
  });

  it('shows a useful error if SHAP is unavailable', async () => {
    explainWithShap.mockRejectedValue(new Error('SHAP is unavailable for the current model.'));
    render(<InfluentialFactorsPanel prediction={prediction} />);
    await userEvent.click(screen.getByRole('button', { name: 'Show SHAP explanation' }));
    expect(await screen.findByRole('alert')).toHaveTextContent('SHAP is unavailable');
  });
});
