import { useCallback, useEffect, useRef, useState } from 'react';
import { getCohortAnalytics } from '../services/assessmentService';

const CACHE_TTL_MS = 60_000;
let cache = { data: null, at: 0, scope: null };
const inflight = new Map();

export function resetCohortCache() {
  cache = { data: null, at: 0, scope: null };
  inflight.clear();
}

/**
 * @param {string} scope identifies the viewer's authorization scope
 * (role + cohort). Cached aggregates are never reused across scopes.
 */
export function useCohortAnalytics(scope = 'default') {
  const [cohort, setCohort] = useState(() => (cache.scope === scope ? cache.data : null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const mounted = useRef(true);
  const scopeRef = useRef(scope);
  scopeRef.current = scope;

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  const load = useCallback(async ({ force = false } = {}) => {
    const currentScope = scopeRef.current;
    const fresh =
      cache.data && cache.scope === currentScope && Date.now() - cache.at < CACHE_TTL_MS;

    if (fresh && !force) {
      if (mounted.current && scopeRef.current === currentScope) setCohort(cache.data);
      return cache.data;
    }

    setLoading(true);
    setError(null);
    try {
      if (!inflight.has(currentScope)) {
        inflight.set(
          currentScope,
          getCohortAnalytics().finally(() => {
            inflight.delete(currentScope);
          }),
        );
      }
      const data = await inflight.get(currentScope);
      if (scopeRef.current !== currentScope) return data;
      cache = { data, at: Date.now(), scope: currentScope };
      if (mounted.current) setCohort(data);
      return data;
    } catch (err) {
      if (mounted.current && scopeRef.current === currentScope) {
        setError(err?.message || 'Cohort analytics are unavailable.');
      }
      return null;
    } finally {
      if (mounted.current && scopeRef.current === currentScope) setLoading(false);
    }
  }, []);

  return { cohort, loading, error, load };
}
