'use client';

import { useCallback, useEffect, useMemo, useState, type ReactNode } from 'react';
import { authApi } from '@/lib/api/endpoints';
import { setCsrfToken as setApiCsrfToken } from '@/lib/api/client';
import { hasRole as checkRole } from '@/lib/auth/rbac';
import type { Role, SessionResponse, UserResponse } from '@/lib/api/types';
import { SessionContext, type SessionStatus } from '@/context/SessionContext';

interface SessionProviderProps {
  children: ReactNode;
  initialUser?: UserResponse | null;
}

export function SessionProvider({ children, initialUser = null }: SessionProviderProps) {
  const [user, setUser] = useState<UserResponse | null>(initialUser);
  const [status, setStatus] = useState<SessionStatus>(initialUser ? 'authenticated' : 'guest');
  const [csrfToken, setCsrfToken] = useState('');

  const clear = useCallback(() => {
    setUser(null);
    setStatus('guest');
    setCsrfToken('');
    setApiCsrfToken('');
  }, []);

  const apply = useCallback((session: SessionResponse | { user: UserResponse; csrfToken: string }) => {
    setUser(session.user);
    setCsrfToken(session.csrfToken);
    setApiCsrfToken(session.csrfToken);
    setStatus('authenticated');
  }, []);

  const refresh = useCallback(async () => {
    try {
      const session = await authApi.me();
      if (session.user) apply({ user: session.user, csrfToken: session.csrfToken });
      else clear();
    } catch {
      clear();
    }
  }, [apply, clear]);

  useEffect(() => {
    void refresh();
    const onUnauthorized = () => void refresh();
    window.addEventListener('auth:unauthorized', onUnauthorized);
    return () => window.removeEventListener('auth:unauthorized', onUnauthorized);
  }, [refresh]);

  const login = useCallback(
    async (email: string, password: string) => {
      const session = await authApi.login(email, password);
      apply(session);
      return session.user;
    },
    [apply],
  );

  const loginGoogle = useCallback(
    async (credential: string) => {
      const session = await authApi.google(credential);
      apply(session);
      return session.user;
    },
    [apply],
  );

  const register = useCallback(
    async (payload: { full_name: string; email: string; password: string }) => {
      const session = await authApi.register(payload);
      apply(session);
      return session.user;
    },
    [apply],
  );

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      clear();
    }
  }, [clear]);

  const value = useMemo(
    () => ({
      user,
      status,
      isAuthenticated: status === 'authenticated' && Boolean(user),
      csrfToken,
      login,
      loginGoogle,
      register,
      logout,
      refresh,
      hasRole: (...roles: Role[]) => checkRole(user, roles),
    }),
    [user, status, csrfToken, login, loginGoogle, register, logout, refresh],
  );

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}
