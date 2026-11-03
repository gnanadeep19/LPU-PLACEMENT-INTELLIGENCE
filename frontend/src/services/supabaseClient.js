import { createClient } from '@supabase/supabase-js';

export const usesSupabaseAuth = import.meta.env?.VITE_AUTH_PROVIDER === 'supabase';
let client;

export function getSupabaseClient() {
  if (!usesSupabaseAuth) return null;
  if (client) return client;
  const url = import.meta.env?.VITE_SUPABASE_URL;
  const key = import.meta.env?.VITE_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) throw new Error('Supabase sign-in is not configured. Contact the project administrator.');
  client = createClient(url, key, {
    auth: { persistSession: true, autoRefreshToken: true, storage: window.sessionStorage },
  });
  return client;
}

export async function getSupabaseAccessToken() {
  const sdk = getSupabaseClient();
  if (!sdk) return null;
  const { data, error } = await sdk.auth.getSession();
  if (error) throw error;
  return data.session?.access_token || null;
}
