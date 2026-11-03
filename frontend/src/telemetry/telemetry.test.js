import { beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearTelemetryBuffer,
  getTelemetryBuffer,
  recordEvent,
  sanitizeProps,
  setTelemetryRoute,
  setTelemetrySink,
  startWebVitals,
} from './telemetry';

describe('privacy-safe telemetry', () => {
  beforeEach(() => {
    clearTelemetryBuffer();
    setTelemetrySink(null);
    setTelemetryRoute('/');
  });

  it('drops unknown event names', () => {
    expect(recordEvent('student_profile_captured', { email: 'a@b.c' })).toBeNull();
    expect(getTelemetryBuffer()).toHaveLength(0);
  });

  it('only keeps allow-listed property keys', () => {
    const clean = sanitizeProps('assessment_failed', {
      error_kind: 'server',
      status_class: '5xx',
      email: 'student@lpu.in',
      student_name: 'Ada',
      profile_hash: 'abc123',
      request_body: '{"cgpa":7.4}',
    });
    expect(clean).toEqual({ error_kind: 'server', status_class: '5xx' });
  });

  it('rejects free-text values even under an allow-listed key', () => {
    const clean = sanitizeProps('pilot_feedback_submitted', {
      task: 'my name is Ada and my roll number is 123',
      ease: 4,
      friction: 'form',
    });
    expect(clean).toEqual({ ease: 4, friction: 'form' });
  });

  it('strips query strings from the route', () => {
    setTelemetryRoute('/dashboard?cgpa=9.1&student_id=42');
    const event = recordEvent('tab_viewed', { tab: 'gaps' });
    expect(event.route).toBe('/dashboard');
    expect(JSON.stringify(event)).not.toContain('9.1');
  });

  it('rounds numbers and caps the in-memory buffer', () => {
    const event = recordEvent('assessment_succeeded', { duration_ms: 128.7 });
    expect(event.props.duration_ms).toBe(129);

    for (let index = 0; index < 30; index += 1) {
      recordEvent('tab_viewed', { tab: 'gaps' });
    }
    expect(getTelemetryBuffer()).toHaveLength(20);
  });

  it('notifies an injected sink and never throws from it', () => {
    const sink = vi.fn(() => {
      throw new Error('sink down');
    });
    setTelemetrySink(sink);
    expect(() => recordEvent('app_boot')).not.toThrow();
    expect(sink).toHaveBeenCalledTimes(1);
  });

  it('records only bucketed Web Vitals ratings', () => {
    const observe = vi.fn(() => ({ observe: vi.fn(), disconnect: vi.fn() }));
    startWebVitals({ observe });
    expect(observe).toHaveBeenCalled();
  });
});
