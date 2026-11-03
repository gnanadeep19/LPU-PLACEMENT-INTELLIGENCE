import React, { memo, useState } from 'react';
import { MetricCard, SectionIntro } from './ui';
import { formatDelta, formatProbability, getProgressDelta } from '../utils/format';

function formatAssessmentDate(value) {
  if (!value) return 'Date unavailable';
  const utcValue = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$/.test(value) ? `${value.replace(' ', 'T')}Z` : value;
  const date = new Date(utcValue);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : new Intl.DateTimeFormat(undefined, { dateStyle: 'medium', timeStyle: 'short' }).format(date);
}

function ProgressPanelComponent({ history, historyError, loading }) {
  const [showAll, setShowAll] = useState(false);
  const latest = history[0];
  const delta = getProgressDelta(history);
  const previous = history[1];
  const changedFields = latest && previous
    ? Object.keys(latest.student_profile || {}).filter((key) => latest.student_profile[key] !== previous.student_profile?.[key])
    : [];
  const fieldLabels = { cgpa:'academics',technical_score:'technical score',aptitude_score:'aptitude',communication_score:'communication',coding_score:'coding',projects:'projects',internships:'internships',certifications:'certifications',backlogs:'backlogs' };

  return (
    <div className="student-progress">
      <SectionIntro>
        Saved assessments for your signed-in account, stored in the local development database.
      </SectionIntro>

      {historyError && (
        <div className="status-banner status-banner-warning" role="status">
          <span>{historyError}</span>
        </div>
      )}

      {loading && history.length === 0 ? (
        <div className="progress-summary-grid" aria-hidden="true">
          <span className="loading-line loading-line-medium" />
          <span className="loading-line loading-line-medium" />
          <span className="loading-line loading-line-medium" />
        </div>
      ) : null}

      {history.length === 0 && !loading && !historyError ? (
        <p className="probability-note">
          No saved assessments yet. Analyze this profile to start tracking progress.
        </p>
      ) : (
        <>
          {history.length > 0 && (
            <div className="progress-summary-grid">
              <MetricCard label="Assessments tracked" value={history.length} />
              <MetricCard
                label="Latest readiness"
                value={`${latest.readiness_score}/100`}
                tone={latest.readiness_score >= 75 ? 'success' : 'warning'}
              />
              <MetricCard
                label="Change since previous"
                value={formatDelta(delta)}
                tone={delta === null || delta >= 0 ? 'success' : 'warning'}
              />
            </div>
          )}

          {history.length > 1 && (
            <div className="status-banner status-banner-warning" role="note">
              {changedFields.length
                ? `Profile inputs changed since the prior assessment: ${changedFields.map((field) => fieldLabels[field] || field).join(', ')}. These changes occurred alongside the score movement; this comparison does not establish that any one change caused it.`
                : 'No saved profile inputs changed since the previous assessment. A score movement can still reflect model or evaluation differences.'}
            </div>
          )}

          {history.length > 1 && latest?.student_profile && previous?.student_profile && (
            <section className="section-spaced" aria-labelledby="skill-history-heading">
              <h3 id="skill-history-heading" className="panel-subheading">Skill-area change since the prior assessment</h3>
              <div className="table-container"><table className="students-table"><thead><tr><th>Area</th><th>Previous</th><th>Latest</th><th>Change</th></tr></thead><tbody>
                {[
                  ['Academics','cgpa','/10'],['Technical skills','technical_score','%'],['Coding practice','coding_score','%'],['Aptitude','aptitude_score','%'],['Communication','communication_score','%'],['Projects','projects',''],['Internships','internships',''],['Certifications','certifications',''],['Active backlogs','backlogs',''],
                ].map(([label,key,unit])=>{const oldValue=previous.student_profile[key];const newValue=latest.student_profile[key];const change=typeof oldValue==='number'&&typeof newValue==='number'?newValue-oldValue:null;return <tr key={key}><th scope="row">{label}</th><td>{oldValue ?? '—'}{oldValue == null?'':unit}</td><td>{newValue ?? '—'}{newValue == null?'':unit}</td><td>{change == null?'Not comparable':`${change>0?'+':''}${Number.isInteger(change)?change:change.toFixed(1)}${unit}`}</td></tr>;})}
              </tbody></table></div>
              <p className="probability-note">This compares recorded inputs between the two newest assessments. Lower backlog counts are generally positive; other changes are contextual. It does not establish that a field change caused the readiness movement.</p>
            </section>
          )}

          {history.length > 0 && <section className="assessment-history" aria-labelledby="assessment-history-heading">
            <div className="assessment-history-heading"><div><h3 id="assessment-history-heading">Assessment history</h3><p>Your saved assessments, newest first. Reassessing the same inputs can produce the same result. Times are shown in your local time.</p></div><span>{history.length} loaded</span></div>
            <div className="assessment-history-list">
            {(showAll ? history : history.slice(0, 5)).map((item, index) => (
              <article className="assessment-history-item" key={item.id ?? `${item.created_at}-${index}`}>
                <div className="assessment-history-main"><div className="assessment-history-meta"><span className="assessment-history-label">{index === 0 ? 'Latest assessment' : 'Assessment'}</span><time>{formatAssessmentDate(item.created_at)}</time></div><h4>{item.readiness_category}</h4><p>{item.model_version ? `Model ${item.model_version}` : 'Model version not recorded'}</p></div>
                <div className="assessment-history-result"><span>Readiness score</span><strong>{item.readiness_score}<small> / 100</small></strong>
                <div
                  className="history-progress"
                  role="progressbar"
                  aria-label={`Assessment ${history.length - index} readiness score`}
                  aria-valuemin="0"
                  aria-valuemax="100"
                  aria-valuenow={item.readiness_score}
                >
                  <span style={{ width: `${item.readiness_score}%` }} />
                </div>
                <p>Model signal: {formatProbability(item.calibrated_probability ?? item.model_probability)}</p></div>
              </article>
            ))}
            </div>
            {history.length > 5 && <button type="button" className="history-toggle" onClick={() => setShowAll((value) => !value)}>{showAll ? 'Show fewer assessments' : `Show all ${history.length} loaded assessments`}</button>}
            <p className="assessment-history-note">The model signal is an estimate, not a guarantee of placement. History shows the records returned for your account.</p>
          </section>}
        </>
      )}
    </div>
  );
}

export default memo(ProgressPanelComponent);
