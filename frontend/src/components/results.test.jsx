import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';
import ReadinessCard from './ReadinessCard';
import SkillGapPanel from './SkillGapPanel';
import MentorOverview from './MentorOverview';
import { cohortFixture, predictionFixture } from '../test/fixtures';

describe('ReadinessCard', () => {
  it('labels an uncalibrated probability as a ranking signal', () => {
    render(<ReadinessCard prediction={predictionFixture} />);
    expect(screen.getByText('Model ranking signal')).toBeInTheDocument();
    expect(screen.getByText('62.0%')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Readiness score 68 out of 100' })).toBeInTheDocument();
  });

  it('shows an unavailable probability instead of inventing a value', () => {
    render(
      <ReadinessCard
        prediction={{ ...predictionFixture, model_probability: null, calibrated_probability: null }}
      />,
    );
    expect(screen.getByText('Unavailable')).toBeInTheDocument();
  });

  it('uses calibrated wording only when calibration metadata is present', () => {
    render(
      <ReadinessCard
        prediction={{
          ...predictionFixture,
          probability_is_calibrated: true,
          calibrated_probability: 0.812,
        }}
      />,
    );
    expect(screen.getByText('Calibrated probability')).toBeInTheDocument();
    expect(screen.getByText('81.2%')).toBeInTheDocument();
  });
});

describe('SkillGapPanel', () => {
  it('shows a useful all-targets-met state', () => {
    render(<SkillGapPanel gaps={[]} totalGaps={4} priorityOnly onTogglePriorityOnly={() => {}} />);
    expect(screen.getByText(/no priority gaps remain/i)).toBeInTheDocument();
    expect(screen.getByText(/0 of 4 shown/)).toBeInTheDocument();
  });

  it('toggles the priority filter through its labelled checkbox', async () => {
    const onToggle = vi.fn();
    const user = userEvent.setup();
    render(
      <SkillGapPanel
        gaps={predictionFixture.skill_gaps}
        totalGaps={3}
        priorityOnly={false}
        onTogglePriorityOnly={onToggle}
      />,
    );
    await user.click(screen.getByLabelText(/show priority gaps only/i));
    expect(onToggle).toHaveBeenCalledTimes(1);
    expect(screen.getByText(/3 of 3 shown/)).toBeInTheDocument();
  });
});

describe('MentorOverview authorization', () => {
  it('hides aggregate data when the staff role is not authorized', () => {
    render(<MentorOverview cohort={cohortFixture} authorized={false} onRetry={() => {}} />);
    expect(screen.getByText(/available to authenticated staff accounts only/i)).toBeInTheDocument();
    expect(screen.queryByText('12')).not.toBeInTheDocument();
  });

  it('renders aggregate metrics for an authorized mentor', () => {
    const { container } = render(
      <MentorOverview
        cohort={cohortFixture}
        authorized
        loading={false}
        error={null}
        onRetry={() => {}}
      />,
    );
    expect(screen.getByText('Profiles in cohort')).toBeInTheDocument();
    expect(screen.getByText('12')).toBeInTheDocument();
    expect(container.querySelector('.rec-details')).toHaveTextContent('7 students (58%)');
  });

  it('suppresses aggregate details for a small cohort', () => {
    render(
      <MentorOverview
        cohort={{
          suppressed: true,
          unique_profiles: null,
          minimum_group_size: 5,
          readiness_distribution: {},
          common_gaps: [],
        }}
        authorized
        loading={false}
        error={null}
        onRetry={() => {}}
        viewer={{ role: 'mentor', cohort: 'CSE-A' }}
      />,
    );
    expect(screen.getByText(/aggregate results are hidden until this cohort meets the minimum group size/i)).toBeInTheDocument();
    expect(screen.getByText('Suppressed')).toBeInTheDocument();
  });

  it('offers a retry action when cohort analytics fail', async () => {
    const onRetry = vi.fn();
    const user = userEvent.setup();
    render(
      <MentorOverview
        cohort={null}
        authorized
        loading={false}
        error="Cohort analytics are unavailable."
        onRetry={onRetry}
      />,
    );
    expect(screen.getByText('Cohort analytics are unavailable.')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: /retry cohort analytics/i }));
    expect(onRetry).toHaveBeenCalledWith({ force: true });
  });
});
