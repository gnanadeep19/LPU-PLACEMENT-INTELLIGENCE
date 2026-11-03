import { FIELD_RANGES, INTEGER_FIELDS } from '../constants/assessment';

export const FIELD_LABELS = {
  cgpa: 'Academic CGPA',
  coding_score: 'Coding practice score',
  technical_score: 'Core CS technical score',
  aptitude_score: 'Aptitude and logical reasoning score',
  communication_score: 'Communication and HR fit score',
  projects: 'Number of projects',
  internships: 'Number of internships',
  certifications: 'Number of certifications',
  backlogs: 'Number of active backlogs',
};

/**
 * Parse a user-entered value without silently coercing invalid input to 0.
 * Returns null when the field is empty or not a finite number.
 */
export function parseFieldValue(field, rawValue) {
  if (rawValue === '' || rawValue === null || rawValue === undefined) return null;
  const parsed = INTEGER_FIELDS.includes(field)
    ? Number.parseInt(rawValue, 10)
    : Number.parseFloat(rawValue);
  if (!Number.isFinite(parsed)) return null;
  return parsed;
}

export function validateField(field, value) {
  const range = FIELD_RANGES[field];
  const label = FIELD_LABELS[field] || field;
  if (value === null || value === undefined || Number.isNaN(value)) {
    return `${label} is required.`;
  }
  if (!range) return null;
  if (INTEGER_FIELDS.includes(field) && !Number.isInteger(value)) {
    return `${label} must be a whole number.`;
  }
  if (value < range[0] || value > range[1]) {
    return `${label} must be between ${range[0]} and ${range[1]}.`;
  }
  return null;
}

/**
 * Validate every field and return the first problem so the form can announce a
 * single, specific correction and focus the offending input.
 */
export function normalizeForm(formData) {
  const normalized = {};
  for (const field of Object.keys(FIELD_RANGES)) {
    const parsed = parseFieldValue(field, formData[field]);
    normalized[field] = parsed === null ? Number.NaN : parsed;
  }
  return normalized;
}

export function validateForm(formData) {
  for (const field of Object.keys(FIELD_RANGES)) {
    const message = validateField(field, formData[field]);
    if (message) {
      return { valid: false, field, message };
    }
  }
  return { valid: true, field: null, message: null };
}
