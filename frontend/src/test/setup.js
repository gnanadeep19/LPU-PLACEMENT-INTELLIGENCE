import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach, beforeEach, vi } from 'vitest';
import { clearTelemetryBuffer, setTelemetrySink } from '../telemetry/telemetry';

class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}

globalThis.ResizeObserver = globalThis.ResizeObserver || ResizeObserverStub;

if (!window.matchMedia) {
  window.matchMedia = (query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  });
}

window.print = vi.fn();

// axe's label-content-name-mismatch rule measures text on a canvas; jsdom has
// no rendering backend, so provide the minimal 2D context it needs.
HTMLCanvasElement.prototype.getContext = function getContext() {
  return {
    measureText: (text) => ({ width: String(text).length * 6 }),
    fillText: () => {},
    font: '',
  };
};

beforeEach(() => {
  clearTelemetryBuffer();
  setTelemetrySink(null);
});

afterEach(() => {
  cleanup();
  vi.useRealTimers();
});
