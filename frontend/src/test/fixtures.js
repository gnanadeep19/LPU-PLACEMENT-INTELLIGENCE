export const PASSWORD = 'CorrectHorseBattery42';

export const studentUser = {
  id: 1,
  username: 'student.a',
  display_name: 'Student A',
  role: 'student',
  cohort: 'CSE-A',
};

export const mentorUser = {
  id: 2,
  username: 'mentor.a',
  display_name: 'Mentor A',
  role: 'mentor',
  cohort: 'CSE-A',
};

export const officerUser = {
  id: 3,
  username: 'officer',
  display_name: 'Placement Officer',
  role: 'placement_officer',
  cohort: null,
};

export const predictionFixture = {
  readiness_score: 68,
  readiness_category: 'Developing readiness',
  readiness_description: 'Your profile shows a workable base with clear priority gaps.',
  badge_variant: 'warning',
  model_probability: 0.62,
  calibrated_probability: null,
  probability_is_calibrated: false,
  probability_note: 'This is a model ranking signal, not a calibrated placement probability.',
  skill_gaps: [
    {
      skill: 'Coding Practice',
      current: 55,
      target: 80,
      unit: '%',
      gap_delta: 25,
      severity: 'critical',
      status: 'Needs focus',
      priority: 'High',
      action: 'Solve three data-structure problems per day for four weeks.',
    },
    {
      skill: 'Aptitude',
      current: 70,
      target: 80,
      unit: '%',
      gap_delta: 10,
      severity: 'warning',
      status: 'Below target',
      priority: 'Medium',
      action: 'Complete one timed aptitude set each week.',
    },
    {
      skill: 'Projects',
      current: 3,
      target: 2,
      unit: 'projects',
      gap_delta: 0,
      severity: 'met',
      status: 'Target met',
      priority: 'Low',
      action: 'Keep documenting project outcomes.',
    },
  ],
  recommendations: [
    {
      badge: '01',
      priority: 'High',
      title: 'Strengthen data structures and algorithms',
      details: 'Coding practice is the largest remaining gap.',
      target_feature: 'coding_score',
      action_items: ['Practice arrays and graphs', 'Review two mock assessments'],
    },
  ],
  local_explanations: [
    {
      feature: 'cgpa',
      label: 'Academic CGPA',
      current_value: 7.4,
      reference_value: 8.5,
      contribution: -0.04,
      contribution_points: -4,
      direction: 'Reduces readiness',
    },
  ],
  counterfactual_scenarios: [],
  top_factors: [
    { label: 'Academic CGPA', importance: 77.9 },
    { label: 'Backlogs', importance: 7.3 },
  ],
  disclaimer:
    'Diagnostic indicator only. This is not an eligibility decision or a placement guarantee.',
};

export const cohortFixture = {
  unique_profiles: 12,
  average_readiness_score: 63.5,
  readiness_distribution: { 'Placement Ready': 4 },
  common_gaps: [{ feature: 'coding_score', profiles: 7, share: 0.58 }],
};
