import React, { useState } from 'react';
import { get } from '../services/apiClient';

export default function PlacementHistory({ studentId, name }) {
  const [open, setOpen] = useState(false);
  const [rows, setRows] = useState(null);
  const [error, setError] = useState('');
  const load = async () => {
    setError(''); setRows(null);
    try { const response = await get(`/placement-pipeline/${studentId}/history`); setRows(response.data || []); }
    catch (err) { setError(err?.message || 'Placement history could not be loaded.'); }
  };
  return <div className="placement-history"><button type="button" className="btn-preset" aria-expanded={open} onClick={() => { if (!open) load(); setOpen(!open); }}>{open ? 'Hide history' : 'View history'}</button>{open && <div><strong>Placement history for {name}</strong>{error ? <p role="alert">{error} <button type="button" className="inline-retry" onClick={load}>Retry</button></p> : rows === null ? <p role="status">Loading history…</p> : rows.length ? <ul>{rows.map((row) => <li key={row.id}>{row.stage} · {row.target_role || 'Role not recorded'}{row.company ? ` · ${row.company}` : ''} · {new Date(row.updated_at).toLocaleString()} · Updated by account {row.updated_by}</li>)}</ul> : <p>No recorded changes yet.</p>}</div>}</div>;
}
