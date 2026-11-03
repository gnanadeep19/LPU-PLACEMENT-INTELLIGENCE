import React from 'react';

export default function ChunkFallback({ label = 'Loading section' }) {
  return (
    <div className="chunk-skeleton" role="status" aria-live="polite">
      <span className="loading-line loading-line-short" />
      <span className="loading-line" />
      <span className="loading-line loading-line-medium" />
      <span className="sr-only">{label}</span>
    </div>
  );
}
