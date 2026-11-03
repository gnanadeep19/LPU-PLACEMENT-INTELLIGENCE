import React, { useState } from 'react';
import { Trash2 } from 'lucide-react';

export default function DeleteControl({ label, onDelete, explanation = 'This cannot be undone.' }) {
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const remove = async () => {
    setBusy(true); setError('');
    try { await onDelete(); setConfirm(false); }
    catch (err) { setError(err?.message || 'Could not remove this item. Please retry.'); }
    finally { setBusy(false); }
  };
  if (!confirm) return <button type="button" className="evidence-delete-icon" aria-label={`Delete ${label}`} title={`Delete ${label}`} onClick={() => setConfirm(true)}><Trash2 size={17} aria-hidden="true" /></button>;
  return <div className="evidence-delete-confirm" role="group" aria-label={`Confirm delete ${label}`}><p>Remove {label}? {explanation}</p>{error && <p role="alert">{error}</p>}<div><button type="button" className="evidence-delete-button" disabled={busy} onClick={remove}>{busy ? 'Removing…' : 'Yes, remove'}</button><button type="button" className="btn-preset" disabled={busy} onClick={() => setConfirm(false)}>Cancel</button></div></div>;
}
