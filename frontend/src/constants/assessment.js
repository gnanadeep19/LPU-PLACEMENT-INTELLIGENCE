export const PRESETS = {
  high: {
    label: '🌟 Top Performer',
    data: {
      cgpa: 8.9,
      technical_score: 88,
      aptitude_score: 82,
      communication_score: 85,
      coding_score: 90,
      projects: 3,
      internships: 2,
      certifications: 3,
      backlogs: 0,
    },
  },
  average: {
    label: '⚖️ Average Profile',
    data: {
      cgpa: 7.4,
      technical_score: 68,
      aptitude_score: 64,
      communication_score: 70,
      coding_score: 62,
      projects: 2,
      internships: 0,
      certifications: 1,
      backlogs: 0,
    },
  },
  needs_focus: {
    label: '⚠️ Needs Focus',
    data: {
      cgpa: 6.2,
      technical_score: 48,
      aptitude_score: 52,
      communication_score: 56,
      coding_score: 44,
      projects: 1,
      internships: 0,
      certifications: 0,
      backlogs: 0,
    },
  },
  backlog: {
    label: '🚨 Active Backlogs',
    data: {
      cgpa: 6.7,
      technical_score: 64,
      aptitude_score: 62,
      communication_score: 65,
      coding_score: 58,
      projects: 1,
      internships: 0,
      certifications: 1,
      backlogs: 2,
    },
  },
};

export const DEFAULT_FORM_DATA = PRESETS.average.data;

export const FIELD_RANGES = {
  cgpa: [5, 10],
  technical_score: [0, 100],
  aptitude_score: [0, 100],
  communication_score: [0, 100],
  coding_score: [0, 100],
  projects: [0, 15],
  internships: [0, 10],
  certifications: [0, 15],
  backlogs: [0, 10],
};

// Fields rendered as free numeric inputs rather than sliders.
export const INTEGER_FIELDS = ['projects', 'internships', 'certifications', 'backlogs'];

export const DIAGNOSTIC_TABS = ['gaps', 'roadmap', 'factors', 'progress'];

export const MENTOR_TAB = 'cohort';

export function isWithinRange(field, value) {
  const range = FIELD_RANGES[field];
  if (!range) return true;
  if (typeof value !== 'number' || Number.isNaN(value)) return false;
  return value >= range[0] && value <= range[1];
}

export function isFormDirty(formData) {
  return Object.keys(DEFAULT_FORM_DATA).some(
    (field) => formData[field] !== DEFAULT_FORM_DATA[field],
  );
}
