import React, { memo } from 'react';
import { getGapProgress } from '../utils/format';

function SkillGapPanelComponent({ gaps, totalGaps, priorityOnly, onTogglePriorityOnly }) {
  return (
    <div className="skill-gap-panel">
      <div className="panel-toolbar">
        <div>
          <strong>Priority skill gaps</strong>
          <span className="toolbar-note">
            {gaps.length} of {totalGaps} shown
          </span>
        </div>
        <label className="toggle-control">
          <input type="checkbox" checked={priorityOnly} onChange={onTogglePriorityOnly} />
          <span>Show priority gaps only</span>
        </label>
      </div>

      {gaps.length === 0 ? (
        <p className="probability-note">
          No priority gaps remain for this profile. Keep the current preparation routine and
          re-assess after your next mock drive.
        </p>
      ) : (
        <div className="gap-grid">
          {gaps.map((gap) => (
            <article key={gap.skill} className={`gap-card ${gap.severity}`}>
              <div className="gap-header">
                <span className="gap-skill-name">{gap.skill}</span>
                <span className={`gap-status-pill ${gap.severity}`}>{gap.status}</span>
              </div>
              <div className="gap-comparison">
                <div className="gap-comparison-item">
                  <span>Current</span>
                  <strong>
                    {gap.current} {gap.unit}
                  </strong>
                </div>
                <div className="gap-comparison-item">
                  <span>Target</span>
                  <strong>
                    {gap.target} {gap.unit}
                  </strong>
                </div>
              </div>
              <div
                className="gap-progress"
                role="progressbar"
                aria-label={`${gap.skill} progress toward target`}
                aria-valuemin="0"
                aria-valuemax="100"
                aria-valuenow={Math.round(getGapProgress(gap))}
              >
                <span style={{ width: `${getGapProgress(gap)}%` }} />
              </div>
              {gap.gap_delta > 0 && (
                <div className="gap-remaining">
                  <span>
                    Remaining gap:{' '}
                    <strong>
                      {gap.gap_delta} {gap.unit}
                    </strong>
                  </span>
                  <span className="gap-priority">{gap.priority} priority</span>
                </div>
              )}
              <div className="gap-next-step"><span>Suggested next step</span><p className="gap-action-text">{gap.action}</p></div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(SkillGapPanelComponent);
