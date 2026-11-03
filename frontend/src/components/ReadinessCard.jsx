import React, { memo } from 'react';
import { AlertTriangle, CheckCircle2, Info, TrendingUp } from 'lucide-react';
import {
  formatProbability,
  getGaugeColor,
  getProbabilityLabel,
  getScoreBand,
} from '../utils/format';

export function ReadinessSkeleton() {
  return (
    <div className="readiness-score-card loading-card" role="status" aria-live="polite">
      <div className="loading-gauge" aria-hidden="true" />
      <div className="loading-copy">
        <span className="loading-line loading-line-short" />
        <span className="loading-line" />
        <span className="loading-line loading-line-medium" />
        <p>Calculating readiness and preparing your diagnostic profile...</p>
      </div>
    </div>
  );
}

function ReadinessCardComponent({ prediction }) {
  const radius = 64;
  const circumference = 2 * Math.PI * radius;
  const score = prediction.readiness_score;
  const strokeDashoffset = circumference - (score / 100) * circumference;
  const color = getGaugeColor(score);

  return (
    <div className="readiness-score-card">
      <div className="gauge-wrapper">
        <svg
          className="gauge-svg"
          viewBox="0 0 160 160"
          role="img"
          aria-label={`Readiness score ${score} out of 100`}
        >
          <circle className="gauge-bg" cx="80" cy="80" r={radius} />
          <circle
            className="gauge-fill"
            cx="80"
            cy="80"
            r={radius}
            stroke={color}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
          />
        </svg>
        <div className="gauge-center-text" aria-hidden="true">
          <span className="gauge-number" style={{ color }}>
            {score}
          </span>
          <span className="gauge-label">Readiness</span>
        </div>
      </div>

      <div className="readiness-info">
        <div className="readiness-heading"><span className="readiness-eyebrow">YOUR CURRENT ESTIMATE</span><h2>Readiness overview</h2></div>
        <div className="category-badge-row">
          <span className={`category-badge ${prediction.badge_variant}`}>
            {prediction.badge_variant === 'success' && (
              <CheckCircle2 size={15} aria-hidden="true" />
            )}
            {prediction.badge_variant === 'warning' && <TrendingUp size={15} aria-hidden="true" />}
            {prediction.badge_variant === 'critical' && (
              <AlertTriangle size={15} aria-hidden="true" />
            )}
            {prediction.readiness_category}
          </span>
          <span className="score-band">{getScoreBand(score)}</span>
        </div>

        <p className="category-description">{prediction.readiness_description}</p>

        <div className="readiness-support-grid">
          <div className="readiness-support-item">
            <span className="readiness-support-label">
              <Info size={13} aria-hidden="true" />
              {getProbabilityLabel(prediction)}
            </span>
            <strong>
              {formatProbability(prediction.calibrated_probability ?? prediction.model_probability)}
            </strong>
          </div>
          <div className="readiness-support-item">
            <span className="readiness-support-label">What this means</span>
            <strong>
              {score >= 75 ? 'Maintain your momentum' : 'Start with the highest-impact gaps below'}
            </strong>
          </div>
        </div>

        <details className="readiness-model-details"><summary>About this estimate</summary><p>{prediction.probability_note}</p><p>Model {prediction.model_version || 'version not reported'} · predicts the project label “{prediction.outcome_label || 'placement_ready'}”. Its meaning is unverified for LPU outcomes.</p></details>
      </div>
    </div>
  );
}

export default memo(ReadinessCardComponent);
