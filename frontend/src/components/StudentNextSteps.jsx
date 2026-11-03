import React, { useCallback, useEffect, useState } from 'react';
import { ArrowRight, RefreshCw } from 'lucide-react';
import { getCoachingRecords, getStudentEvidence } from '../services/assessmentService';

const formatDate = (value) => {
  if (!value) return 'No due date';
  const date = new Date(value.length === 10 ? `${value}T12:00:00` : value);
  return Number.isNaN(date.getTime()) ? 'Date unavailable' : date.toLocaleDateString();
};

export default function StudentNextSteps({ studentId, recommendations = [], history = [], onOpenPlan, onOpenEvidence, onOpenProgress }) {
  const [records, setRecords] = useState(null);
  const [evidence, setEvidence] = useState(null);
  const [error, setError] = useState('');
  const load = useCallback(async () => {
    if (!studentId) return;
    try {
      const [goals, items] = await Promise.all([getCoachingRecords(studentId), getStudentEvidence(studentId)]);
      setRecords(goals); setEvidence(items); setError('');
    } catch (err) { setRecords(null); setEvidence(null); setError(err?.message || 'Your activity could not be loaded.'); }
  }, [studentId]);
  useEffect(() => { load(); }, [load]);

  const active = (records || []).filter((item) => item.kind === 'goal' && item.status !== 'completed')
    .sort((a, b) => (a.due_date || '9999').localeCompare(b.due_date || '9999'));
  const suggestions = recommendations.filter((item) => !(records || []).some((record) => record.kind === 'goal' && record.title === item.title));
  const actions = [...active.map((item) => ({ title: item.title, date: item.due_date, suggested: false })),
    ...suggestions.map((item) => ({ title: item.title, suggested: true, days: item.suggested_days || 7 }))].slice(0, 3);
  const events = [
    ...history.map((item) => ({ key: `assessment-${item.id}`, date: item.created_at, label: `Assessment: ${item.readiness_score}/100`, open: onOpenProgress })),
    ...(records || []).filter((item) => item.kind === 'goal' && item.status === 'completed').map((item) => ({ key: `goal-${item.id}`, date: item.updated_at, label: `Goal completed: ${item.title}`, open: onOpenPlan })),
    ...(records || []).filter((item) => item.kind !== 'goal' && item.visibility === 'student').map((item) => ({ key: `mentor-${item.id}`, date: item.created_at, label: `Mentor update: ${item.title}`, open: onOpenPlan })),
    ...(evidence || []).map((item) => ({ key: `evidence-${item.id}`, date: item.submitted_at, label: `Evidence submitted: ${item.title}`, open: onOpenEvidence })),
  ].filter((item) => item.date).sort((a, b) => Date.parse(b.date) - Date.parse(a.date)).slice(0, 5);

  return <section className="glass-card next-steps" aria-labelledby="next-steps-title">
    <div className="card-header"><div><h2 id="next-steps-title">What should I do next?</h2><p>Your next actions and recent activity in one place.</p></div><button type="button" className="btn-preset" onClick={load}><RefreshCw size={14} aria-hidden="true" /> Refresh</button></div>
    <div className="card-body">
      {error && <p role="alert">{error} <button className="inline-retry" type="button" onClick={load}>Retry loading activity</button></p>}
      {records === null && !error && <p role="status">Loading your plan…</p>}
      {records !== null && (actions.length ? <div className="next-action-list">{actions.map((item, index) => <article className="next-action" key={`${item.title}-${index}`}><div><strong>{item.title}</strong><p>{item.suggested ? `Suggested: within ${item.days} days; add to your plan to set a due date` : item.date ? `Due ${formatDate(item.date)}` : 'No due date set'}</p></div><button type="button" className="btn-preset" onClick={onOpenPlan}>Open plan <ArrowRight size={14} aria-hidden="true" /></button></article>)}</div> : <p className="probability-note">No actions yet. Analyze your profile or add a goal to your plan.</p>)}
      <h3 className="panel-subheading">Recent activity</h3>
      {events.length ? <ul className="activity-timeline">{events.map((item) => <li key={item.key}><time>{formatDate(item.date)}</time><button type="button" className="mentor-link-button" onClick={item.open}>{item.label}</button></li>)}</ul> : <p className="probability-note">Your assessments, completed goals, evidence, and mentor updates will appear here.</p>}
      <p className="probability-note">Assessment comparisons show recorded input changes; they do not prove why a score changed.</p>
    </div>
  </section>;
}
