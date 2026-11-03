import { describe, expect, it } from 'vitest';
import {
  formatContribution,
  formatDelta,
  formatProbability,
  getGapProgress,
  getProbabilityLabel,
  getProgressDelta,
  getScoreBand,
  sortSkillGaps,
} from './format';

describe('format helpers', () => {
  it('maps scores to readiness bands at the boundaries', () => {
    expect(getScoreBand(75)).toBe('Strong starting position');
    expect(getScoreBand(74)).toBe('Developing placement readiness');
    expect(getScoreBand(50)).toBe('Developing placement readiness');
    expect(getScoreBand(49)).toBe('Priority improvement required');
  });

  it('never renders null or undefined probabilities as a number', () => {
    expect(formatProbability(null)).toBe('Unavailable');
    expect(formatProbability(undefined)).toBe('Unavailable');
    expect(formatProbability(0.8123)).toBe('81.2%');
  });

  it('distinguishes calibrated probability from a ranking signal', () => {
    expect(getProbabilityLabel({ probability_is_calibrated: true })).toBe('Calibrated probability');
    expect(getProbabilityLabel({ probability_is_calibrated: false })).toBe('Model ranking signal');
    expect(getProbabilityLabel(null)).toBe('Model ranking signal');
  });

  it('sorts gaps by severity and can hide met targets', () => {
    const gaps = [
      { skill: 'Projects', severity: 'met' },
      { skill: 'Coding', severity: 'critical' },
      { skill: 'Aptitude', severity: 'warning' },
    ];
    expect(sortSkillGaps(gaps).map((gap) => gap.skill)).toEqual(['Coding', 'Aptitude', 'Projects']);
    expect(sortSkillGaps(gaps, true).map((gap) => gap.skill)).toEqual(['Coding', 'Aptitude']);
  });

  it('clamps gap progress and handles zero targets', () => {
    expect(getGapProgress({ current: 40, target: 80 })).toBe(50);
    expect(getGapProgress({ current: 120, target: 80 })).toBe(100);
    expect(getGapProgress({ current: 5, target: 0 })).toBe(100);
    expect(getGapProgress(null)).toBe(100);
  });

  it('computes the delta only when two assessments exist', () => {
    expect(getProgressDelta([{ readiness_score: 80 }])).toBeNull();
    expect(getProgressDelta([{ readiness_score: 80 }, { readiness_score: 62 }])).toBe(18);
    expect(formatDelta(null)).toBe('First assessment');
    expect(formatDelta(4)).toBe('+4 pts');
    expect(formatDelta(-3)).toBe('-3 pts');
    expect(formatContribution(-2.5)).toBe('-2.5 points');
    expect(formatContribution(3)).toBe('+3 points');
  });
});
