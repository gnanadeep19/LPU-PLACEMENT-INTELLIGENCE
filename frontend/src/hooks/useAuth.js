import { useCallback, useEffect, useRef, useState } from 'react';
import { onUnauthorized } from '../services/apiClient';
import { fetchSession, signIn, signOut } from '../services/authService';
import { usesSupabaseAuth } from '../services/supabaseClient';

export const STAFF_ROLES = ['mentor', 'placement_officer', 'admin'];

export const ROLE_LABELS = {
  student: 'Student',
  mentor: 'Mentor',
  placement_officer: 'Placement officer',
  admin: 'Administrator',
};

const SESSION_EXPIRED_MESSAGE = 'Your session expired. Sign in again to continue.';

/**
 * Owns the browser session:
 * - resolves the server session on boot,
 * - schedules a local expiry notice so the user is not surprised mid-task,
 * - returns to the sign-in screen when any API call reports 401.
 */
export function useAuth() {
  const [user, setUser] = useState(null);
  const [status, setStatus] = useState('loading'); // loading | anonymous | authenticating | authenticated
  const [message, setMessage] = useState('');
  const expiryTimer = useRef(null);
  const mounted = useRef(true);

  const clearExpiryTimer = useCallback(() => {
    if (expiryTimer.current) {
      clearTimeout(expiryTimer.current);
      expiryTimer.current = null;
    }
  }, []);

  const scheduleExpiry = useCallback(
    (expiresInSeconds) => {
      clearExpiryTimer();
      if (!Number.isFinite(expiresInSeconds) || expiresInSeconds <= 0) return;
      const delay = Math.min(expiresInSeconds * 1000, 2147483000);
      expiryTimer.current = setTimeout(() => {
        if (!mounted.current) return;
        setUser(null);
        setStatus('anonymous');
        setMessage(SESSION_EXPIRED_MESSAGE);
      }, delay);
    },
    [clearExpiryTimer],
  );

  useEffect(() => {
    mounted.current = true;
    const unsubscribe = onUnauthorized((serverMessage) => {
      if (!mounted.current) return;
      setUser(null);
      setStatus('anonymous');
      setMessage(
        serverMessage && /expired/i.test(serverMessage) ? serverMessage : SESSION_EXPIRED_MESSAGE,
      );
      clearExpiryTimer();
    });

    fetchSession()
      .then((session) => {
        if (!mounted.current) return;
        if (!session?.user) { setStatus('anonymous'); return; }
        setUser(session.user);
        setStatus('authenticated');
        setMessage('');
        scheduleExpiry(session.expires_in);
      })
      .catch((error) => {
        if (!mounted.current) return;
        setStatus('anonymous');
        setMessage(
          error?.kind === 'unauthorized'
            ? ''
            : 'The sign-in service is unavailable. Retry in a moment.',
        );
      });

    return () => {
      mounted.current = false;
      clearExpiryTimer();
      unsubscribe();
    };
  }, [clearExpiryTimer, scheduleExpiry]);

  const login = useCallback(
    async (username, password) => {
      setStatus('authenticating');
      setMessage('');
      try {
        const session = await signIn(username, password);
        if (!session?.user) { setStatus('anonymous'); return 'Sign-in did not return a session. Try again.'; }
        setUser(session.user);
        setStatus('authenticated');
        setMessage('');
        scheduleExpiry(session.expires_in);
        return null;
      } catch (error) {
        setStatus('anonymous');
        return error?.message || 'Sign-in failed. Check your details and retry.';
      }
    },
    [scheduleExpiry],
  );

  const logout = useCallback(async () => {
    clearExpiryTimer();
    try {
      await signOut();
    } catch {
      if (usesSupabaseAuth) {
        return 'Sign-out could not be completed. Check your connection and try again.';
      }
      // The local session is cleared even if revocation fails.
    }
    setUser(null);
    setStatus('anonymous');
    setMessage('You have signed out.');
  }, [clearExpiryTimer]);

  return {
    user,
    status,
    message,
    login,
    logout,
    clearMessage: useCallback(() => setMessage(''), []),
    isStaff: Boolean(user && STAFF_ROLES.includes(user.role)),
  };
}
