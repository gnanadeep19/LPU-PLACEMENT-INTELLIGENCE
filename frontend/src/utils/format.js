const SEVERITY_RANK = { critical: 0, warning: 1, met: 2 };

export function getGaugeColor(value) {
  if (value >= 75) return '#10b981'; // Emerald
  if (value >= 50) return '#f59e0b'; // Amber
  return '#ef4444'; // Red
}

export function getScoreBand(value) {
  if (value >= 75) return 'Strong starting position';
  if (value >= 50) return 'Developing placement readiness';
  return 'Priority improvement required';
}

export function formatProbability(probability) {
  if (probability === null || probability === undefined || Number.isNaN(probability)) {
    return 'Unavailable';
  }
  return `${(probability * 100).toFixed(1)}%`;
}

export function sortSkillGaps(gaps = [], priorityOnly = false) {
  return [...gaps]
    .sort((a, b) => (SEVERITY_RANK[a.severity] ?? 3) - (SEVERITY_RANK[b.severity] ?? 3))
    .filter((gap) => !priorityOnly || gap.severity !== 'met');
}

export function getGapProgress(gap) {
  if (!gap || gap.target <= 0) return 100;
  return Math.min(100, Math.max(0, (gap.current / gap.target) * 100));
}

export function getReadinessProbability(prediction) {
  if (!prediction) return null;
  return prediction.calibrated_probability ?? prediction.model_probability ?? null;
}

export function getProbabilityLabel(prediction) {
  return prediction?.probability_is_calibrated ? 'Calibrated probability' : 'Model ranking signal';
}

export function getProgressDelta(history = []) {
  if (history.length < 2) return null;
  return history[0].readiness_score - history[1].readiness_score;
}

export function formatDelta(delta) {
  if (delta === null || delta === undefined) return 'First assessment';
  return `${delta >= 0 ? '+' : ''}${delta} pts`;
}

export function formatContribution(points) {
  if (typeof points !== 'number' || Number.isNaN(points)) return 'Unavailable';
  return `${points > 0 ? '+' : ''}${points} points`;
}
