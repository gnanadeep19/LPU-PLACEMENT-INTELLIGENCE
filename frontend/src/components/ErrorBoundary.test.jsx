import React from 'react';
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import ErrorBoundary from './ErrorBoundary';
import { getTelemetryBuffer } from '../telemetry/telemetry';

function Broken() {
  throw new Error('render exploded');
}

describe('ErrorBoundary', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('shows a recovery message with a support reference and records only the error type', () => {
    vi.spyOn(console, 'error').mockImplementation(() => {});
    render(
      <ErrorBoundary>
        <Broken />
      </ErrorBoundary>,
    );

    expect(screen.getByRole('alert')).toHaveTextContent(/something went wrong/i);
    expect(screen.getByText(/support reference/i)).toBeInTheDocument();
    expect(screen.queryByText('render exploded')).not.toBeInTheDocument();

    const event = getTelemetryBuffer().find((entry) => entry.event === 'error_boundary_caught');
    expect(event.props).toEqual({ error_type: 'Error' });
    expect(JSON.stringify(event)).not.toContain('render exploded');
  });
});
