import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { api, getRefreshToken, hasSession, setTokens } from '@/api/client';
import type { Tokens, User } from '@/api/types';

type LoginCredentials = { tenant_slug: string; email: string; password: string };
type AuthContextValue = {
  user: User | null; loading: boolean;
  login: (details: LoginCredentials) => Promise<void>;
  registerAgency: (details: { agency_name: string; slug: string; full_name: string; email: string; password: string }) => Promise<void>;
  registerCustomer: (details: LoginCredentials & { full_name: string }) => Promise<void>;
  logout: () => Promise<void>; reload: () => Promise<void>;
};
const Context = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const reload = useCallback(async () => {
    if (!hasSession()) { setUser(null); return; }
    try { setUser(await api<User>('/auth/me')); }
    catch { setTokens(null); setUser(null); }
  }, []);
  useEffect(() => {
    void reload().finally(() => setLoading(false));
    const onExpired = () => setUser(null);
    window.addEventListener('proptech-session-expired', onExpired);
    return () => window.removeEventListener('proptech-session-expired', onExpired);
  }, [reload]);
  async function acceptTokens(tokens: Tokens) {
    setTokens(tokens);
    await reload();
  }
  const login = async (details: LoginCredentials) => {
    await acceptTokens(await api<Tokens>('/auth/login', { method: 'POST', body: JSON.stringify(details) }));
  };
  const registerAgency: AuthContextValue['registerAgency'] = async details => {
    await acceptTokens(await api<Tokens>('/auth/tenant/register', { method: 'POST', body: JSON.stringify(details) }));
  };
  const registerCustomer: AuthContextValue['registerCustomer'] = async details => {
    await acceptTokens(await api<Tokens>('/auth/register', { method: 'POST', body: JSON.stringify(details) }));
  };
  const logout = async () => {
    const refreshToken = getRefreshToken();
    if (refreshToken) {
      await api('/auth/logout', { method: 'POST', body: JSON.stringify({ refresh_token: refreshToken }) }).catch(() => {});
    }
    setTokens(null); setUser(null);
  };
  const value = useMemo(() => ({ user, loading, login, registerAgency, registerCustomer, logout, reload }), [user, loading, reload]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useAuth() {
  const context = useContext(Context);
  if (!context) throw new Error('AuthProvider missing');
  return context;
}
