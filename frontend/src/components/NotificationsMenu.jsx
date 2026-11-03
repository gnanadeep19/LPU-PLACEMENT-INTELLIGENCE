import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell, Check } from 'lucide-react';
import { getSupabaseClient } from '../services/supabaseClient';

export default function NotificationsMenu() {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unread, setUnread] = useState(0);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const menuRef = useRef(null);
  const toggleRef = useRef(null);

  const refresh = useCallback(async () => {
    try {
      const db = getSupabaseClient();
      const [list, count] = await Promise.all([
        db.from('notifications').select('id,title,message,created_at,read_at').order('created_at', { ascending: false }).limit(30),
        db.from('notifications').select('id', { count: 'exact', head: true }).is('read_at', null),
      ]);
      if (list.error || count.error) throw new Error('Unable to load notifications.');
      setItems(list.data || []);
      setUnread(count.count || 0);
      setError('');
    } catch {
      setError('Notifications are unavailable. Try again.');
    }
  }, []);

  useEffect(() => {
    refresh();
    const timer = window.setInterval(refresh, 60000);
    return () => window.clearInterval(timer);
  }, [refresh]);

  useEffect(() => {
    if (!open) return undefined;
    const dismissOnOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) setOpen(false);
    };
    const dismissOnEscape = (event) => {
      if (event.key === 'Escape') {
        setOpen(false);
        toggleRef.current?.focus();
      }
    };
    document.addEventListener('pointerdown', dismissOnOutside);
    document.addEventListener('keydown', dismissOnEscape);
    return () => {
      document.removeEventListener('pointerdown', dismissOnOutside);
      document.removeEventListener('keydown', dismissOnEscape);
    };
  }, [open]);

  const markRead = async (id) => {
    setBusy(true);
    try {
      const { data, error: updateError } = await getSupabaseClient().from('notifications')
        .update({ read_at: new Date().toISOString() }).eq('id', id).select('id');
      if (updateError || data?.length !== 1) throw new Error('Unable to update notification.');
      await refresh();
    } catch {
      setError('Could not mark the notification as read. Try again.');
    } finally { setBusy(false); }
  };

  return (
    <div className="notifications-menu" ref={menuRef}>
      <button type="button" className="btn-preset notifications-toggle" ref={toggleRef} aria-expanded={open}
        aria-controls="notifications-panel" aria-label={`Notifications, ${unread} unread`}
        onClick={() => { setOpen((value) => !value); if (!open) refresh(); }}>
        <Bell size={16} aria-hidden="true" /> <span>Notifications</span>
        {unread > 0 && <span className="notifications-count">{unread > 99 ? '99+' : unread}</span>}
      </button>
      {open && <section id="notifications-panel" className="notifications-panel" aria-label="Notifications">
        <div className="notifications-heading"><div><h2>Notifications</h2><p>{unread} unread</p></div><button className="notifications-refresh" type="button" onClick={refresh}>Refresh</button></div>
        {error && <p className="notifications-error" role="status">{error}</p>}
        {!error && items.length === 0 && <p className="notifications-empty">You have no notifications yet.</p>}
        {items.length > 0 && <ul className="notifications-list">{items.map((item) => <li key={item.id} className={item.read_at ? '' : 'is-unread'}>
          <div><strong>{item.title}</strong><p>{item.message}</p><time>{new Date(item.created_at).toLocaleString()}</time></div>
          {!item.read_at && <button type="button" disabled={busy} onClick={() => markRead(item.id)} aria-label={`Mark ${item.title} as read`}><Check size={15} aria-hidden="true" /> Mark read</button>}
        </li>)}</ul>}
      </section>}
    </div>
  );
}
