import { get, post, request } from './apiClient';

export function checkHealth({ signal } = {}) {
  return get('/health', { signal, timeoutMs: 8000 });
}

export async function predictStudent(student, { signal } = {}) {
  const response = await post('/predict', student, { signal, timeoutMs: 30000 });
  return response?.data ?? null;
}

export async function explainWithShap(student, modelVersion, { signal } = {}) {
  const response = await post('/explain/shap', { student, model_version: modelVersion }, { signal, timeoutMs: 30000 });
  return response?.data ?? null;
}

export async function saveAssessment(student, prediction, { signal } = {}) {
  const response = await post('/history', { student, prediction }, { signal, timeoutMs: 10000 });
  return response?.data ?? null;
}

export async function getHistory(student, { signal } = {}) {
  // POST keeps student feature values out of URLs, proxy logs, and browser history.
  const response = await post('/history/query', { student }, { signal, timeoutMs: 10000 });
  return response?.data || [];
}

export async function getCohortAnalytics({ signal } = {}) {
  const response = await get('/cohort-analytics', { signal, timeoutMs: 15000 });
  return response?.data ?? null;
}

export async function getMentorStudents({ signal } = {}) {
  const response = await get('/mentor/students', { signal, timeoutMs: 30000 });
  return response?.data || [];
}

export async function getMyStudentProfile({ signal } = {}) {
  const response = await get('/student/profile', { signal, timeoutMs: 10000 });
  return response?.data ?? null;
}

export async function saveMyTargetRoles(target_roles) {
  const response = await request('/student/profile', { method:'PUT', body:{ target_roles }, timeoutMs:10000 });
  return response?.data ?? null;
}

export async function getCoachingRecords(studentId, { signal } = {}) {
  const response = await get(`/students/${encodeURIComponent(studentId)}/coaching`, {
    signal,
    timeoutMs: 10000,
  });
  return response?.data || [];
}

export async function createCoachingRecord(studentId, record) {
  const response = await post(`/students/${encodeURIComponent(studentId)}/coaching`, record, {
    timeoutMs: 10000,
  });
  return response?.data ?? null;
}

export async function updateCoachingRecord(studentId, recordId, changes) {
  const response = await request(`/students/${encodeURIComponent(studentId)}/coaching/${encodeURIComponent(recordId)}`, {
    method: 'PATCH', body: changes, timeoutMs: 10000,
  });
  return response?.data ?? null;
}

export async function deleteCoachingRecord(studentId, recordId) {
  return request(`/students/${encodeURIComponent(studentId)}/coaching/${encodeURIComponent(recordId)}`, { method: 'DELETE', timeoutMs: 10000 });
}

export async function getStudentEvidence(studentId, { signal } = {}) {
  const response = await get(`/students/${encodeURIComponent(studentId)}/evidence`, { signal, timeoutMs:10000 });
  return response?.data || [];
}

export async function addStudentEvidence(studentId, evidence) {
  const response = await post(`/students/${encodeURIComponent(studentId)}/evidence`, evidence, { timeoutMs:10000 });
  return response?.data ?? null;
}

export async function deleteStudentEvidence(studentId, evidenceId) {
  return request(`/students/${encodeURIComponent(studentId)}/evidence/${encodeURIComponent(evidenceId)}`, { method: 'DELETE', timeoutMs: 10000 });
}

export async function getProfileCorrections(studentId, { signal } = {}) {
  const path = studentId == null ? '/profile-corrections' : `/students/${encodeURIComponent(studentId)}/profile-corrections`;
  const response = await get(path, { signal, timeoutMs: 10000 });
  return response?.data || [];
}

export async function requestProfileCorrection(studentId, correction) {
  const response = await post(`/students/${encodeURIComponent(studentId)}/profile-corrections`, correction, { timeoutMs: 10000 });
  return response?.data ?? null;
}

export async function withdrawProfileCorrection(studentId, correctionId) {
  return request(`/students/${encodeURIComponent(studentId)}/profile-corrections/${encodeURIComponent(correctionId)}`, { method: 'DELETE', timeoutMs: 10000 });
}

export async function deletePlacementRecord(studentId) {
  return request(`/placement-pipeline/${encodeURIComponent(studentId)}`, { method: 'DELETE', timeoutMs: 10000 });
}

export async function resolveProfileCorrection(correctionId, status, resolution) {
  const response = await request(`/profile-corrections/${encodeURIComponent(correctionId)}`, {
    method: 'PATCH', body: { status, resolution }, timeoutMs: 10000,
  });
  return response?.data ?? null;
}

export async function verifyStudentEvidence(studentId, evidenceId, status) {
  const response = await request(`/students/${encodeURIComponent(studentId)}/evidence/${encodeURIComponent(evidenceId)}`, { method:'PATCH', body:{status}, timeoutMs:10000 });
  return response?.data ?? null;
}

export async function getPlacementPipeline({ signal } = {}) {
  const response = await get('/placement-pipeline', { signal, timeoutMs: 12000 });
  return response?.data || [];
}

export async function getPlacementSummary({ signal } = {}) {
  const response = await get('/placement-pipeline/summary', { signal, timeoutMs:10000 });
  return response?.data || null;
}

export async function savePlacementStage(record) {
  const response = await post('/placement-pipeline', record, { timeoutMs: 10000 });
  return response?.data ?? null;
}

export async function getModelInfo({ signal } = {}) {
  const response = await get('/model-info', { signal, timeoutMs: 12000 });
  return response?.data ?? response ?? null;
}

export function createVersionedClient(version = 'v1') {
  const prefix = `/${version}`;
  return {
    health: () => get(`${prefix}/health`, { timeoutMs: 8000 }),
    predict: (student) => post(`${prefix}/predict`, student, { timeoutMs: 30000 }),
    history: (student) => post(`${prefix}/history/query`, { student }, { timeoutMs: 10000 }),
    cohort: () => get(`${prefix}/cohort-analytics`, { timeoutMs: 15000 }),
  };
}
