import { get, post } from './apiClient';
import { getSupabaseClient, usesSupabaseAuth } from './supabaseClient';

export async function fetchSession() {
  if (usesSupabaseAuth) {
    const { data, error } = await getSupabaseClient().auth.getSession();
    if (error) throw error;
    if (!data.session) return null;
  }
  const response = await get('/auth/me', { timeoutMs: 8000 });
  return response?.data ?? null;
}

export async function signIn(username, password) {
  if (usesSupabaseAuth) {
    const { error } = await getSupabaseClient().auth.signInWithPassword({ email: username, password });
    if (error) throw new Error('Sign-in failed. Check your email and password and try again.');
    try { return await fetchSession(); }
    catch (err) { await getSupabaseClient().auth.signOut(); throw err; }
  }
  const response = await post('/auth/login', { username, password }, { timeoutMs: 15000 });
  return response?.data ?? null;
}

export async function signOut() {
  if (usesSupabaseAuth) {
    const { error } = await getSupabaseClient().auth.signOut();
    if (error) throw error;
    return { signed_out: true };
  }
  const response = await post('/auth/logout', {}, { timeoutMs: 8000 });
  return response?.data ?? null;
}
