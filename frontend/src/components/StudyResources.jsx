import React, { useCallback, useEffect, useRef, useState } from 'react';
import { BookOpen, ChevronDown, Download, RefreshCw, Search, SlidersHorizontal, Upload } from 'lucide-react';
import { download, get, post, request } from '../services/apiClient';
import DeleteControl from './DeleteControl';

const CATEGORIES = ['General', 'Coding', 'Technical skills', 'Aptitude', 'Communication', 'Resume', 'Interview'];

export default function StudyResources({ studentId, canUpload = false, viewer = null, students = [] }) {
  const [items, setItems] = useState(null);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const [retryingId, setRetryingId] = useState(null);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('General');
  const [categoryFilter, setCategoryFilter] = useState('All subjects');
  const [search, setSearch] = useState('');
  const [additionalStudents, setAdditionalStudents] = useState([]);
  const [file, setFile] = useState(null);
  const [fileKey, setFileKey] = useState(0);
  const uploadKey = useRef(null);
  const refresh = useCallback(async () => {
    if (!studentId) return;
    try { const result = await get(`/students/${studentId}/resources`); setItems(result.data || []); setError(''); }
    catch (err) { setItems(null); setError(err?.message || 'Could not load study resources.'); }
  }, [studentId]);
  useEffect(() => { uploadKey.current = null; setItems(null); setTitle(''); setDescription(''); setFile(null); setFileKey((n) => n + 1); setAdditionalStudents([]); setMessage(''); refresh(); }, [refresh]);
  const submit = async (event) => {
    event.preventDefault();
    if (!file || !title.trim()) return;
    if (file.size > 5 * 1024 * 1024) { setError('Choose a file of at most 5 MB.'); return; }
    if (!uploadKey.current) {
      if (!globalThis.crypto?.randomUUID) { setError('This browser cannot create a secure upload identifier. Please use a current browser.'); return; }
      uploadKey.current = globalThis.crypto.randomUUID();
    }
    setBusy(true); setError(''); setMessage('');
    try {
      const recipients = [studentId, ...additionalStudents.filter((id) => id !== studentId)];
      const results = await Promise.allSettled(recipients.map((id) => { const form = new FormData(); form.append('title', title.trim()); form.append('description', description); form.append('category', category); form.append('upload_key', uploadKey.current); form.append('file', file); return post(`/students/${id}/resources`, form); }));
      const failed = recipients.filter((_, index) => results[index].status === 'rejected');
      await refresh();
      if (failed.length) {
        const failedNames = failed.map((id) => students.find((item) => item.user_id === id)?.display_name || `Student ${id}`).join(', ');
        setError(`Shared with ${recipients.length - failed.length} of ${recipients.length} students. Failed: ${failedNames}. Retry those students individually to avoid duplicates.`);
      } else { const unsent = results.filter((result) => result.value?.data?.notification_sent === false).length; uploadKey.current = null; setTitle(''); setDescription(''); setFile(null); setFileKey((n) => n + 1); setAdditionalStudents([]); setMessage(`Resource shared with ${recipients.length} student${recipients.length === 1 ? '' : 's'}.${unsent ? ` Notification is pending for ${unsent}; open each student's resource list to retry.` : ''}`); }
    }
    catch (err) { setError(err?.message || 'The resource could not be shared.'); }
    finally { setBusy(false); }
  };
  const visibleItems = (items || []).filter((item) => (categoryFilter === 'All subjects' || (item.category || 'General') === categoryFilter) && `${item.title} ${item.description} ${item.filename}`.toLowerCase().includes(search.trim().toLowerCase()));
  const retryNotification = async (item) => {
    setRetryingId(item.id); setError(''); setMessage('');
    try { await post(`/students/${studentId}/resources/${item.id}/notification`, {}); await refresh(); setMessage(`Notification sent for ${item.title}.`); }
    catch (err) { setError(err?.message || 'Notification could not be sent. Please retry.'); }
    finally { setRetryingId(null); }
  };
  const open = async (item) => {
    setError('');
    try {
      const blob = await download(`/students/${studentId}/resources/${item.id}/download`);
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a'); link.href = url; link.download = item.filename; document.body.appendChild(link); link.click(); link.remove();
      setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (err) { setError(err?.message || 'The resource could not be downloaded.'); }
  };
  return <section className="glass-card study-resources" aria-labelledby={`resources-heading-${canUpload ? 'mentor' : 'student'}`}>
    <div className="card-header"><div><h2 id={`resources-heading-${canUpload ? 'mentor' : 'student'}`}><BookOpen size={18} aria-hidden="true" /> Study resources</h2><p>{canUpload ? 'Share a file with the selected student.' : 'Materials shared by your mentor.'}</p></div><button className="btn-preset" type="button" onClick={refresh}><RefreshCw size={15} aria-hidden="true" /> Refresh</button></div>
    <div className="card-body">
      {error && <p className="study-resource-error" role="alert">{error} <button type="button" className="mentor-link-button" onClick={refresh}>Retry loading</button></p>}
      {message && <p className="study-resource-message" role="status">{message}</p>}
      {canUpload && <form className="study-resource-form" onSubmit={submit}>
        <label className="input-label">Resource title<input className="number-input-field" value={title} onChange={(event) => { uploadKey.current = null; setTitle(event.target.value); }} maxLength={140} required placeholder="e.g. SQL practice guide" /></label>
        <label className="input-label">Description (optional)<textarea className="number-input-field" value={description} onChange={(event) => { uploadKey.current = null; setDescription(event.target.value); }} maxLength={2000} rows={2} placeholder="What should the student study?" /></label>
        <label className="input-label">Subject<select className="number-input-field" value={category} onChange={(event) => { uploadKey.current = null; setCategory(event.target.value); }}>{CATEGORIES.map((name) => <option key={name}>{name}</option>)}</select></label>
        {students.length > 1 && <fieldset className="resource-recipients"><legend>Also share with</legend><p>Only students in your permitted roster are listed.</p>{students.filter((item) => item.user_id !== studentId).map((item) => <label key={item.user_id}><input type="checkbox" checked={additionalStudents.includes(item.user_id)} onChange={(event) => setAdditionalStudents((current) => event.target.checked ? [...current, item.user_id] : current.filter((id) => id !== item.user_id))} /> {item.display_name} · {item.cohort || 'No cohort'}</label>)}</fieldset>}
        <label className="input-label">Study file<input key={fileKey} className="number-input-field" type="file" accept=".pdf,.docx,.pptx,.txt,.png,.jpg,.jpeg" aria-required="true" onChange={(event) => { uploadKey.current = null; setFile(event.target.files?.[0] || null); }} /></label>
        <p className="probability-note">PDF, DOCX, PPTX, TXT, PNG or JPG · Maximum 5 MB</p>
        <button type="submit" className="study-resource-button" disabled={busy || !file || !title.trim()}><Upload size={16} aria-hidden="true" />{busy ? 'Sharing…' : 'Share resource'}</button>
      </form>}
      {items?.length > 0 && <div className="resource-filters" role="search" aria-label="Filter study resources">
        <div className="resource-filters-heading">
          <div className="resource-filters-title"><SlidersHorizontal size={16} aria-hidden="true" /><span>Find resources</span></div>
          <span className="resource-filters-count" aria-live="polite">{visibleItems.length} of {items.length} {items.length === 1 ? 'resource' : 'resources'}</span>
        </div>
        <div className="resource-filters-fields">
          <label className="resource-filter-field">
            <span>Search resources</span>
            <span className="resource-filter-control resource-search-control">
              <Search size={18} aria-hidden="true" />
              <input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by title or file name" />
            </span>
          </label>
          <label className="resource-filter-field">
            <span>Subject</span>
            <span className="resource-filter-control resource-subject-control">
              <select value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)}><option>All subjects</option>{CATEGORIES.map((name) => <option key={name}>{name}</option>)}</select>
              <ChevronDown size={17} aria-hidden="true" />
            </span>
          </label>
        </div>
        {(search || categoryFilter !== 'All subjects') && <button type="button" className="resource-filter-reset" onClick={() => { setSearch(''); setCategoryFilter('All subjects'); }}>Clear filters</button>}
      </div>}
      {items === null ? !error && <p role="status">Loading resources…</p> : items.length ? visibleItems.length ? <div className="study-resource-list">{visibleItems.map((item) => <article className="study-resource-item" key={item.id}><div><h3>{item.title}</h3>{item.description && <p>{item.description}</p>}<small>{item.category || 'General'} · {item.filename} · Uploaded {new Date(item.created_at).toLocaleDateString()}</small>{canUpload && item.notification_status === 'pending' && <p className="study-resource-error">Student notification pending</p>}</div><div className="resource-item-actions"><button type="button" className="btn-preset" onClick={() => open(item)}><Download size={15} aria-hidden="true" /> Download</button>{canUpload && item.notification_status === 'pending' && (viewer?.id === item.author_id || viewer?.role === 'admin') && <button type="button" className="btn-preset" disabled={retryingId === item.id} onClick={() => retryNotification(item)}>{retryingId === item.id ? 'Retrying…' : 'Retry notification'}</button>}{canUpload && (viewer?.id === item.author_id || viewer?.role === 'admin') && <DeleteControl label={item.title} explanation="The student will no longer be able to download this file." onDelete={async () => { await request(`/students/${studentId}/resources/${item.id}`, { method: 'DELETE' }); setItems((current) => current.filter((entry) => entry.id !== item.id)); setMessage('Resource removed.'); }} />}</div></article>)}</div> : <p className="probability-note">No resources match your search.</p> : <p className="probability-note">{canUpload ? 'No resources have been shared with this student yet.' : 'Your mentor has not shared any resources yet.'}</p>}
    </div>
  </section>;
}
