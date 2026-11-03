import { useCallback, useEffect, useRef, useState } from 'react';
import { getHistory, predictStudent, saveAssessment } from '../services/assessmentService';
import { recordEvent } from '../telemetry/telemetry';

/**
 * Owns the prediction request lifecycle:
 * - one in-flight request at a time (previous request is cancelled),
 * - stale responses are ignored,
 * - a history persistence failure never discards a successful prediction,
 * - the last submitted profile is kept for one-click retry.
 */
export function useAssessment() {
  const [prediction, setPrediction] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [historyError, setHistoryError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  const controllerRef = useRef(null);
  const requestSequence = useRef(0);
  const lastProfileRef = useRef(null);
  const mounted = useRef(true);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      controllerRef.current?.abort();
    };
  }, []);

  const loadHistory = useCallback(async (profile, signal) => {
    try {
      const rows = await getHistory(profile, { signal });
      if (mounted.current) {
        setHistory(rows);
        setHistoryError(null);
      }
    } catch (err) {
      if (err?.name === 'AbortError') return;
      if (mounted.current) setHistoryError(err?.message || 'Progress history is unavailable.');
    }
  }, []);

  const analyze = useCallback(
    async (formData) => {
      lastProfileRef.current = formData;
      controllerRef.current?.abort();
      const controller = new AbortController();
      controllerRef.current = controller;
      const sequence = ++requestSequence.current;
      const startedAt = typeof performance !== 'undefined' ? performance.now() : Date.now();

      setLoading(true);
      setError(null);
      recordEvent('assessment_submitted');

      try {
        const result = await predictStudent(formData, { signal: controller.signal });
        if (!mounted.current || sequence !== requestSequence.current) return;

        setPrediction(result);
        setLastUpdated(new Date());
        recordEvent('assessment_succeeded', {
          duration_ms:
            (typeof performance !== 'undefined' ? performance.now() : Date.now()) - startedAt,
        });

        // Persistence is best-effort: the result on screen is still valid.
        try {
          await saveAssessment(formData, result, { signal: controller.signal });
        } catch (err) {
          if (err?.name !== 'AbortError' && mounted.current) {
            setHistoryError('This assessment could not be saved to progress history.');
          }
        }

        await loadHistory(formData, controller.signal);
      } catch (err) {
        if (err?.name === 'AbortError' || sequence !== requestSequence.current) return;
        if (!mounted.current) return;
        setError({
          message: err?.message || 'The readiness analysis could not be completed.',
          kind: err?.kind || 'server',
          correlationId: err?.correlationId || null,
        });
      } finally {
        if (mounted.current && sequence === requestSequence.current) setLoading(false);
      }
    },
    [loadHistory],
  );

  const retry = useCallback(() => {
    if (lastProfileRef.current) analyze(lastProfileRef.current);
  }, [analyze]);

  const clearError = useCallback(() => setError(null), []);

  return {
    prediction,
    history,
    loading,
    error,
    historyError,
    lastUpdated,
    analyze,
    retry,
    clearError,
  };
}
