import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it } from 'vitest';
import FeedbackWidget from './FeedbackWidget';
import { clearTelemetryBuffer, getTelemetryBuffer, setTelemetrySink } from '../telemetry/telemetry';

describe('FeedbackWidget', () => {
  beforeEach(() => {
    clearTelemetryBuffer();
    setTelemetrySink(null);
  });

  it('submits a coded rating without free text or identity fields', async () => {
    const user = userEvent.setup();
    render(<FeedbackWidget task="assessment" />);

    await user.click(screen.getByRole('radio', { name: /rating 4 of 5/i }));
    await user.selectOptions(screen.getByLabelText(/what got in the way/i), 'interpretation');
    await user.click(screen.getByRole('button', { name: /send feedback/i }));

    expect(screen.getByText(/recorded without any personal data/i)).toBeInTheDocument();

    const events = getTelemetryBuffer();
    const feedback = events.find((event) => event.event === 'pilot_feedback_submitted');
    expect(feedback.props).toEqual({ task: 'assessment', ease: 4, friction: 'interpretation' });
    expect(JSON.stringify(feedback)).not.toMatch(/@|name|student/i);
  });

  it('cannot be submitted without a rating', () => {
    render(<FeedbackWidget />);
    expect(screen.getByRole('button', { name: /send feedback/i })).toBeDisabled();
  });
});
