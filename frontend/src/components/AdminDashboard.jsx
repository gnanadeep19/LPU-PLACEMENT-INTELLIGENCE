import React, { memo, useCallback, useEffect, useMemo, useState } from 'react';
import { BarChart3, Download, RefreshCw, ShieldCheck, Users } from 'lucide-react';
import { getCohortAnalytics, getMentorStudents, getPlacementPipeline, getPlacementSummary, getModelInfo, getProfileCorrections, resolveProfileCorrection, savePlacementStage, verifyStudentEvidence, deletePlacementRecord } from '../services/assessmentService';
import { get } from '../services/apiClient';
import { MetricCard, SectionIntro, StatusBanner } from './ui';
import canonicalEvaluation from '../../../reports/model-evaluation/canonical_evaluation.json';
import AdminMentorProgram from './AdminMentorProgram';
import PipelineFilters from './PipelineFilters';
import PlacementRoleCompanyFields from './PlacementRoleCompanyFields';
import AdminMentorDirectory from './AdminMentorDirectory';
import AdminMentorAssignments from './AdminMentorAssignments';
import DeleteControl from './DeleteControl';
import PlacementHistory from './PlacementHistory';
import CohortBreakdown from './CohortBreakdown';

const STAGES = ['Eligible','Preparing','Applied','Shortlisted','Interviewing','Offered','Placed','Opted out'];
const FIELDS = { cgpa:'Academics',technical_score:'Technical skills',aptitude_score:'Aptitude',communication_score:'Communication',coding_score:'Coding',projects:'Projects',internships:'Internships',certifications:'Certifications',backlogs:'Backlogs' };
const fieldValue = (profile, key) => profile?.[key];

