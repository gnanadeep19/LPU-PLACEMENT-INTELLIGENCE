import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Download, FileText, RefreshCw, Upload } from 'lucide-react';
import { download, get, post, request } from '../services/apiClient';

const LABELS = { pending: 'Awaiting mentor review', approved: 'Approved by mentor', changes_requested: 'Changes requested' };

export default function CvReview({ studentId, mentor = false, onReviewed }) {
  const [records, setRecords] = useState(null);
  const [file, setFile] = useState(null);
  const [fileKey, setFileKey] = useState(0);
  const [feedback, setFeedback] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const headingId = `cv-review-${mentor ? 'mentor' : 'student'}-${studentId}`;
  const refresh = useCallback(async () => {
    try {
      const result = await get(`/students/${studentId}/cv`);
      setRecords(result.data || []); setError('');
    } catch (err) { setRecords(null); setError(err?.message || 'CV submissions could not be loaded.'); }
  }, [studentId]);
  useEffect(() => { setRecords(null); setFile(null); setFeedback(''); setMessage(''); refresh(); }, [refresh]);
  const latest = records?.[0];
  const submit = async (event) => {
    event.preventDefault();
    if (!file || busy) return;
    if (file.size > 5 * 1024 * 1024) { setError('Choose a CV of at most 5 MB.'); return; }
    setBusy(true); setError(''); setMessage('');
    try {
      const form = new FormData(); form.append('file', file);
      await post(`/students/${studentId}/cv`, form);
      setFile(null); setFileKey((current) => current + 1);
      setMessage('CV submitted for mentor review.');
      await refresh();
    } catch (err) { setError(err?.message || 'Your CV could not be submitted. Please retry.'); }
    finally { setBusy(false); }
  };
  const open = async () => {
    setError('');
    try {
      const blob = await download(`/students/${studentId}/cv/${latest.id}/download`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = latest.filename;
      document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err?.message || 'The CV could not be downloaded.'); }
  };
  const review = async (status) => {
    if (!latest || busy) return;
    if (status === 'changes_requested' && !feedback.trim()) { setError('Add feedback so the student knows what to change.'); return; }
    setBusy(true); setError(''); setMessage('');
    try {
      await request(`/students/${studentId}/cv/${latest.id}/review`, { method: 'PATCH', body: { status, feedback: feedback.trim() } });
      onReviewed?.(status);
      setFeedback(''); setMessage(status === 'approved' ? 'CV approved.' : 'Feedback sent to the student.');
      await refresh();
    } catch (err) { setError(err?.message || 'The review could not be saved. Please retry.'); }
    finally { setBusy(false); }
  };
  return <section className="glass-card cv-review" aria-labelledby={headingId}>
    <div className="card-header"><div><h2 id={headingId}><FileText size={18} aria-hidden="true" /> CV review</h2><p>{mentor ? 'Review the student’s latest CV and share clear feedback.' : 'Submit your CV for a mentor to review.'}</p></div><button type="button" className="btn-preset" onClick={refresh} disabled={busy}><RefreshCw size={15} aria-hidden="true" /> Refresh</button></div>
    <div className="card-body">
      {error && <p className="study-resource-error" role="alert">{error} <button type="button" className="mentor-link-button" onClick={refresh}>Retry loading</button></p>}
      {message && <p className="study-resource-message" role="status">{message}</p>}
      {records === null ? !error && <p role="status">Loading CV submissions…</p> : !latest ? <p className="probability-note">{mentor ? 'This student has not submitted a CV yet.' : 'You have not submitted a CV yet.'}</p> : <article className="cv-review-current">
        <div className="cv-review-summary"><div><span className={`cv-review-status cv-review-status-${latest.status}`}>{LABELS[latest.status] || 'Review status unavailable'}</span><h3>{latest.filename}</h3><p>Submitted {new Date(latest.submitted_at).toLocaleDateString()}{latest.reviewed_at ? ` · Reviewed ${new Date(latest.reviewed_at).toLocaleDateString()}` : ''}</p></div><button type="button" className="btn-preset" onClick={open}><Download size={15} aria-hidden="true" /> Download CV</button></div>
        {latest.feedback && <div className="cv-review-feedback"><strong>Mentor feedback</strong><p>{latest.feedback}</p></div>}
        {mentor && latest.status === 'pending' && <div className="cv-review-actions"><label className="input-label">Feedback to student<textarea className="number-input-field" rows={3} maxLength={1000} value={feedback} onChange={(event) => setFeedback(event.target.value)} placeholder="Share strengths and any suggested changes" /></label><p className="probability-note">Feedback is required when requesting changes.</p><div className="cv-review-buttons"><button type="button" className="study-resource-button" disabled={busy} onClick={() => review('approved')}><CheckCircle2 size={16} aria-hidden="true" /> Approve CV</button><button type="button" className="btn-preset" disabled={busy} onClick={() => review('changes_requested')}>Request changes</button></div></div>}
      </article>}
      {!mentor && <form className="study-resource-form cv-upload-form" onSubmit={submit}><label className="input-label">{latest ? 'Upload a new CV version' : 'Choose your CV'}<input key={fileKey} className="number-input-field" type="file" accept=".pdf,.docx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><p className="probability-note">PDF or DOCX · Maximum 5 MB. A new version requires a new mentor review. In this demo, CV files are stored on this computer.</p><button type="submit" className="study-resource-button" disabled={busy || !file}><Upload size={16} aria-hidden="true" /> {busy ? 'Submitting…' : 'Submit for review'}</button></form>}
    </div>
  </section>;
}
