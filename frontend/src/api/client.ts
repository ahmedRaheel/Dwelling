import type { Tokens } from './types';
const BASE = import.meta.env.VITE_API_BASE ?? '/api/v1';
const ACCESS_KEY = 'proptech_access';
const REFRESH_KEY = 'proptech_refresh';

export function setTokens(tokens: Tokens | null) {
  if (tokens) {
    sessionStorage.setItem(ACCESS_KEY, tokens.access_token);
    sessionStorage.setItem(REFRESH_KEY, tokens.refresh_token);
  } else {
    sessionStorage.removeItem(ACCESS_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
  }
}
export const hasSession = () => Boolean(sessionStorage.getItem(ACCESS_KEY));
export const getRefreshToken = () => sessionStorage.getItem(REFRESH_KEY);
let ongoingRefresh: Promise<void> | null = null;

async function renew() {
  if (!ongoingRefresh) {
    ongoingRefresh = (async () => {
      const refresh = sessionStorage.getItem(REFRESH_KEY);
      if (!refresh) throw new Error('Session expired');
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) throw new Error('Session expired');
      setTokens(await response.json() as Tokens);
    })().finally(() => { ongoingRefresh = null; });
  }
  return ongoingRefresh;
}

async function request<T>(path: string, options: RequestInit = {}, retry = true, responseType: 'json' | 'blob' = 'json'): Promise<T> {
  const token = sessionStorage.getItem(ACCESS_KEY);
  const response = await fetch(`${BASE}${path}`, {
    ...options,
    headers: { Accept: responseType === 'blob' ? 'image/webp' : 'application/json', 'Accept-Language': document.documentElement.lang,
      ...(options.body && !(options.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
      ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (response.status === 401 && retry && token && !['/auth/login', '/auth/register', '/auth/tenant/register', '/auth/refresh', '/auth/logout'].includes(path)) {
    try { await renew(); return request<T>(path, options, false, responseType); }
    catch { setTokens(null); window.dispatchEvent(new Event('proptech-session-expired')); }
  }
  if (!response.ok) {
    const problem: { detail?: unknown } = await response.json().catch(() => ({}));
    const message = typeof problem.detail === 'string' ? problem.detail : JSON.stringify(problem.detail ?? `HTTP ${response.status}`);
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return responseType === 'blob' ? await response.blob() as T : await response.json() as T;
}

export function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  return request<T>(path, options);
}

export function apiBlob(path: string): Promise<Blob> {
  return request<Blob>(path, {}, true, 'blob');
}

export function photoPath(url: string): string {
  return url.replace(/^\/api\/v1/, '');
}
