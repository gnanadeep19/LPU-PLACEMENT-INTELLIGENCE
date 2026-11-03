import React from 'react';
import { AlertTriangle, RefreshCw } from 'lucide-react';
import { createCorrelationId, recordEvent, reportFrontendError } from '../telemetry/telemetry';

export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { error: null, correlationId: null, chunkFailed: false };
  }

  static getDerivedStateFromError(error) {
    return {
      error,
      correlationId: createCorrelationId(),
      chunkFailed: /dynamically imported module|Loading chunk|ChunkLoadError/i.test(
        error?.message || '',
      ),
    };
  }

  componentDidCatch(error, info) {
    reportFrontendError(error);
    if (this.state.chunkFailed) {
      recordEvent('chunk_load_failed', { chunk: 'lazy-panel' });
    }
    // Error details stay out of telemetry; only the type is recorded.
    if (import.meta.env?.DEV) {
      console.error('Render failure', error, info?.componentStack);
    }
  }

  handleRetry = () => {
    this.setState({ error: null, correlationId: null, chunkFailed: false });
  };

  render() {
    const { error, correlationId, chunkFailed } = this.state;
    if (!error) return this.props.children;

    return (
      <div className="error-boundary glass-card" role="alert">
        <AlertTriangle size={22} color="var(--color-danger)" aria-hidden="true" />
        <div>
          <h2>{chunkFailed ? 'This section did not finish loading' : 'Something went wrong'}</h2>
          <p>
            {chunkFailed
              ? 'A part of the dashboard could not be downloaded. Check your connection and try again.'
              : 'The dashboard hit an unexpected problem. Your entered values are still available.'}
          </p>
          <p className="probability-note">
            Support reference: <code>{correlationId.slice(0, 8)}</code>
          </p>
          <button type="button" className="btn-preset" onClick={this.handleRetry}>
            <RefreshCw size={14} aria-hidden="true" /> Try again
          </button>
        </div>
      </div>
    );
  }
}
