import React, { useEffect, useMemo, useState } from 'react';
import { ChevronDown, RefreshCw, Search, Users } from 'lucide-react';
import { get } from '../services/apiClient';
import { MetricCard } from './ui';

// The two directories share a layout, but each endpoint enforces admin access.
export default function AdminMentorDirectory({ kind = 'mentor' }) {
  const isStudent = kind === 'student';
  const noun = isStudent ? 'student' : 'mentor';
  const title = isStudent ? 'Student' : 'Mentor';
  const [accounts, setAccounts] = useState(null);
  const [error, setError] = useState('');
  const [search, setSearch] = useState('');
  const [cohort, setCohort] = useState('All cohorts');
  const [version, setVersion] = useState(0);

  useEffect(() => {
    let active = true;
    setAccounts(null);
    setError('');
    get(isStudent ? '/admin/students' : '/admin/mentors').then((response) => {
      if (active) setAccounts(response.data || []);
    }).catch((err) => {
      if (active) setError(err?.message || `${title} directory could not be loaded.`);
    });
    return () => { active = false; };
  }, [version, isStudent, title]);

  const cohorts = useMemo(() => [...new Set((accounts || []).map((account) => account.cohort).filter(Boolean))].sort(), [accounts]);
  const visible = (accounts || []).filter((account) => {
    const query = search.trim().toLocaleLowerCase();
    return (cohort === 'All cohorts' || account.cohort === cohort)
      && (!query || [account.display_name, account.username, account.cohort || ''].some((value) => value.toLocaleLowerCase().includes(query)));
  });

  return <section className="glass-card admin-mentor-directory" aria-labelledby={`${noun}-directory-title`}>
    <div className="card-header"><div><h2 id={`${noun}-directory-title`}><Users size={18} aria-hidden="true" /> {title} users</h2><p>Review {noun} accounts and their assigned cohorts.</p></div>
      <button className="btn-preset" type="button" onClick={() => setVersion((current) => current + 1)}><RefreshCw size={15} aria-hidden="true" /> Refresh list</button>
    </div>
    <div className="card-body">
      <p className="probability-note">This directory lists local app accounts and their local status{isStudent ? ', including students without an assessment' : ''}. During the Supabase migration, an active local account does not confirm that a Supabase login is linked or active.</p>
      {error ? <p className="admin-empty-state" role="alert">{error} Use Refresh list to try again.</p> : accounts === null ? <p className="admin-empty-state" role="status">Loading {noun} users…</p> : <>
        <div className="mentor-directory-metrics"><MetricCard label={`${title} accounts`} value={accounts.length} /><MetricCard label="Active local accounts" value={accounts.filter((account) => account.is_active).length} tone="success" /><MetricCard label="Assigned cohorts" value={cohorts.length} /></div>
        <div className="mentor-directory-filters"><label className="input-label" htmlFor={`${noun}-directory-search`}><span>Find a {noun}</span><span className="directory-input-wrap"><Search size={17} aria-hidden="true" /><input id={`${noun}-directory-search`} className="number-input-field" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search by name, username or cohort" /></span></label>
          <label className="input-label" htmlFor={`${noun}-directory-cohort`}><span>Cohort</span><span className="directory-select-wrap"><select id={`${noun}-directory-cohort`} className="number-input-field" value={cohort} onChange={(event) => setCohort(event.target.value)}><option>All cohorts</option>{cohorts.map((value) => <option key={value}>{value}</option>)}</select><ChevronDown size={17} aria-hidden="true" /></span></label>
        </div>
        <p className="mentor-directory-count">Showing {visible.length} of {accounts.length} {noun} accounts</p>
        <div className="table-container"><table className="students-table"><thead><tr><th scope="col">{title}</th><th scope="col">Username</th><th scope="col">Cohort</th><th scope="col">Local account status</th></tr></thead><tbody>
          {visible.map((account) => <tr key={account.id}><td><strong>{account.display_name}</strong></td><td>{account.username}</td><td>{account.cohort || 'Not assigned'}</td><td><span className={`mentor-directory-status ${account.is_active ? 'is-active' : 'is-inactive'}`}>{account.is_active ? 'Active' : 'Inactive'}</span></td></tr>)}
          {visible.length === 0 && <tr><td className="admin-empty-cell" colSpan={4}>{accounts.length ? `No ${noun} accounts match these filters.` : `No ${noun} accounts are available.`}</td></tr>}
        </tbody></table></div>
      </>}
    </div>
  </section>;
}