function AdminDashboardComponent({ authorized, viewer, cohort: passedCohort, loading: passedLoading, error: passedError, onRetry }) {
  const [tab, setTab] = useState('Overview');
  const [cohort, setCohort] = useState(passedCohort || null);
  const [students, setStudents] = useState([]);
  const [rosterLoaded, setRosterLoaded] = useState(false);
  const [placements, setPlacements] = useState([]);
  const [placementSummary, setPlacementSummary] = useState(null);
  const [model, setModel] = useState(null);
  const [audit, setAudit] = useState([]);
  const [auditError, setAuditError] = useState('');
  const [auditLoading, setAuditLoading] = useState(false);
  const [corrections, setCorrections] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState('All cohorts');
  const [pipelineRole, setPipelineRole] = useState('All roles');
  const [pipelineCompany, setPipelineCompany] = useState('All companies');
  const [pipelineCohort, setPipelineCohort] = useState('All cohorts');
  const [selected, setSelected] = useState(null);
  const [placementForm, setPlacementForm] = useState({ stage: 'Preparing', company: '', target_role: '' });

  const refresh = useCallback(async () => {
    if (!authorized) return;
    setBusy(true); setError('');
    const requests = [getCohortAnalytics().then(setCohort)];
    const needsRoster = ['Overview','Data quality','Placement pipeline','Mentor program'].includes(tab);
    if (needsRoster) requests.push(getMentorStudents().then((data) => { setStudents(data); setRosterLoaded(true); }).catch((err) => { setStudents([]); setRosterLoaded(false); throw err; }));
    else { setStudents([]); setSelected(null); setRosterLoaded(false); }
    if (tab === 'Overview') requests.push(getPlacementSummary().then(setPlacementSummary));
    if (tab === 'Placement pipeline') requests.push(getPlacementPipeline().then(setPlacements));
    if (tab === 'Model monitoring') requests.push(getModelInfo().then(setModel));
    if (tab === 'Data quality' && viewer?.role === 'admin') requests.push(getProfileCorrections().then(setCorrections).catch((err) => { setCorrections(null); throw err; }));
    if (tab !== 'Placement pipeline') setPlacements([]);
    const results = await Promise.allSettled(requests);
    const failures = results.filter((item) => item.status === 'rejected');
    if (failures.length) setError(failures.map((item) => item.reason?.message || 'Some admin data could not be loaded.').join(' '));
    setBusy(false);
  }, [authorized, tab, viewer?.role]);

  useEffect(() => { refresh(); }, [refresh]);
  useEffect(() => { setFilter('All cohorts'); }, [tab]);
  const loadAudit = useCallback(async () => {
    setAuditLoading(true); setAuditError('');
    try { const response = await get('/staff/audit'); setAudit(response?.data || []); }
    catch (err) { setAudit([]); setAuditError(err?.message || 'Audit history could not be loaded.'); }
    finally { setAuditLoading(false); }
  }, []);
  useEffect(() => { if (authorized && viewer?.role === 'admin' && tab === 'Access and audit') loadAudit(); }, [authorized, viewer?.role, tab, loadAudit]);

  const cohorts = useMemo(() => ['All cohorts', ...new Set(students.map((item) => item.cohort).filter(Boolean))], [students]);
  const visibleStudents = useMemo(() => students.filter((item) => filter === 'All cohorts' || item.cohort === filter), [students, filter]);
  const roleSummary = useMemo(() => [...new Set(students.flatMap((item)=>item.target_roles?.length ? item.target_roles : (item.target_role && item.target_role!=='Not selected' ? [item.target_role] : [])))].map((role)=>{const rows=students.filter((item)=>(item.target_roles || [item.target_role]).includes(role));return {role,count:rows.length,average:Math.round(rows.reduce((sum,item)=>sum+item.readiness_score,0)/rows.length)};}),[students]);
  const coverage = useMemo(() => {
    if (!visibleStudents.length) return { complete: 0, stale: 0, missing: 0 };
    let complete = 0; let stale = 0; let missing = 0;
    visibleStudents.forEach((item) => {
      const profile = item.profile || {};
      const absent = Object.keys(FIELDS).filter((key) => fieldValue(profile,key) == null).length;
      if (absent === 0) complete += 1;
      missing += absent;
      if (Date.now() - Date.parse(item.created_at) > 45 * 86400000) stale += 1;
    });
    return { complete: Math.round((complete / visibleStudents.length) * 100), stale, missing };
  }, [visibleStudents]);
  const placementsByStage = useMemo(() => STAGES.map((stage) => ({ stage, count: placements.filter((item) => item.stage === stage).length })), [placements]);
  const visiblePlacements = useMemo(() => placements.filter((item)=>(pipelineRole==='All roles'||item.target_role===pipelineRole)&&(pipelineCompany==='All companies'||item.company===pipelineCompany)&&(pipelineCohort==='All cohorts'||item.cohort===pipelineCohort)),[placements,pipelineRole,pipelineCompany,pipelineCohort]);
  const evidenceRows = visibleStudents.flatMap((student)=>(student.evidence||[]).map((item)=>({...item,student_name:student.display_name,student_id:student.user_id,cohort:student.cohort})));
  const coaching = useMemo(() => {
    const records = students.flatMap((student) => student.coaching_records || []);
    const goals = records.filter((record) => record.kind === 'goal');
    const today = new Date().toISOString().slice(0,10);
    return {
      studentsWithCheckIn: new Set(records.filter((record)=>record.kind==='check_in').map((record)=>record.student_id)).size,
      goals: goals.length,
      completed: goals.filter((record)=>record.status==='completed').length,
      overdue: goals.filter((record)=>record.due_date && record.due_date < today && record.status!=='completed').length,
    };
  }, [students]);

  const savePlacement = async (event) => {
    event.preventDefault();
    if (!selected) return;
    try {
      await savePlacementStage({ student_id: selected.user_id, ...placementForm });
      await refresh();
    } catch (err) { setError(err?.message || 'Placement stage could not be saved.'); }
  };

  const reviewEvidence = async (studentId,evidenceId,status) => {
    try { await verifyStudentEvidence(studentId,evidenceId,status); await refresh(); }
    catch (err) { setError(err?.message || 'Evidence review could not be saved.'); }
  };

  const reviewCorrection = async (item, status) => {
    try {
      const resolution = status === 'reviewed'
        ? 'Reviewed. Update the profile through an approved source, then run a new assessment.'
        : 'Request declined. Contact the placement office if you need to provide more information.';
      await resolveProfileCorrection(item.id, status, resolution);
      await refresh();
    } catch (err) { setError(err?.message || 'The correction request could not be updated.'); }
  };

  const exportSummary = () => {
    const rows = [['Metric','Value'],['Students assessed',cohort?.unique_profiles ?? 'Suppressed'],['Average readiness',cohort?.average_readiness_score ?? 'Not available'],['Complete profile coverage (%)','Open the data-quality view for this measure'],...Object.entries(placementSummary?.stages || {}).map(([stage,count]) => [`Placement stage: ${stage}`,count])];
    const csv = rows.map((row) => row.map((value) => `"${String(value).replaceAll('"','""')}"`).join(',')).join('\r\n');
    const url = URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8'}));
    const anchor = document.createElement('a'); anchor.href=url; anchor.download='placement-cohort-summary.csv'; anchor.click(); URL.revokeObjectURL(url);
  };

  if (!authorized) return <StatusBanner tone="warning"><ShieldCheck size={16} aria-hidden="true" /> Admin analytics require an authenticated administrator or placement-officer account.</StatusBanner>;
  const distribution = cohort?.readiness_distribution || {};
  const minimumGroupSize = cohort?.minimum_group_size || 5;
  const modelMetrics = model?.metrics || model?.calibration_metrics || {};

  return (
    <section className="admin-workspace" aria-labelledby="admin-heading">
      <div className="workspace-heading"><div><h1 id="admin-heading">Placement program overview</h1><SectionIntro>Monitor cohort readiness, preparation coverage, actual placement stages, data quality, and model evaluation in one place.</SectionIntro></div><div className="card-actions"><button type="button" className="btn-preset" onClick={refresh} disabled={busy}><RefreshCw size={15} aria-hidden="true" /> Refresh</button><button type="button" className="btn-preset" onClick={exportSummary}><Download size={15} aria-hidden="true" /> Export aggregate summary</button></div></div>
      {(error || passedError) && <StatusBanner tone="warning">{error || passedError}</StatusBanner>}
      {passedLoading && <p className="probability-note">Loading cohort analytics…</p>}
      <nav className="tabs-nav" aria-label="Admin sections">{['Overview','Placement pipeline','Data quality','Mentor program',...(viewer?.role === 'admin' ? ['Mentor assignments', 'Mentor users', 'Student users'] : []),'Model monitoring','Access and audit'].map((label) => <button className={`tab-btn ${tab === label ? 'active' : ''}`} type="button" key={label} onClick={() => setTab(label)} aria-pressed={tab === label}>{label}</button>)}</nav>

      {tab === 'Overview' && <>
        <div className="progress-summary-grid overview-metrics"><MetricCard label="Assessed profiles" value={cohort?.suppressed ? 'Suppressed' : cohort?.unique_profiles ?? 'Not available'} /><MetricCard label="Average readiness rubric" value={cohort?.average_readiness_score == null ? 'Not available' : `${cohort.average_readiness_score}/100`} tone="warning" /><MetricCard label="Placement outcomes recorded" value={placementSummary?.suppressed ? 'Suppressed' : placementSummary?.total ?? 'Not available'} /><MetricCard label="Profiles with target met" value={cohort?.suppressed ? 'Suppressed' : distribution['Placement Ready'] ?? 0} tone="success" /></div>
        <p className="probability-note overview-definitions">Definitions: assessed profiles are unique active student accounts with a saved assessment; average readiness uses those profiles only; placement stages count students with a manually recorded stage; “target met” counts model rubric labels and is not a placement outcome. Small cohorts are suppressed.</p>
        {cohort?.suppressed && <StatusBanner tone="warning">Cohort aggregate details are suppressed until at least {cohort.minimum_group_size} assessed profiles are available.</StatusBanner>}
        <section className="glass-card overview-stage-summary"><div className="card-header"><div><h2>Placement stage summary</h2><p>Actual records are separate from readiness estimates.</p></div></div><div className="card-body">{placementSummary?.suppressed ? <p className="admin-empty-state">Placement stage counts are hidden until this view reaches the minimum group size.</p> : placementSummary ? <div className="progress-summary-grid">{STAGES.map((stage)=><MetricCard key={stage} label={stage} value={placementSummary.stages?.[stage] ?? 0} tone={stage==='Placed'?'success':'primary'} />)}</div> : <p className="admin-empty-state">Placement stage summary is not available yet.</p>}</div></section>
        <div className="mentor-layout overview-panels"><section className="glass-card"><div className="card-header"><div><h2><BarChart3 size={17} aria-hidden="true" /> Readiness distribution</h2><p>Prediction rubric distribution; actual placement outcomes are shown separately.</p></div></div><div className="card-body">{Object.entries(distribution).length ? Object.entries(distribution).map(([level,count]) => <p className="rec-details" key={level}><strong>{level}</strong><span> · {count} students</span></p>) : <p className="probability-note">No publishable cohort distribution yet.</p>}<h3 className="panel-subheading">Most common gaps</h3>{(cohort?.common_gaps || []).slice(0,8).map((gap) => <p className="rec-details" key={gap.feature}><strong>{FIELDS[gap.feature] || gap.feature}</strong> — {gap.profiles} of assessed profiles ({Math.round(gap.share * 100)}%) are below the model target.</p>)}</div></section>
          <section className="glass-card"><div className="card-header"><div><h2><Users size={17} aria-hidden="true" /> Cohort and role breakdown</h2><p>Individual records load only when you open a detail view.</p></div></div><div className="card-body"><CohortBreakdown students={students} loading={busy} loaded={rosterLoaded} minimum={minimumGroupSize} /></div></section></div>
      </>}

      {tab === 'Placement pipeline' && <section className="glass-card admin-placement-pipeline"><div className="card-header"><div><h2>Actual placement stages</h2><p>Recorded placement outcomes are separate from readiness estimates.</p></div></div><div className="card-body"><PipelineFilters placements={placements} cohort={pipelineCohort} setCohort={setPipelineCohort} role={pipelineRole} setRole={setPipelineRole} company={pipelineCompany} setCompany={setPipelineCompany} /><div className="progress-summary-grid">{STAGES.map((stage)=><MetricCard key={stage} label={stage} value={visiblePlacements.filter((item)=>item.stage===stage).length} tone={stage==='Placed'?'success':'primary'} />)}</div><div className="table-container"><table className="students-table"><thead><tr><th>Student</th><th>Cohort</th><th>Role / company</th><th>Stage</th><th>Updated</th><th>Actions</th></tr></thead><tbody>{!busy && !visiblePlacements.length && <tr><td colSpan={6} className="admin-empty-cell">No placement records match these filters.</td></tr>}{visiblePlacements.map((item) => <tr key={item.student_id}><td>{item.display_name} ({item.username})</td><td>{item.cohort || '—'}</td><td>{item.target_role || '—'}{item.company ? ` · ${item.company}` : ''}</td><td>{item.stage}</td><td>{new Date(item.updated_at).toLocaleDateString()}</td><td><PlacementHistory studentId={item.student_id} name={item.display_name} /><DeleteControl label={`placement record for ${item.display_name}`} explanation="This removes the manually recorded placement stage." onDelete={async () => { await deletePlacementRecord(item.student_id); setPlacements((current) => current.filter((entry) => entry.student_id !== item.student_id)); }} /></td></tr>)}</tbody></table></div><h3 className="panel-subheading">Update a placement record</h3><div className="placement-student-field"><label htmlFor="placement-student">Student</label><select className="number-input-field" id="placement-student" value={selected?.user_id || ''} onChange={(event)=>setSelected(students.find((item)=>item.user_id===Number(event.target.value)) || null)}><option value="">Choose student</option>{visibleStudents.map((item)=><option key={item.user_id} value={item.user_id}>{item.display_name} · {item.cohort}</option>)}</select></div><form className="placement-edit-form" onSubmit={savePlacement}><label className="input-label">Stage<select className="number-input-field" value={placementForm.stage} onChange={(event)=>setPlacementForm({...placementForm,stage:event.target.value})}>{STAGES.map((stage)=><option key={stage}>{stage}</option>)}</select></label><PlacementRoleCompanyFields form={placementForm} setForm={setPlacementForm} placements={placements} /><button className="placement-save-button" type="submit" disabled={!selected}>Save placement update</button></form><p className="probability-note">Only placement officers and administrators can edit outcomes. This project uses manually recorded events; verify outcomes with official placement records.</p></div></section>}

      {tab === 'Data quality' && <section className="glass-card admin-data-quality"><div className="card-header"><div><h2>Data coverage and quality</h2><p>Coverage denominators use active students with a saved assessment in the selected cohort.</p></div><label className="input-label">Cohort<select className="number-input-field" value={filter} onChange={(event)=>setFilter(event.target.value)}>{cohorts.map((item)=><option key={item}>{item}</option>)}</select></label></div><div className="card-body"><div className="progress-summary-grid"><MetricCard label="Complete 9-field profiles" value={`${coverage.complete}%`} tone={coverage.complete >= 80 ? 'success' : 'warning'} /><MetricCard label="Missing field entries" value={coverage.missing} tone="warning" /><MetricCard label="Assessments older than 45 days" value={coverage.stale} tone="warning" /><MetricCard label="Evidence awaiting review" value={evidenceRows.filter((item)=>item.verification_status==='pending').length} tone="warning" /></div><p className="probability-note">Denominator: {visibleStudents.length} assessed student profiles. Missing fields measure evidence coverage, not student ability.</p><div className="table-container"><table className="students-table"><thead><tr><th>Profile</th><th>Missing or stale inputs</th><th>Last assessment</th></tr></thead><tbody>{!busy && !visibleStudents.length && <tr><td colSpan={3} className="admin-empty-cell">No assessed profiles are available for this cohort.</td></tr>}{visibleStudents.map((item)=>{const missing=Object.keys(FIELDS).filter((key)=>fieldValue(item.profile,key)==null);const old=Date.now()-Date.parse(item.created_at)>45*86400000;return <tr key={item.user_id}><td>{item.display_name} · {item.cohort}</td><td>{missing.length ? missing.map((key)=>FIELDS[key]).join(', ') : 'No required model fields missing'}{old ? ' · Stale assessment' : ''}</td><td>{new Date(item.created_at).toLocaleDateString()}</td></tr>;})}</tbody></table></div><h3 className="panel-subheading">Submitted evidence review</h3><div className="table-container"><table className="students-table"><thead><tr><th>Student</th><th>Type / title</th><th>Evidence</th><th>Review status</th></tr></thead><tbody>{!busy && !evidenceRows.length && <tr><td colSpan={4} className="admin-empty-cell">No evidence has been submitted for this cohort.</td></tr>}{evidenceRows.map((item)=><tr key={item.id}><td>{item.student_name} · {item.cohort}</td><td>{item.evidence_type}: {item.title}</td><td>{item.evidence_url?<a href={item.evidence_url} target="_blank" rel="noreferrer">Open</a>:'No link'}</td><td>{viewer?.role==='admin'?<select className="number-input-field" value={item.verification_status} onChange={(event)=>reviewEvidence(item.student_id,item.id,event.target.value)}><option value="pending">Pending</option><option value="verified">Verified</option><option value="rejected">Rejected</option></select>:item.verification_status}</td></tr>)}</tbody></table></div>{viewer?.role==='admin' && <><h3 className="panel-subheading">Student correction requests</h3>{corrections === null ? <p className="admin-empty-state">{busy ? 'Loading correction requests…' : 'Correction requests could not be loaded. Check the connection and refresh.'}</p> : corrections.length ? <div className="rec-list">{corrections.map((item)=><article className="rec-card" key={item.id}><div className="rec-header"><strong>{item.field_name}</strong><span className="rec-badge">{item.status}</span></div><p><strong>Student ID:</strong> {item.student_id} · <strong>Submitted:</strong> {new Date(item.submitted_at).toLocaleDateString()}</p><p className="rec-details">Current: {item.current_value || 'Not provided'} · Requested: {item.requested_value}</p><p className="rec-details">Reason: {item.reason}</p>{item.resolution && <p className="probability-note">Response: {item.resolution}</p>}{item.status==='open' && <div className="admin-card-actions"><button type="button" className="btn-preset" onClick={()=>reviewCorrection(item,'reviewed')}>Mark reviewed</button><button type="button" className="btn-preset" onClick={()=>reviewCorrection(item,'declined')}>Decline</button></div>}</article>)}</div> : <p className="probability-note">No profile correction requests are awaiting review.</p>}</>}<p className="probability-note">URL format is checked on submission, but link reachability and content are not automatically validated. This release cannot detect duplicate profiles or imported-source provenance. Student input is self-reported until an authorized administrator reviews evidence.</p></div></section>}

      {tab === 'Mentor program' && <AdminMentorProgram students={students} filter={filter} setFilter={setFilter} loading={busy} rosterLoaded={rosterLoaded} />}
      {tab === 'Mentor users' && viewer?.role === 'admin' && <AdminMentorDirectory />}
      {tab === 'Mentor assignments' && viewer?.role === 'admin' && <AdminMentorAssignments />}
      {tab === 'Student users' && viewer?.role === 'admin' && <AdminMentorDirectory kind="student" />}
      {tab === 'Model monitoring' && <section className="glass-card admin-model-monitor"><div className="card-header"><div><h2>Model evaluation and monitoring</h2><p>Metrics are shown with the model metadata returned by the API.</p></div></div><div className="card-body">{model ? <><div className="progress-summary-grid model-monitor-metrics"><MetricCard label="Model version" value={model.model_version || 'Unspecified'} /><MetricCard label="Last trained" value={model.trained_at ? new Date(model.trained_at).toLocaleDateString() : 'Not reported'} /><MetricCard label="Holdout test rows" value={modelMetrics.test_rows ?? 'Not reported'} /><MetricCard label="Holdout accuracy" value={typeof modelMetrics.accuracy === 'number' ? `${(modelMetrics.accuracy*100).toFixed(1)}%` : 'Not reported'} /></div><p className="probability-note">Target label: <strong>{canonicalEvaluation.dataset.target}</strong>. Its real-world meaning is unverified. Active-artifact holdout details are separate from the historical model comparison below.</p><details className="model-details"><summary>Active artifact evaluation details</summary><pre className="model-metrics-json">{JSON.stringify(modelMetrics,null,2)}</pre></details><h3 className="panel-subheading">Historical baseline comparison</h3><p className="probability-note">The report uses {canonicalEvaluation.dataset.rows} rows from the project dataset and {canonicalEvaluation.evaluation.total_splits} repeated stratified folds. Values are mean ± fold standard deviation, not confidence intervals. The reported model-selection winner and this active artifact may differ.</p><div className="table-container"><table className="students-table"><caption className="sr-only">Historical model comparison across repeated folds</caption><thead><tr><th>Model</th><th>Accuracy (mean ± SD)</th><th>F1 (mean ± SD)</th><th>ROC-AUC (mean ± SD)</th></tr></thead><tbody>{Object.entries(canonicalEvaluation.models).map(([name,result])=><tr key={name}><th scope="row">{name.replaceAll('_',' ')}</th><td>{(result.mean.accuracy*100).toFixed(1)}% ± {(result.std.accuracy*100).toFixed(1)}</td><td>{(result.mean.f1*100).toFixed(1)}% ± {(result.std.f1*100).toFixed(1)}</td><td>{(result.mean.roc_auc*100).toFixed(1)}% ± {(result.std.roc_auc*100).toFixed(1)}</td></tr>)}</tbody></table></div><details className="model-details"><summary>Calibration details</summary><pre className="model-metrics-json">{JSON.stringify(model.calibration_metrics || model.calibration || { status:'Not reported for the active model artifact' },null,2)}</pre></details><p className="probability-note">External validation on LPU-representative students, calibrated uncertainty intervals, approved subgroup errors, and drift monitoring remain unavailable. The project evaluation report documents two exact duplicates removed from 253 and unverified data provenance/label construction. These small-dataset results do not establish generalization to LPU placements.</p></> : <p className="probability-note">Model metadata is not available. Refresh or check the API connection.</p>}</div></section>}

      {tab === 'Access and audit' && <section className="glass-card admin-access-audit"><div className="card-header"><div><h2><ShieldCheck size={17} aria-hidden="true" /> Access and audit</h2><p>Roles and server-enforced data access</p></div></div><div className="card-body"><ul className="rec-actions-list"><li>Students can read their own records and update their own goals.</li><li>Mentors can view students in their cohort and individually assigned students.</li><li>Placement officers can view institution analytics and update actual placement stages.</li><li>Administrators can view institution-wide analytics, model metadata, and the access audit.</li><li>Private mentor notes are hidden from students; all sensitive reads and writes are recorded.</li></ul><p className="probability-note">Use synthetic or anonymized profiles in a public demo. This local SQLite prototype is not connected to LPU single sign-on, institutional retention policy, or a consent-management service.</p>{viewer?.role === 'admin' && <><h3 className="panel-subheading">Recent access and record changes</h3>{auditLoading ? <p role="status">Loading audit history…</p> : auditError ? <p role="alert">{auditError} <button type="button" className="inline-retry" onClick={loadAudit}>Retry</button></p> : audit.length ? <div className="table-container"><table className="students-table"><thead><tr><th>Action</th><th>Actor account ID</th><th>Student account ID</th><th>Time</th></tr></thead><tbody>{audit.map((item)=><tr key={item.id}><td>{item.action}</td><td>{item.actor_id}</td><td>{item.subject_id ?? '—'}</td><td>{new Date(item.created_at).toLocaleString()}</td></tr>)}</tbody></table></div> : <p className="probability-note">No admin-visible audit entries are available.</p>}</>}</div></section>}
    </section>
  );
}

export default memo(AdminDashboardComponent);


