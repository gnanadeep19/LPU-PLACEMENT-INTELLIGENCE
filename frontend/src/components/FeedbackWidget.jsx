import React, { useState } from 'react';
import { MessageSquare } from 'lucide-react';
import { recordEvent } from '../telemetry/telemetry';

const FRICTION_OPTIONS = [
  { value: 'none', label: 'Nothing got in the way' },
  { value: 'form', label: 'Entering my profile' },
  { value: 'interpretation', label: 'Understanding the readiness result' },
  { value: 'actions', label: 'Choosing the next action' },
  { value: 'performance', label: 'Speed or loading' },
  { value: 'access', label: 'Keyboard, screen reader, or mobile use' },
];

/**
 * Pilot feedback capture deliberately collects only a task, a 1-5 ease rating,
 * and a coded friction reason. No free text, names, or profile values.
 */
export default function FeedbackWidget({ task = 'assessment' }) {
  const [ease, setEase] = useState('');
  const [friction, setFriction] = useState('none');
  const [submitted, setSubmitted] = useState(false);

  if (submitted) {
    return (
      <div className="pilot-feedback" role="status">
        <MessageSquare size={16} aria-hidden="true" />
        <span>Thanks — your feedback was recorded without any personal data.</span>
      </div>
    );
  }

  return (
    <form
      className="pilot-feedback"
      onSubmit={(event) => {
        event.preventDefault();
        if (!ease) return;
        recordEvent('pilot_feedback_submitted', {
          task,
          ease: Number(ease),
          friction,
        });
        setSubmitted(true);
      }}
      aria-labelledby="pilot-feedback-heading"
    >
      <div className="pilot-feedback-heading" id="pilot-feedback-heading">
        <MessageSquare size={16} aria-hidden="true" />
        <strong>Pilot feedback (optional, no personal data)</strong>
      </div>

      <fieldset className="pilot-rating">
        <legend>How easy was this task?</legend>
        {[1, 2, 3, 4, 5].map((value) => (
          <label key={value} className="pilot-rating-option">
            <input
              type="radio"
              name="ease"
              value={value}
              checked={ease === String(value)}
              onChange={(event) => setEase(event.target.value)}
            />
            <span>{value}</span>
            <span className="sr-only">
              {value === 1 ? 'Very difficult' : value === 5 ? 'Very easy' : `Rating ${value} of 5`}
            </span>
          </label>
        ))}
      </fieldset>

      <label className="pilot-friction">
        What got in the way?
        <select value={friction} onChange={(event) => setFriction(event.target.value)}>
          {FRICTION_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </label>

      <button type="submit" className="btn-preset" disabled={!ease}>
        Send feedback
      </button>
    </form>
  );
}
