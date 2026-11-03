import React, { memo, useCallback, useEffect, useState } from 'react';
import { CalendarDays, CheckCircle2, Plus, RefreshCw, Save } from 'lucide-react';
import { createCoachingRecord, getCoachingRecords, updateCoachingRecord, deleteCoachingRecord } from '../services/assessmentService';
import DeleteControl from './DeleteControl';

function RoadmapPanelComponent({ recommendations = [], studentId, assessmentDate }) {
  const [records, setRecords] = useState([]);
  const [error, setError] = useState('');
  const [title, setTitle] = useState('');
  const [detail, setDetail] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    if (!studentId) return;
    try { setRecords(await getCoachingRecords(studentId)); setError(''); }
    catch (err) { setError(err?.message || 'Saved action plans could not be loaded.'); }
  }, [studentId]);
  useEffect(() => { refresh(); }, [refresh]);

  const addAction = async (actionTitle, actionDetail, due = null) => {
    setBusy(true);
    try {
      await createCoachingRecord(studentId, { kind:'goal', title:actionTitle, detail:actionDetail, due_date:due, visibility:'student' });
      await refresh();
      return true;
    } catch (err) { setError(err?.message || 'This action could not be saved.'); return false; }
    finally { setBusy(false); }
  };

  const submitCustom = async (event) => {
    event.preventDefault();
    if (!title.trim()) return;
    if (await addAction(title, detail, dueDate || null)) { setTitle(''); setDetail(''); setDueDate(''); }
  };

  const patchRecord = async (record, changes) => {
    try { await updateCoachingRecord(studentId, record.id, changes); await refresh(); }
    catch (err) { setError(err?.message || 'The action could not be updated.'); }
  };

  const activeGoals = records.filter((record) => record.kind === 'goal');
  const completed = activeGoals.filter((record) => record.status === 'completed').length;
  const suggested = recommendations.filter((rec) => !activeGoals.some((record) => record.title === rec.title));
  const defaultDue = () => { const date = new Date(); date.setDate(date.getDate()+7); const month = String(date.getMonth()+1).padStart(2,'0'); const day = String(date.getDate()).padStart(2,'0'); return `${date.getFullYear()}-${month}-${day}`; };
  const preparationTasks = [
    ['Timed aptitude practice','Complete two timed quantitative, logical, or verbal practice sets and review incorrect answers.','https://www.indiabix.com/'],
    ['Coding assessment','Complete one timed coding assessment for your selected role and record the result.','https://www.hackerrank.com/'],
    ['Resume review','Review your resume for clear project outcomes, skills, links, and accurate dates.','https://www.ncs.gov.in/'],
    ['Mock interview','Schedule a mock interview with a mentor or peer; record one strength and one improvement.'],
    ['Communication practice','Practise a 90-second introduction and request feedback on clarity and structure.'],
    ['Group discussion practice','Join a practice discussion and reflect on listening, evidence, and turn-taking.'],
  ];

  return (
    <div className="student-roadmap">
      <div className="progress-summary-grid"><article className="metric-card"><span className="metric-card-label">Actions in plan</span><strong className="metric-card-value">{activeGoals.length}</strong></article><article className="metric-card metric-card-success"><span className="metric-card-label">Completed</span><strong className="metric-card-value">{completed}</strong></article><article className="metric-card metric-card-primary"><span className="metric-card-label">Progress</span><strong className="metric-card-value">{activeGoals.length ? `${Math.round(completed/activeGoals.length*100)}%` : '—'}</strong></article></div>
      {error && <div className="status-banner status-banner-warning" role="status">{error}<button className="inline-retry" type="button" onClick={refresh}><RefreshCw size={14} aria-hidden="true" /> Retry</button></div>}
      <h3 className="panel-subheading">Your action plan</h3>
      {activeGoals.length === 0 ? <p className="probability-note">Save one or two focused actions. Completing a resource does not automatically change your readiness result; reassess with evidence.</p> : <div className="rec-list">{activeGoals.map((record)=><article className="rec-card" key={record.id}><div className="rec-header"><span className="rec-badge">{record.status === 'completed' ? 'Completed' : record.status === 'in_progress' ? 'In progress' : 'Not started'}</span><span className="rec-priority">{record.due_date ? `Due ${record.due_date}` : 'No due date'}</span></div><h4 className="rec-title">{record.title}</h4>{record.detail && <p className="rec-details">{record.detail}</p>}<label className="input-label">Action status<select className="number-input-field" value={record.status} onChange={(event)=>patchRecord(record,{status:event.target.value})}><option value="open">Not started</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></label><EvidenceLink record={record} onSave={(evidence_url)=>patchRecord(record,{evidence_url})} />{record.author_id === studentId && <DeleteControl label={`goal ${record.title}`} onDelete={async () => { await deleteCoachingRecord(studentId, record.id); setRecords((current) => current.filter((item) => item.id !== record.id)); }} />}</article>)}</div>}
      {suggested.length > 0 && <><h3 className="panel-subheading">Recommended next actions</h3><p className="probability-note">Showing up to three priorities. Reassess after completing an action; the score is not guaranteed to change.</p><div className="rec-list">{suggested.slice(0,3).map((rec)=><article className="rec-card" key={rec.title}><div className="rec-header"><span className="rec-badge">{rec.badge || 'From this assessment'}</span><span className={`rec-priority ${rec.priority || ''}`}>{rec.priority || 'Suggested'} priority</span></div><h4 className="rec-title">{rec.title}</h4><p className="rec-details"><strong>Gap / interpretation:</strong> {rec.details}</p><p className="rec-details"><strong>Evidence:</strong> {rec.evidence || `Profile area: ${rec.target_feature || 'overall readiness'}`}{assessmentDate ? ` · Latest assessment ${new Date(assessmentDate).toLocaleDateString()}` : ''}</p><p className="rec-details"><strong>Effort:</strong> About {rec.effort_hours || 3} hours · <strong>Suggested due date:</strong> {new Date(new Date().setDate(new Date().getDate() + (rec.suggested_days || 7))).toLocaleDateString()}</p><ul className="rec-actions-list">{(rec.action_items || []).slice(0,3).map((item)=><li key={item}><span className="rec-bullet" aria-hidden="true">▸</span><span>{item}</span></li>)}</ul><p className="probability-note"><strong>Progress check:</strong> {rec.progress_measure || 'Review with your mentor and reassess after the action.'}</p><button className="btn-primary" type="button" disabled={busy} onClick={()=>addAction(rec.title,[rec.details,rec.evidence&&`Evidence: ${rec.evidence}`,rec.action_items?.slice(0,3).join(' '),`Estimated effort: about ${rec.effort_hours || 3} hours.`, `Progress check: ${rec.progress_measure || 'Review with a mentor and reassess.'}`].filter(Boolean).join(' '),defaultDue())}><Plus size={15} aria-hidden="true" /> Add to my plan · 1 week</button></article>)}</div></>}
      <form className="rec-card" onSubmit={submitCustom}><h3 className="panel-subheading"><Plus size={16} aria-hidden="true" /> Add a personal goal</h3><label className="input-label" htmlFor="personal-goal-title">Goal</label><input id="personal-goal-title" className="number-input-field" required maxLength={140} value={title} onChange={(event)=>setTitle(event.target.value)} placeholder="e.g. Complete a mock interview" /><label className="input-label" htmlFor="personal-goal-detail">Plan and progress measure</label><textarea id="personal-goal-detail" className="number-input-field" rows={3} maxLength={2000} value={detail} onChange={(event)=>setDetail(event.target.value)} placeholder="What will you do, and how will you show completion?" /><label className="input-label" htmlFor="personal-goal-date">Due date</label><input id="personal-goal-date" className="number-input-field" type="date" value={dueDate} onChange={(event)=>setDueDate(event.target.value)} onInput={(event)=>setDueDate(event.currentTarget.value)} /><button type="submit" className="btn-primary" disabled={busy}><CalendarDays size={15} aria-hidden="true" /> Save goal</button></form>
      <details className="rec-card"><summary className="rec-summary"><strong>Preparation library</strong><span className="rec-toggle">Add a practice goal</span></summary><p className="probability-note">These are preparation activities, not automatic score boosts. Add a task to your plan, complete it, and then reassess.</p>{preparationTasks.map(([task,description,url])=><div className="rec-header" key={task}><span><strong>{task}</strong><br /><small>{description}</small>{url&&<><br/><a href={url} target="_blank" rel="noreferrer">Open practice resource</a></>}</span><button type="button" className="btn-preset" disabled={busy || activeGoals.some((item)=>item.title===task)} onClick={()=>addAction(task,description,defaultDue())}><Plus size={14} aria-hidden="true" /> Add</button></div>)}</details>
      <p className="probability-note"><CheckCircle2 size={14} aria-hidden="true" /> Your actions are saved to the shared account record so an authorized mentor can follow progress. Only you and permitted staff can access them.</p>
    </div>
  );
}

function EvidenceLink({ record, onSave }) {
  const [url, setUrl] = useState(record.evidence_url || '');
  useEffect(()=>setUrl(record.evidence_url || ''),[record.evidence_url]);
  return <form className="evidence-form" onSubmit={(event)=>{event.preventDefault();onSave(url);}}><label className="input-label" htmlFor={`evidence-${record.id}`}>Evidence link (optional)</label><input id={`evidence-${record.id}`} className="number-input-field" type="url" maxLength={500} value={url} onChange={(event)=>setUrl(event.target.value)} placeholder="https://…" /><button className="btn-primary evidence-save-button" type="submit"><Save size={15} aria-hidden="true" /> Save evidence</button></form>;
}

export default memo(RoadmapPanelComponent);
