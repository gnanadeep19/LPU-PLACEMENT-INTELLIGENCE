import React, { memo, useEffect, useRef, useState } from 'react';
import { Bar, BarChart, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { formatContribution, formatProbability } from '../utils/format';
import { explainWithShap } from '../services/assessmentService';

function InfluentialFactorsPanelComponent({ prediction }) {
  const localExplanations = prediction.local_explanations || [];
  const scenarios = prediction.counterfactual_scenarios || [];
  const topFactors = prediction.top_factors || [];
  const [shap, setShap] = useState(null);
  const [shapError, setShapError] = useState('');
  const [shapLoading, setShapLoading] = useState(false);
  const pending = useRef(null);

  useEffect(() => {
    pending.current?.abort();
    setShap(null);
    setShapError('');
    setShapLoading(false);
    return () => pending.current?.abort();
  }, [prediction]);

  const loadShap = async () => {
    const controller = new AbortController();
    pending.current?.abort();
    pending.current = controller;
    setShapLoading(true);
    setShapError('');
    try {
      const result = await explainWithShap(prediction.student_profile, prediction.model_version, { signal: controller.signal });
      if (!controller.signal.aborted) setShap(result);
    } catch (error) {
      if (!controller.signal.aborted) setShapError(error?.message || 'SHAP explanation is unavailable.');
    } finally {
      if (!controller.signal.aborted) setShapLoading(false);
    }
  };

  return (
    <div>
      <p className="panel-copy">
        Student-specific factors are estimated by replacing one value at a time with the
        project-defined reference target. They are directional model explanations, not causal effects.
      </p>

      {localExplanations.length === 0 ? (
        <p className="probability-note">
          Local explanations are not available for this assessment.
        </p>
      ) : (
        <div className="gap-grid">
          {localExplanations.slice(0, 5).map((factor) => (
            <div
              key={factor.feature}
              className={`gap-card ${factor.contribution < -0.01 ? 'warning' : 'met'}`}
            >
              <div className="gap-header">
                <span className="gap-skill-name">{factor.label}</span>
                <span
                  className={`gap-status-pill ${factor.contribution < -0.01 ? 'warning' : 'met'}`}
                >
                  {factor.direction}
                </span>
              </div>
              <div className="gap-metric-row">
                <span>
                  Current: <strong>{factor.current_value}</strong>
                </span>
                <span>
                  Reference: <strong>{factor.reference_value}</strong>
                </span>
              </div>
              <p className="gap-action-text">
                Local impact: <strong>{formatContribution(factor.contribution_points)}</strong>
              </p>
            </div>
          ))}
        </div>
      )}

      <section className="section-spaced" aria-labelledby="shap-explanation-heading">
        <h4 id="shap-explanation-heading" className="panel-subheading">SHAP model explanation</h4>
        <p className="probability-note">See how each input moves this model's score compared with its training baseline. SHAP values are in log-odds, not percentage points.</p>
        {prediction.student_profile && prediction.model_version ? (
          <button type="button" className="btn-preset" onClick={loadShap} disabled={shapLoading}>
            {shapLoading ? 'Calculating SHAP…' : shap ? 'Recalculate SHAP' : 'Show SHAP explanation'}
          </button>
        ) : <p className="probability-note">Analyze your profile to request this explanation.</p>}
        {shapError && <p role="alert" className="probability-note">{shapError}</p>}
        {shap && <div className="rec-list section-spaced">
          <p className="probability-note">{shap.note}</p>
          {shap.factors.slice(0, 5).map((factor) => <div className="rec-card" key={factor.feature}>
            <strong>{factor.label}</strong>
            <p className="rec-details">Input: {factor.value} · {factor.impact_log_odds >= 0 ? 'Raises' : 'Lowers'} the model score by {Math.abs(factor.impact_log_odds).toFixed(2)} log-odds</p>
          </div>)}
        </div>}
      </section>

      {scenarios.length > 0 && (
        <div className="section-spaced">
          <h4 className="panel-subheading">Highest-impact one-change scenarios</h4>
          <div className="rec-list">
            {scenarios.slice(0, 3).map((scenario) => (
              <div className="rec-card" key={scenario.feature}>
                <h4 className="rec-title">{scenario.label}</h4>
                <p className="rec-details">
                  Change {scenario.current_value} to {scenario.target_value} {scenario.unit}.
                  Projected readiness probability:{' '}
                  {formatProbability(scenario.projected_probability)}
                  {typeof scenario.probability_gain === 'number'
                    ? ` (${scenario.probability_gain >= 0 ? '+' : ''}${(scenario.probability_gain * 100).toFixed(1)} points)`
                    : ''}
                  .
                </p>
                <p className="probability-note">{scenario.note}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {topFactors.length > 0 && (
        <div className="section-spaced">
          <h4 className="panel-subheading">Global model feature importance</h4>
          <div className="chart-container">
            <table className="sr-only">
              <caption>Global model feature importance</caption>
              <thead>
                <tr>
                  <th scope="col">Factor</th>
                  <th scope="col">Relative weight</th>
                </tr>
              </thead>
              <tbody>
                {topFactors.map((factor) => (
                  <tr key={factor.label}>
                    <th scope="row">{factor.label}</th>
                    <td>{factor.importance}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div aria-hidden="true" className="chart-canvas">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={topFactors}
                  layout="vertical"
                  margin={{ top: 5, right: 30, left: 100, bottom: 5 }}
                >
                  <XAxis type="number" unit="%" stroke="#64748b" />
                  <YAxis
                    type="category"
                    dataKey="label"
                    stroke="#94a3b8"
                    tick={{ fontSize: 12 }}
                    width={110}
                  />
                  <Tooltip
                    formatter={(value) => [`${value}%`, 'Relative Weight']}
                    contentStyle={{
                      background: '#1e293b',
                      border: '1px solid rgba(255,255,255,0.1)',
                      borderRadius: '8px',
                      color: '#fff',
                    }}
                  />
                  <Bar dataKey="importance" radius={[0, 4, 4, 0]}>
                    {topFactors.map((entry, index) => (
                      <Cell
                        key={entry.label}
                        fill={index === 0 ? '#f97316' : index < 3 ? '#6366f1' : '#3b82f6'}
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(InfluentialFactorsPanelComponent);
