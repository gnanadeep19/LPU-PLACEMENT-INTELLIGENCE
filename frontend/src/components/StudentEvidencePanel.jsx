import React, { memo, useCallback, useEffect, useState } from 'react';
import { ExternalLink, FileCheck2, Plus, RefreshCw, Trash2 } from 'lucide-react';
import { addStudentEvidence, deleteStudentEvidence, getProfileCorrections, getStudentEvidence, requestProfileCorrection, withdrawProfileCorrection } from '../services/assessmentService';
import { SectionIntro, StatusBanner } from './ui';
import DeleteControl from './DeleteControl';

const labels = { project: 'Project', internship: 'Internship', certification: 'Certification', portfolio: 'Portfolio', skill: 'Skill evidence' };

function StudentEvidencePanel({ studentId }) {
  const [items, setItems] = useState([]);
  const [corrections, setCorrections] = useState([]);
  const [type, setType] = useState('project');
  const [title, setTitle] = useState('');
  const [detail, setDetail] = useState('');
  const [url, setUrl] = useState('');
  const [correction, setCorrection] = useState({ field_name: '', current_value: '', requested_value: '', reason: '' });
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const [evidence, requests] = await Promise.all([getStudentEvidence(studentId), getProfileCorrections(studentId)]);
      setItems(evidence); setCorrections(requests); setError('');
    } catch (err) { setError(err?.message || 'Profile information could not be loaded. Your unsent edits are still on this page.'); }
  }, [studentId]);
  useEffect(() => { refresh(); }, [refresh]);

  const submit = async (event) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try { await addStudentEvidence(studentId, { evidence_type: type, title, detail, evidence_url: url }); setTitle(''); setDetail(''); setUrl(''); setNotice('Evidence submitted. It remains student-reported until reviewed.'); await refresh(); }
    catch (err) { setError(err?.message || 'Evidence could not be saved. Your form values have been kept.'); }
    finally { setBusy(false); }
  };
  const submitCorrection = async (event) => {
    event.preventDefault(); setBusy(true); setError(''); setNotice('');
    try { await requestProfileCorrection(studentId, correction); setCorrection({ field_name: '', current_value: '', requested_value: '', reason: '' }); setNotice('Correction request sent to an administrator for review.'); await refresh(); }
    catch (err) { setError(err?.message || 'Correction request could not be saved. Your form values have been kept.'); }
    finally { setBusy(false); }
  };

  const removeEvidence = async (item) => {
    setDeleting(true); setError(''); setNotice('');
    try {
      await deleteStudentEvidence(studentId, item.id);
      setItems((current) => current.filter((entry) => entry.id !== item.id));
      setConfirmDelete(null);
      setNotice('Evidence removed from your profile. Your saved assessments have not changed.');
    } catch (err) { setError(err?.message || 'Evidence could not be removed. Please retry.'); }
    finally { setDeleting(false); }
  };

  return <section className="glass-card student-evidence-panel" aria-labelledby="student-evidence-title">
    <div className="card-header"><div><h2 id="student-evidence-title"><FileCheck2 size={18} aria-hidden="true" /> Profile evidence and corrections</h2><SectionIntro>Add project, internship, certification, portfolio, or skill evidence. Student correction requests are reviewed by an administrator; they do not silently change an assessment.</SectionIntro></div><button type="button" className="btn-preset" onClick={refresh}><RefreshCw size={14} aria-hidden="true" /> Refresh</button></div>
    <div className="card-body">{error && <StatusBanner tone="warning">{error}</StatusBanner>}{notice && <StatusBanner tone="success">{notice}</StatusBanner>}
      {items.length ? <div className="rec-list">{items.map((item) => <article className="rec-card" key={item.id}><div className="rec-header"><span className="rec-badge">{labels[item.evidence_type] || item.evidence_type} · {item.verification_status}</span><span className="rec-priority">Submitted {new Date(item.submitted_at).toLocaleDateString()}</span></div><h3 className="rec-title">{item.title}</h3>{item.detail && <p className="rec-details">{item.detail}</p>}{item.evidence_url && <a href={item.evidence_url} target="_blank" rel="noreferrer">Open submitted evidence <ExternalLink size={14} aria-hidden="true" /></a>}<p className="probability-note">Source: {item.source}{item.verified_at ? ` · Reviewed ${new Date(item.verified_at).toLocaleDateString()}` : ' · Awaiting authorized review'}</p>{confirmDelete === item.id ? <div className="evidence-delete-confirm" role="group" aria-label={`Remove ${item.title}`}><p>Remove this evidence from your profile? This cannot be undone.</p><div><button type="button" className="evidence-delete-button" onClick={() => removeEvidence(item)} disabled={deleting}><Trash2 size={15} aria-hidden="true" />{deleting ? 'Removing…' : 'Yes, remove'}</button><button type="button" className="btn-preset" disabled={deleting} onClick={() => setConfirmDelete(null)}>Cancel</button></div></div> : <button type="button" className="evidence-delete-icon" aria-label={`Delete ${item.title}`} title="Delete evidence" disabled={deleting} onClick={() => setConfirmDelete(item.id)}><Trash2 size={17} aria-hidden="true" /></button>}</article>)}</div> : <p className="probability-note">No evidence submitted yet. Counts in your assessment are not independently verified.</p>}
      <form className="rec-card student-evidence-form" onSubmit={submit}><h3 className="panel-subheading"><Plus size={16} aria-hidden="true" /> Add evidence</h3><label className="input-label">Evidence type<select className="number-input-field" value={type} onChange={(event) => setType(event.target.value)}>{Object.entries(labels).map(([key, label]) => <option key={key} value={key}>{label}</option>)}</select></label><label className="input-label">Title<input required maxLength={140} className="number-input-field" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Project, certificate, internship, or skill" /></label><label className="input-label">Description<textarea maxLength={2000} rows={3} className="number-input-field" value={detail} onChange={(event) => setDetail(event.target.value)} placeholder="Your contribution, dates, tools, or outcomes" /></label><label className="input-label">Evidence URL (optional)<input type="url" maxLength={500} className="number-input-field" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://…" /></label><button className="evidence-submit-button" type="submit" disabled={busy}><Plus size={15} aria-hidden="true" /> Submit for review</button></form>
      <h3 className="panel-subheading">Request a profile correction</h3><form className="rec-card student-evidence-form student-correction-form" onSubmit={submitCorrection}><label className="input-label">Field to correct<input required maxLength={80} className="number-input-field" value={correction.field_name} onChange={(event) => setCorrection({ ...correction, field_name: event.target.value })} placeholder="e.g. coding assessment score" /></label><label className="input-label">Current value (optional)<input maxLength={300} className="number-input-field" value={correction.current_value} onChange={(event) => setCorrection({ ...correction, current_value: event.target.value })} /></label><label className="input-label">Correct value<input required maxLength={300} className="number-input-field" value={correction.requested_value} onChange={(event) => setCorrection({ ...correction, requested_value: event.target.value })} /></label><label className="input-label">Reason<textarea required maxLength={1000} rows={2} className="number-input-field" value={correction.reason} onChange={(event) => setCorrection({ ...correction, reason: event.target.value })} /></label><button className="evidence-submit-button" type="submit" disabled={busy}>Send for admin review</button></form>
      {corrections.length > 0 && <><h3 className="panel-subheading">Correction request history</h3><div className="rec-list">{corrections.map((item) => <article className="rec-card" key={item.id}><div className="rec-header"><strong>{item.field_name}</strong><span className="rec-badge">{item.status}</span></div><p className="rec-details">Requested: {item.requested_value} · Submitted {new Date(item.submitted_at).toLocaleDateString()}</p>{item.resolution && <p className="probability-note">Admin response: {item.resolution}</p>}{item.status === 'open' && <DeleteControl label={`correction request for ${item.field_name}`} explanation="The request will be withdrawn from admin review." onDelete={async () => { await withdrawProfileCorrection(studentId, item.id); setCorrections((current) => current.filter((entry) => entry.id !== item.id)); setNotice('Correction request withdrawn.'); }} />}</article>)}</div></>}
      <p className="probability-note">Links are validated for HTTP/HTTPS format only; the app does not confirm reachability or content. A reviewed correction still requires a new assessment to update the readiness estimate.</p>
    </div>
  </section>;
}

export default memo(StudentEvidencePanel);
