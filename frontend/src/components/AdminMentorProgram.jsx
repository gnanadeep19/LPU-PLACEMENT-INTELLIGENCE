import React from 'react';
import { MetricCard } from './ui';
import { EXAMPLE_COHORTS } from '../constants/pipelineOptions';

const dateLabel = (date) => date ? new Date(date).toLocaleDateString() : 'Not recorded';

export default function AdminMentorProgram({ students, filter, setFilter, loading, rosterLoaded }) {
  const recordedCohorts = [...new Set(students.map((student) => student.cohort).filter(Boolean))].sort();
  const examples = EXAMPLE_COHORTS.filter(([value]) => !recordedCohorts.includes(value));
  const visible = students.filter((student) => filter === 'All cohorts' || student.cohort === filter);
  const available = visible.filter((student) => student.coaching_available !== false);
  const records = available.flatMap((student) => student.coaching_records || []);
  const goals = records.filter((record) => record.kind === 'goal');
  const today = new Date();
  const localToday = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
  const metric = (value) => rosterLoaded ? value : '—';

  return <section className="glass-card admin-mentor-program">
    <div className="card-header"><div><h2>Mentor program oversight</h2><p>Review cohort support and recorded coaching activity.</p></div>
      <label className="input-label">Cohort<select className="number-input-field" value={filter} onChange={(event) => setFilter(event.target.value)}>
        <option>All cohorts</option>
        {recordedCohorts.length > 0 && <optgroup label="Cohorts with assessed students">{recordedCohorts.map((cohort) => <option key={cohort} value={cohort}>{cohort}</option>)}</optgroup>}
        {examples.length > 0 && <optgroup label="Example B.Tech cohorts (no assessed students)">{examples.map(([value, label]) => <option key={value} value={value}>{label}</option>)}</optgroup>}
      </select></label>
    </div>
    <div className="card-body">
      <p className="probability-note">B.Tech examples are filter options, not created cohorts. Individual assignments are managed in Student users; assigned mentors can also access students from other cohorts.</p>
      {!rosterLoaded ? <p className="admin-empty-state">{loading ? 'Loading the student roster…' : 'The student roster is unavailable. Use Refresh to try again.'}</p> : <>
        <div className="progress-summary-grid">
          <MetricCard label="Students with a check-in" value={metric(available.filter((student) => (student.coaching_records || []).some((record) => record.kind === 'check_in')).length)} />
          <MetricCard label="Goals in plans" value={metric(goals.length)} />
          <MetricCard label="Goals completed" value={metric(goals.filter((goal) => goal.status === 'completed').length)} tone="success" />
          <MetricCard label="Overdue goals" value={metric(goals.filter((goal) => goal.due_date && goal.due_date < localToday && goal.status !== 'completed').length)} tone="warning" />
        </div>
        <p className="probability-note">Coaching coverage: {available.length} of {visible.length} assessed students. Counts include student-created goals and cover only available timelines.</p>
        <div className="table-container"><table className="students-table"><thead><tr><th>Student</th><th>Cohort</th><th>Assigned mentor</th><th>Readiness</th><th>Goals</th><th>Completed</th><th>Last check-in</th></tr></thead><tbody>
          {!visible.length && <tr><td colSpan={7} className="admin-empty-cell">No assessed students are available for this cohort.</td></tr>}
          {visible.map((student) => {
            const hasTimeline = student.coaching_available !== false;
            const timeline = student.coaching_records || [];
            const studentGoals = timeline.filter((record) => record.kind === 'goal');
            const checkins = timeline.filter((record) => record.kind === 'check_in').sort((a, b) => String(b.created_at).localeCompare(String(a.created_at)));
            return <tr key={student.user_id}><td>{student.display_name}</td><td>{student.cohort || '—'}</td><td>{student.assigned_mentor?.display_name || 'Not assigned'}</td><td>{student.readiness_score}/100</td><td>{hasTimeline ? studentGoals.length : 'Unavailable'}</td><td>{hasTimeline ? studentGoals.filter((goal) => goal.status === 'completed').length : 'Unavailable'}</td><td>{hasTimeline ? dateLabel(checkins[0]?.created_at) : 'Unavailable'}</td></tr>;
          })}
        </tbody></table></div>
        <h3 className="panel-subheading">Student support activity</h3>
        <div className="admin-mentor-activity">{visible.map((student) => <details className="admin-mentor-activity-item" key={student.user_id}>
          <summary><strong>{student.display_name}</strong><span>{student.cohort || 'No cohort'} · {student.coaching_available === false ? 'Timeline unavailable' : `${(student.coaching_records || []).length} records`}</span></summary>
          {student.coaching_available === false ? <p>Coaching data could not be retrieved for this student. Check the Supabase account mapping or retry.</p> : !(student.coaching_records || []).length ? <p>No coaching activity has been recorded.</p> : <ul>
            {student.coaching_records.map((record) => {
              const author = student.cohort_mentors?.find((mentor) => mentor.id === record.author_id)?.display_name || (record.author_id === student.user_id ? student.display_name : `Account ${record.author_id}`);
              return <li key={record.id}><div className="admin-activity-meta"><span>{record.kind.replaceAll('_', ' ')} · {record.visibility === 'mentor' ? 'Mentor only' : 'Visible to student'}</span><time>{dateLabel(record.created_at)}</time></div><strong>{record.title}</strong>{record.detail && <p>{record.detail}</p>}<p className="admin-activity-footer">Recorded by {author}{record.kind === 'goal' ? ` · ${record.status.replaceAll('_', ' ')}` : ''}{record.due_date ? ` · Due ${record.due_date}` : ''}{record.evidence_url ? ' · Evidence link recorded' : ''}</p></li>;
            })}
          </ul>}
        </details>)}</div>
      </>}
      <p className="probability-note">These are activity indicators, not evidence that mentoring caused a change in readiness.</p>
    </div>
  </section>;
}
