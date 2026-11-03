import { afterEach, describe, expect, it, vi } from 'vitest';

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.doUnmock('@supabase/supabase-js');
  vi.resetModules();
});

describe('Supabase sign-in transition', () => {
  it('sends the Supabase access token to Flask and uses the trusted Flask profile', async () => {
    vi.stubEnv('VITE_AUTH_PROVIDER', 'supabase');
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'publishable');
    const sdk = { auth: {
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
      getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'verified-token' } }, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    } };
    vi.doMock('@supabase/supabase-js', () => ({ createClient: () => sdk }));
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, headers: new Headers(), json: async () => ({ data: { user: { id: 2, role: 'student' } } }) });
    vi.stubGlobal('fetch', fetchMock);
    const { signIn } = await import('./authService');
    const session = await signIn('student@example.com', 'password');
    expect(sdk.auth.signInWithPassword).toHaveBeenCalledWith({ email: 'student@example.com', password: 'password' });
    expect(fetchMock.mock.calls[0][1].headers.Authorization).toBe('Bearer verified-token');
    expect(session.user).toEqual({ id: 2, role: 'student' });
  });

  it('signs out of Supabase if the backend rejects the account mapping', async () => {
    vi.stubEnv('VITE_AUTH_PROVIDER', 'supabase');
    vi.stubEnv('VITE_SUPABASE_URL', 'https://example.supabase.co');
    vi.stubEnv('VITE_SUPABASE_PUBLISHABLE_KEY', 'publishable');
    const sdk = { auth: {
      signInWithPassword: vi.fn().mockResolvedValue({ error: null }),
      getSession: vi.fn().mockResolvedValue({ data: { session: { access_token: 'token' } }, error: null }),
      signOut: vi.fn().mockResolvedValue({ error: null }),
    } };
    vi.doMock('@supabase/supabase-js', () => ({ createClient: () => sdk }));
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401, headers: new Headers(), json: async () => ({ message: 'Account mapping is invalid.' }) }));
    const { signIn } = await import('./authService');
    await expect(signIn('student@example.com', 'password')).rejects.toThrow('Account mapping is invalid.');
    expect(sdk.auth.signOut).toHaveBeenCalled();
  });
});
