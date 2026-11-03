import React, { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { ArrowRight, CalendarDays, CheckCircle2, ClipboardList, MessageSquare, RefreshCw, Shield, Users } from 'lucide-react';
import { getMentorStudents, createCoachingRecord, updateCoachingRecord, deleteCoachingRecord } from '../services/assessmentService';
import { MetricCard, SectionIntro, StatusBanner } from './ui';
import StudyResources from './StudyResources';
import CvReview from './CvReview';
import DeleteControl from './DeleteControl';

const STALE_DAYS = 45;
const LABELS = {
  cgpa: 'Academics', coding_score: 'Coding practice', technical_score: 'Technical skills',
  aptitude_score: 'Aptitude', communication_score: 'Communication', projects: 'Projects',
  internships: 'Internships', certifications: 'Certifications', backlogs: 'Backlogs',
};

function ageDays(dateText) {
  const value = Date.parse(dateText || '');
  return Number.isFinite(value) ? Math.max(0, Math.floor((Date.now() - value) / 86400000)) : Infinity;
}

function studentSignal(student) {
  const profile = student.profile || {};
  const completeness = Object.keys(LABELS).filter((key) => profile[key] !== null && profile[key] !== undefined).length;
  const days = ageDays(student.created_at);
  const followUp = student.coaching_records?.filter((item) => item.kind === 'check_in') || [];
  const lastContact = followUp[0]?.created_at;
  if (completeness < Object.keys(LABELS).length) return { label: 'Profile incomplete', reason: `${Object.keys(LABELS).length - completeness} assessment fields are missing`, action: 'Agree on a short profile completion plan.' };
  if (student.readiness_score < 50) return { label: 'Needs attention', reason: `Readiness rubric score is ${student.readiness_score}/100`, action: 'Review the top skill gap together and choose one weekly goal.' };
  if (student.previous_score !== null && student.previous_score !== undefined && student.readiness_score < student.previous_score) return { label: 'Score decreased', reason: `Down ${student.previous_score - student.readiness_score} points since the previous saved assessment`, action: 'Check what changed in the assessment inputs before recommending support.' };
  if (!lastContact || ageDays(lastContact) > 30) return { label: 'Check-in due', reason: lastContact ? `Last recorded check-in ${ageDays(lastContact)} days ago` : 'No mentor check-in recorded', action: 'Schedule a brief progress check-in.' };
  if (student.readiness_score >= 70 && student.readiness_score < 80) return { label: 'Interview preparation', reason: 'Near the project rubric’s readiness threshold', action: 'Review role fit and practise an interview scenario.' };
  if (days > STALE_DAYS) return { label: 'Assessment stale', reason: `Last assessment ${days} days ago`, action: 'Ask the student to refresh the assessment with current evidence.' };
  return { label: 'On track', reason: 'No urgent support signal detected', action: 'Recognize progress and agree on the next milestone.' };
}

function MentorOverviewComponent({ cohort, loading, error, onRetry, authorized, viewer }) {
  const [students, setStudents] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [detailTopic, setDetailTopic] = useState('profile');
  const [filter, setFilter] = useState('All students');
  const [roleFilter, setRoleFilter] = useState('All target roles');
  const [assignmentFilter, setAssignmentFilter] = useState('All permitted students');
  const [search, setSearch] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [recordType, setRecordType] = useState('goal');
  const [visibility, setVisibility] = useState('student');
  const [title, setTitle] = useState('');
  const [detail, setDetail] = useState('');
  const [dueDate, setDueDate] = useState('');

  const refresh = useCallback(async () => {
    if (!authorized) return;
    setBusy(true);
    try {
      const rows = await getMentorStudents();
      setStudents(rows);
      setSelectedId((current) => rows.some((row) => row.user_id === current) ? current : (rows[0]?.user_id ?? null));
      setNotice('');
    } catch (err) {
      setNotice(err?.message || 'The permitted mentee roster could not be loaded.');
    } finally { setBusy(false); }
  }, [authorized]);

  useEffect(() => { refresh(); }, [refresh]);

  const selected = students.find((student) => student.user_id === selectedId) || null;
  const openStudent = (id) => {
    setSelectedId(id);
    document.getElementById('mentor-detail')?.scrollIntoView?.({ behavior: 'smooth', block: 'start' });
  };
  const visible = useMemo(() => students.filter((student) => {
    const signal = studentSignal(student);
    const matchesFilter = (filter === 'All students' || signal.label === filter)
      && (roleFilter === 'All target roles' || (student.target_roles || [student.target_role]).includes(roleFilter));
    const term = search.trim().toLowerCase();
    const assigned = student.assigned_mentor?.id === viewer?.id;
    const matchesAssignment = assignmentFilter === 'All permitted students' || (assignmentFilter === 'Assigned to me' ? assigned : !assigned);
    return matchesFilter && matchesAssignment && (!term || `${student.display_name} ${student.username} ${student.cohort}`.toLowerCase().includes(term));
  }), [students, filter, roleFilter, search, assignmentFilter, viewer?.id]);
  const signalCounts = useMemo(() => students.reduce((counts, student) => {
    const label = studentSignal(student).label;
    counts[label] = (counts[label] || 0) + 1;
    return counts;
  }, {}), [students]);
  const records = students.flatMap((student) => student.coaching_records || []);
  const studentGoals = records.filter((item) => item.kind === 'goal');
  const completedGoals = studentGoals.filter((item) => item.status === 'completed').length;
  const checkIns = records.filter((item) => item.kind === 'check_in').length;
  const overdueGoals = studentGoals.filter((item) => item.due_date && item.due_date < new Date().toISOString().slice(0,10) && item.status !== 'completed').length;
  const queue = students.flatMap((student) => {
    const missing = Object.keys(LABELS).filter((key) => student.profile?.[key] == null).length;
    const today = new Date(); today.setHours(0, 0, 0, 0);
    const limit = new Date(today); limit.setDate(limit.getDate() + 7);
    const items = (student.coaching_records || []).flatMap((record) => {
      if (!record.due_date || record.status === 'completed') return [];
      const date = new Date(`${record.due_date}T00:00:00`);
      if (record.kind === 'goal' && date < today) return [{ student, label: `Overdue goal: ${record.title}`, date: record.due_date, topic: 'coaching' }];
      if (record.kind === 'check_in' && date >= today && date <= limit) return [{ student, label: `Upcoming meeting: ${record.title}`, date: record.due_date, topic: 'coaching' }];
      return [];
    });
    if (student.cv_status === 'pending') items.push({ student, label: 'CV awaiting review', date: null, topic: 'cv' });
    if (missing) items.push({ student, label: `Profile incomplete: ${missing} missing fields`, date: null, topic: 'profile' });
    return items;
  }).sort((a, b) => (a.date || '9999').localeCompare(b.date || '9999'));

  const submitRecord = async (event) => {
    event.preventDefault();
    if (!selected || !title.trim()) return;
    setBusy(true);
    try {
      await createCoachingRecord(selected.user_id, { kind: recordType, title, detail, due_date: dueDate || null, visibility: recordType === 'goal' ? 'student' : visibility });
      setTitle(''); setDetail(''); setDueDate('');
      setNotice('Coaching update saved to the shared student timeline.');
      await refresh();
    } catch (err) { setNotice(err?.message || 'Unable to save this update.'); }
    finally { setBusy(false); }
  };

  const setGoalStatus = async (item, status) => {
    try {
      await updateCoachingRecord(selected.user_id, item.id, { status });
      await refresh();
    } catch (err) { setNotice(err?.message || 'Unable to update the goal.'); }
  };

  if (!authorized) return <StatusBanner tone="warning" icon={<Shield size={16} aria-hidden="true" />}>Mentor analytics are available to authenticated staff accounts only.</StatusBanner>;

  return (
    <section className="staff-workspace mentor-workspace" aria-labelledby="mentor-heading">
      <div className="workspace-heading mentor-heading">
        <div><span className="mentor-eyebrow">STUDENT SUPPORT</span><h1 id="mentor-heading">Mentor workspace</h1><SectionIntro>Review your cohort and assigned students, prioritize supportive follow-ups, and keep goals and meeting notes on the shared student timeline.</SectionIntro></div>
        <button type="button" className="btn-preset" onClick={refresh} disabled={busy}><RefreshCw size={15} aria-hidden="true" /> Refresh</button>
      </div>
      {notice && <StatusBanner tone="warning">{notice}</StatusBanner>}
      {error && <StatusBanner tone="warning">{error}<button type="button" className="inline-retry" disabled={loading} onClick={() => onRetry?.({ force: true })}>Retry cohort analytics</button></StatusBanner>}
      <div className="progress-summary-grid mentor-metrics" aria-label="Cohort summary">
        <MetricCard label="My assigned assessed students" value={loading || busy ? '…' : students.filter((student) => student.assigned_mentor?.id === viewer?.id && student.readiness_score != null).length} />
        <MetricCard label="Profiles in cohort" value={cohort?.suppressed ? 'Suppressed' : cohort?.unique_profiles ?? 'Not available'} />
        <MetricCard label="Needs attention" value={signalCounts['Needs attention'] || 0} tone="warning" />
        <MetricCard label="Check-ins due" value={(signalCounts['Check-in due'] || 0) + (signalCounts['Assessment stale'] || 0)} tone="warning" />
        <MetricCard label="Goals completed" value={`${completedGoals}/${studentGoals.length}`} tone="success" />
        <MetricCard label="Overdue goals" value={overdueGoals} tone={overdueGoals ? 'warning' : 'success'} />
      </div>
      <section className="glass-card follow-up-queue" aria-labelledby="follow-up-heading"><div className="card-header"><div><h2 id="follow-up-heading">Follow-up queue</h2><p>Overdue goals, upcoming meetings, CV reviews, and incomplete profiles. Refresh to see new submissions.</p></div></div><div className="card-body">{busy ? <p role="status">Loading follow-ups…</p> : queue.length ? <div className="next-action-list">{queue.slice(0, 8).map((item, index) => <article className="next-action" key={`${item.student.user_id}-${item.label}-${index}`}><div><strong>{item.student.display_name}</strong><p>{item.label}{item.date ? ` · ${item.date}` : ''}</p></div><button type="button" className="btn-preset" onClick={() => { setDetailTopic(item.topic); openStudent(item.student.user_id); }}>Open student <ArrowRight size={14} aria-hidden="true" /></button></article>)}</div> : <p className="probability-note">No follow-ups are currently due.</p>}{queue.length > 8 && <p className="probability-note">Showing 8 of {queue.length} follow-ups. Use the student list below to find others.</p>}</div></section>
      <div className="mentor-layout">
        <section className="glass-card mentor-roster" aria-label="Assigned student roster">
          <div className="card-header"><div><span className="mentor-card-eyebrow">YOUR STUDENTS</span><h2><Users size={18} aria-hidden="true" /> Student overview</h2><p>Find a student and open their coaching profile.</p></div><span className="mentor-cohort-tag">{viewer?.cohort || cohort?.cohort || 'Assigned cohort'}</span></div>
          <div className="card-body">
            <div className="mentor-filters">
            <label className="mentor-field" htmlFor="assignment-filter"><span>Student group</span><select id="assignment-filter" className="number-input-field" value={assignmentFilter} onChange={(event) => setAssignmentFilter(event.target.value)}><option>All permitted students</option><option>Assigned to me</option><option>Other cohort students</option></select></label>
            <label className="mentor-field" htmlFor="mentee-search"><span>Find a student</span>
            <input id="mentee-search" className="number-input-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Name or student ID" />
            </label>
            <label className="mentor-field" htmlFor="mentee-filter"><span>Support signal</span>
            <select id="mentee-filter" className="number-input-field" value={filter} onChange={(event) => setFilter(event.target.value)}>
              {['All students','Needs attention','Score decreased','Profile incomplete','Check-in due','Assessment stale','Interview preparation','On track'].map((item) => <option key={item}>{item}</option>)}
            </select>
            </label>
            <label className="mentor-field" htmlFor="mentee-role-filter"><span>Target role</span>
            <select id="mentee-role-filter" className="number-input-field" value={roleFilter} onChange={(event)=>setRoleFilter(event.target.value)}>
              {['All target roles',...new Set(students.flatMap((item)=>item.target_roles?.length ? item.target_roles : (item.target_role && item.target_role!=='Not selected' ? [item.target_role] : [])))].map((item)=><option key={item}>{item}</option>)}
            </select>
            </label>
            </div>
            <div className="mentor-list-heading"><h3>Cohort and assigned students</h3><span>{visible.length} shown</span></div>
            {visible.length === 0 ? <p className="probability-note">{busy ? 'Loading your assigned cohort…' : 'No matching students with saved assessments.'}</p> : (
              <div className="table-container"><table className="students-table"><thead><tr><th>Student</th><th>Program / cohort</th><th>Target role</th><th>Score / signal</th><th>Trend</th></tr></thead><tbody>
                {visible.map((student) => { const signal = studentSignal(student); const delta = student.previous_score == null ? null : student.readiness_score - student.previous_score; return <tr key={student.user_id} className={student.user_id === selectedId ? 'mentor-selected-row' : ''}><td><button type="button" className="mentor-student-button" onClick={() => openStudent(student.user_id)} aria-pressed={student.user_id === selectedId}><strong>{student.display_name}</strong><small>{student.username}{student.assigned_mentor?.id === viewer?.id ? ' · Assigned to you' : ''}</small></button></td><td>{student.cohort || 'Not recorded'}</td><td>{(student.target_roles || [student.target_role]).filter(Boolean).join(', ') || 'Not selected'}</td><td><strong>{student.readiness_score == null ? 'Not assessed' : <>{student.readiness_score}<small> / 100</small></>}</strong><br /><span className="rec-badge">{signal.label}</span></td><td>{delta == null ? 'Baseline' : `${delta > 0 ? '+' : ''}${delta} pts`}</td></tr>; })}
              </tbody></table></div>
            )}
            <div className="mentor-section-heading"><div><span className="mentor-card-eyebrow">WHERE TO START</span><h3 className="panel-subheading">Prioritized support queue</h3><p>Signals to help you plan your next conversation.</p></div></div>
            <div className="mentor-queue">
            {visible.filter((student)=>studentSignal(student).label!=='On track').slice(0,8).map((student)=>{const signal=studentSignal(student);return <article className="rec-card mentor-queue-card" key={`queue-${student.user_id}`}><div className="rec-header"><span className="rec-badge">{signal.label}</span><span className="rec-priority">{student.created_at ? new Date(student.created_at).toLocaleDateString() : 'Not assessed'}</span></div><h4 className="rec-title">{student.display_name}</h4><p className="rec-details"><strong>Signal:</strong> {signal.reason}</p><p className="rec-details"><strong>Suggested follow-up:</strong> {signal.action}</p><button className="mentor-link-button" type="button" onClick={()=>openStudent(student.user_id)}>Open student profile <ArrowRight size={15} aria-hidden="true" /></button></article>;})}
            {visible.filter((student)=>studentSignal(student).label!=='On track').length === 0 && <p className="mentor-empty">No support signals for the current filters.</p>}
            </div>
            <p className="probability-note">Mentor activity: {checkIns} recorded check-ins and {completedGoals} completed goals. These indicators describe activity and progress; they do not establish that coaching caused a score change.</p>
            <div className="mentor-insights"><div className="mentor-section-heading"><div><span className="mentor-card-eyebrow">GROUP INSIGHTS</span><h3 className="panel-subheading">Cohort coaching signals</h3></div></div>
            {(cohort?.common_gaps || []).slice(0, 5).map((gap) => <p className="rec-details" key={gap.feature}><strong>{LABELS[gap.feature] || gap.feature}:</strong> {gap.profiles} students ({Math.round(gap.share * 100)}%) below the current model threshold. Consider a group practice session.</p>)}
            {cohort?.suppressed && <p className="probability-note">Aggregate results are hidden until this cohort meets the minimum group size ({cohort.minimum_group_size}).</p>}
            {!cohort?.suppressed && !cohort?.common_gaps?.length && <p className="probability-note">No group skill-gap data is available yet.</p>}
            </div>
          </div>
        </section>
        <section id="mentor-detail" className="glass-card mentee-detail" aria-label="Selected mentee detail">
          {!selected ? <div className="card-body"><h2>Mentee detail</h2><p className="probability-note">A student profile appears here after an assessed student is selected.</p></div> : <>
            <div className="card-header"><div><span className="mentor-card-eyebrow">SELECTED STUDENT</span><h2>{selected.display_name}</h2><p>{selected.username} · {selected.cohort || 'Unassigned cohort'} · Last assessment {selected.created_at ? new Date(selected.created_at).toLocaleDateString() : 'Not completed'}</p><p>Target roles: {(selected.target_roles || [selected.target_role]).filter(Boolean).join(', ') || 'Not selected'}</p></div><span className="rec-badge">{studentSignal(selected).label}</span></div>
            <div className="card-body">
              <nav className="mentor-detail-nav" aria-label="Student detail sections">
                {[['profile', 'Profile'], ['evidence', 'Student evidence'], ['cv', 'CV review'], ['resources', 'Study resources'], ['coaching', 'Goals & follow-up']].map(([id, label]) => <button key={id} type="button" className={`mentor-detail-tab${detailTopic === id ? ' is-active' : ''}`} aria-pressed={detailTopic === id} aria-controls={`mentor-detail-${id}`} onClick={() => setDetailTopic(id)}>{label}</button>)}
              </nav>
              <div id="mentor-detail-profile" className="mentor-detail-panel" hidden={detailTopic !== 'profile'}>
              <div className="progress-summary-grid"><MetricCard label="Readiness rubric" value={selected.readiness_score == null ? 'Not assessed' : `${selected.readiness_score}/100`} tone={selected.readiness_score >= 75 ? 'success' : 'warning'} /><MetricCard label="Level" value={selected.readiness_category} /><MetricCard label="Data confidence" value={Object.keys(LABELS).filter((key) => selected.profile?.[key] != null).length >= 7 ? 'Good coverage' : 'Limited'} tone="warning" /></div>
              <p className="probability-note">This estimate reflects the latest submitted profile. It is a learning-support signal, not a placement guarantee. Student inputs remain self-reported unless separately verified.</p>
              <h3 className="panel-subheading">Profile evidence and skill gaps</h3>
              <div className="table-container"><table className="students-table"><thead><tr><th>Area</th><th>Evidence</th><th>Signal</th></tr></thead><tbody>{Object.entries(LABELS).map(([key,label]) => { const value = selected.profile?.[key]; return <tr key={key}><td>{label}</td><td>{value == null ? 'Missing' : key === 'cgpa' ? `${value}/10` : key === 'backlogs' ? `${value} current` : `${value}${['projects','internships','certifications'].includes(key) ? ' recorded' : '/100'}`}</td><td>{value == null ? 'Needs update' : key === 'backlogs' ? (value > 0 ? 'Follow up' : 'Recorded') : 'Recorded'}</td></tr>; })}</tbody></table></div>
              </div>
              <div id="mentor-detail-evidence" className="mentor-detail-panel" hidden={detailTopic !== 'evidence'}>
              <h3 className="panel-subheading">Student-submitted evidence</h3>
              {(selected.evidence || []).length ? <div className="rec-list">{selected.evidence.map((item)=><article className="rec-card" key={item.id}><div className="rec-header"><span className="rec-badge">{item.evidence_type} · {item.verification_status}</span><span className="rec-priority">{new Date(item.submitted_at).toLocaleDateString()}</span></div><h4 className="rec-title">{item.title}</h4>{item.detail&&<p className="rec-details">{item.detail}</p>}{item.evidence_url&&<a href={item.evidence_url} target="_blank" rel="noreferrer">Review evidence link</a>}<p className="probability-note">Student-submitted. Only an administrator can mark evidence as verified.</p></article>)}</div> : <p className="probability-note">No project, internship, portfolio, or certification evidence has been submitted.</p>}
              </div>
              <div id="mentor-detail-cv" className="mentor-detail-panel" hidden={detailTopic !== 'cv'}>
              {detailTopic === 'cv' && <CvReview key={selected.user_id} studentId={selected.user_id} mentor onReviewed={(status) => setStudents((current) => current.map((student) => student.user_id === selected.user_id ? { ...student, cv_status: status } : student))} />}
              </div>
              <div id="mentor-detail-resources" className="mentor-detail-panel" hidden={detailTopic !== 'resources'}>
              <StudyResources key={selected.user_id} studentId={selected.user_id} canUpload viewer={viewer} students={students} />
              </div>
              <div id="mentor-detail-coaching" className="mentor-detail-panel" hidden={detailTopic !== 'coaching'}>
              <h3 className="panel-subheading"><ClipboardList size={16} aria-hidden="true" /> Action plan and mentor timeline</h3>
              {(selected.coaching_records || []).length === 0 ? <p className="probability-note">No goals or mentor contact have been recorded yet.</p> : <div className="rec-list">{selected.coaching_records.map((item) => <article className="rec-card" key={item.id}><div className="rec-header"><span className="rec-badge">{item.kind.replace('_',' ')} · {item.visibility === 'mentor' ? 'Mentor only' : 'Visible to student'}</span><span className="rec-priority">{new Date(item.created_at).toLocaleDateString()}{item.due_date ? ` · due ${item.due_date}` : ''}</span></div><h4 className="rec-title">{item.title}</h4>{item.detail && <p className="rec-details">{item.detail}</p>}{item.evidence_url && <a href={item.evidence_url} target="_blank" rel="noreferrer">Evidence link</a>}{item.kind === 'goal' && <label className="input-label">Status <select className="number-input-field" value={item.status} onChange={(event) => setGoalStatus(item,event.target.value)}><option value="open">Not started</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></label>}{item.author_id === viewer?.id && <DeleteControl label={`coaching record ${item.title}`} onDelete={async () => { await deleteCoachingRecord(selected.user_id, item.id); setStudents((current) => current.map((student) => student.user_id === selected.user_id ? { ...student, coaching_records: student.coaching_records.filter((entry) => entry.id !== item.id) } : student)); }} />}</article>)}</div>}
              <form className="rec-card mentor-record-form" onSubmit={submitRecord}>
                <h3 className="panel-subheading"><MessageSquare size={16} aria-hidden="true" /> Record follow-up or assign a goal</h3>
                <p>Keep a clear record of your next step with {selected.display_name}. Goals are visible to the student.</p>
                <div className="mentor-form-grid">
                <label className="mentor-field" htmlFor="record-type"><span>Record type</span><select id="record-type" className="number-input-field" value={recordType} onChange={(event) => setRecordType(event.target.value)}><option value="goal">Student goal</option><option value="check_in">Meeting / check-in</option><option value="referral">Referral</option><option value="note">Mentor note</option></select></label>
                <label className="mentor-field" htmlFor="record-title"><span>Title</span><input id="record-title" className="number-input-field" required maxLength={140} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Complete a timed SQL practice set" /></label>
                <label className="mentor-field mentor-form-wide" htmlFor="record-detail"><span>Details and follow-up</span><textarea id="record-detail" className="number-input-field" maxLength={2000} value={detail} onChange={(event) => setDetail(event.target.value)} rows={3} placeholder="Add notes or agree on the next step" /></label>
                <label className="mentor-field" htmlFor="record-due"><span>Follow-up date (optional)</span><input id="record-due" className="number-input-field" type="date" value={dueDate} onChange={(event) => setDueDate(event.target.value)} /></label>
                {recordType !== 'goal' && <label className="mentor-field" htmlFor="record-visibility"><span>Visibility</span><select id="record-visibility" className="number-input-field" value={visibility} onChange={(event) => setVisibility(event.target.value)}><option value="student">Visible to student</option><option value="mentor">Private to mentor team</option></select></label>}
                </div>
                <button className="btn-primary" type="submit" disabled={busy}><CalendarDays size={15} aria-hidden="true" /> Save to shared timeline</button>
              </form>
              </div>
            </div>
          </>}
        </section>
      </div>
      <StatusBanner tone="warning" icon={<CheckCircle2 size={16} aria-hidden="true" />}>Mentors can access their cohort and students individually assigned to them. Private notes are hidden from students.</StatusBanner>
    </section>
  );
}

export default memo(MentorOverviewComponent);
