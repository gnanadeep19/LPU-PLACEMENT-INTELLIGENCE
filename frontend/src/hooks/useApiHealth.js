import { useCallback, useEffect, useRef, useState } from 'react';
import { checkHealth } from '../services/assessmentService';

let inflightHealth = null;

function checkOnce() {
  if (!inflightHealth) {
    inflightHealth = checkHealth().finally(() => {
      inflightHealth = null;
    });
  }
  return inflightHealth;
}

export function useApiHealth() {
  const [apiOnline, setApiOnline] = useState(false);
  const [checking, setChecking] = useState(true);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const check = useCallback(async () => {
    setChecking(true);
    try {
      await checkOnce();
      if (mounted.current) setApiOnline(true);
      return true;
    } catch {
      if (mounted.current) setApiOnline(false);
      return false;
    } finally {
      if (mounted.current) setChecking(false);
    }
  }, []);

  useEffect(() => {
    check();
  }, [check]);

  return { apiOnline, checking, check };
}
