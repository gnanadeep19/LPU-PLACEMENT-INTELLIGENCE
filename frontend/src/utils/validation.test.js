import { describe, expect, it } from 'vitest';
import { normalizeForm, parseFieldValue, validateField, validateForm } from './validation';
import { DEFAULT_FORM_DATA } from '../constants/assessment';

describe('form validation', () => {
  it('parses numbers without turning invalid input into zero', () => {
    expect(parseFieldValue('cgpa', '7.4')).toBe(7.4);
    expect(parseFieldValue('projects', '3')).toBe(3);
    expect(parseFieldValue('projects', '')).toBeNull();
    expect(parseFieldValue('projects', 'abc')).toBeNull();
    expect(parseFieldValue('cgpa', 'not-a-number')).toBeNull();
  });

  it('reports the field and a specific range message', () => {
    expect(validateField('backlogs', 12)).toBe(
      'Number of active backlogs must be between 0 and 10.',
    );
    expect(validateField('cgpa', 4.5)).toContain('Academic CGPA must be between 5 and 10');
    expect(validateField('projects', null)).toBe('Number of projects is required.');
    expect(validateField('coding_score', 55)).toBeNull();
  });

  it('rejects fractional values for integer-only fields', () => {
    expect(validateField('projects', 2.5)).toBe('Number of projects must be a whole number.');
  });

  it('normalizes empty numeric inputs to NaN so validation blocks submission', () => {
    const normalized = normalizeForm({ ...DEFAULT_FORM_DATA, projects: '' });
    expect(Number.isNaN(normalized.projects)).toBe(true);
    expect(validateForm(normalized).valid).toBe(false);
    expect(validateForm(normalizeForm(DEFAULT_FORM_DATA)).valid).toBe(true);
  });
});
