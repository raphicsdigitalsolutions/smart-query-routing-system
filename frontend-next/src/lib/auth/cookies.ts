import 'server-only';

import { randomBytes } from 'node:crypto';
import { cookies } from 'next/headers';
import { CSRF_COOKIE, SESSION_COOKIE } from '@/lib/config';

function cookieBase(maxAge: number) {
  return {
    httpOnly: false,
    sameSite: 'lax' as const,
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge,
  };
}

export function generateCsrfToken(): string {
  return randomBytes(32).toString('hex');
}

export async function getSessionToken(): Promise<string | null> {
  const store = await cookies();
  return store.get(SESSION_COOKIE)?.value ?? null;
}

export async function getCsrfCookie(): Promise<string | null> {
  const store = await cookies();
  return store.get(CSRF_COOKIE)?.value ?? null;
}

export async function ensureCsrfToken(): Promise<string> {
  const store = await cookies();
  const existing = store.get(CSRF_COOKIE)?.value;
  if (existing) return existing;

  const token = generateCsrfToken();
  store.set(CSRF_COOKIE, token, cookieBase(60 * 60 * 24));
  return token;
}

export async function setSession(token: string, expiresIn: number): Promise<string> {
  const store = await cookies();
  const maxAge = Math.max(1, expiresIn);
  const csrfToken = generateCsrfToken();

  store.set(SESSION_COOKIE, token, {
    ...cookieBase(maxAge),
    httpOnly: true,
  });
  store.set(CSRF_COOKIE, csrfToken, cookieBase(maxAge));
  return csrfToken;
}

export async function clearSession(): Promise<void> {
  const store = await cookies();
  store.delete(SESSION_COOKIE);
  store.delete(CSRF_COOKIE);
}
