import React, { useCallback, useEffect, useState } from 'react';
import { CalendarDays, Plus } from 'lucide-react';
import { createCoachingRecord, getCoachingRecords, updateCoachingRecord } from '../services/assessmentService';

const CHECKLIST = [
  ['Contact information', 'Check that your contact details and professional links are current.'],
  ['Role-specific skills', 'Show relevant skills for your target role accurately.'],
  ['Projects and outcomes', 'Describe your contributions, tools and measurable results.'],
  ['Experience and dates', 'Check internships, education and dates for accuracy.'],
  ['Final review', 'Proofread the resume and ask a mentor or peer for feedback.'],
];
const PREFIX = 'Resume checklist: ';

export default function PreparationPlanner({ studentId, targetRole }) {
  const [records, setRecords] = useState([]); const [error, setError] = useState('');
  const [busy, setBusy] = useState(false); const [date, setDate] = useState(''); const [details, setDetails] = useState('');
  const refresh = useCallback(async () => { try { setRecords(await getCoachingRecords(studentId)); setError(''); } catch (err) { setError(err?.message || 'Preparation plan could not be loaded.'); } }, [studentId]);
  useEffect(() => { refresh(); }, [refresh]);
  const toggle = async (title, detail, record, checked) => {
    setBusy(true);
    try {
      if (record) await updateCoachingRecord(studentId, record.id, { status: checked ? 'completed' : 'open' });
      else { const created = await createCoachingRecord(studentId, { kind: 'goal', title: PREFIX + title, detail, visibility: 'student' }); if (checked) await updateCoachingRecord(studentId, created.id, { status: 'completed' }); }
      await refresh();
    } catch (err) { setError(err?.message || 'Checklist could not be saved.'); } finally { setBusy(false); }
  };
  const schedule = async (event) => {
    event.preventDefault(); if (!date) return; setBusy(true);
    try { await createCoachingRecord(studentId, { kind: 'goal', title: 'Interview practice', detail: details || `Practice for ${targetRole || 'your target role'} and record feedback.`, due_date: date, visibility: 'student' }); setDate(''); setDetails(''); await refresh(); }
    catch (err) { setError(err?.message || 'Practice could not be scheduled.'); } finally { setBusy(false); }
  };
  const practice = records.filter((record) => record.kind === 'goal' && record.title === 'Interview practice' && record.status !== 'completed');
  return <section className="glass-card preparation-planner" aria-labelledby="preparation-planner-heading"><div className="card-header"><div><h2 id="preparation-planner-heading">Resume and interview preparation</h2><p>Plan your preparation for {targetRole || 'your target role'}.</p></div></div><div className="card-body">
    {error && <p role="alert">{error} <button className="inline-retry" type="button" onClick={refresh}>Retry</button></p>}
    <h3 className="panel-subheading">Resume checklist</h3><div className="preparation-checklist">{CHECKLIST.map(([title, detail]) => { const record = records.find((item) => item.kind === 'goal' && item.title === PREFIX + title); return <label key={title}><input type="checkbox" checked={record?.status === 'completed'} disabled={busy} onChange={(event) => toggle(title, detail, record, event.target.checked)} /><span><strong>{title}</strong><small>{detail}</small></span></label>; })}</div>
    <div className="preparation-practice">
      <div className="preparation-practice-header">
        <span className="preparation-practice-icon"><CalendarDays size={19} aria-hidden="true" /></span>
        <div>
          <h3>Interview practice schedule</h3>
          <p>Set a personal practice goal. This does not book a meeting.</p>
        </div>
      </div>
      <form onSubmit={schedule} className="preparation-schedule">
        <label className="preparation-field">
          <span>Practice date <span className="preparation-required">*</span></span>
          <input type="date" required value={date} onChange={(event) => setDate(event.target.value)} />
        </label>
        <label className="preparation-field">
          <span>Practice plan <span className="preparation-optional">Optional</span></span>
          <input maxLength={2000} value={details} onChange={(event) => setDetails(event.target.value)} placeholder="e.g. Mock technical interview with a peer" />
        </label>
        <button className="preparation-add-button" type="submit" disabled={busy}><Plus size={17} aria-hidden="true" />{busy ? 'Saving…' : 'Add practice'}</button>
      </form>
      {practice.length > 0 && <ul className="activity-timeline">{practice.map((item) => <li key={item.id}><time>{item.due_date || 'No date'}</time><span>{item.detail || item.title}</span></li>)}</ul>}
    </div>
  </div></section>;
}
