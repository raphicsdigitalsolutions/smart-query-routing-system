'use client';

import { createContext } from 'react';
import type { Role, UserResponse } from '@/lib/api/types';

export type SessionStatus = 'loading' | 'authenticated' | 'guest';

export interface SessionContextValue {
  user: UserResponse | null;
  status: SessionStatus;
  isAuthenticated: boolean;
  csrfToken: string;
  login: (email: string, password: string) => Promise<UserResponse>;
  loginGoogle: (credential: string) => Promise<UserResponse>;
  register: (payload: { full_name: string; email: string; password: string }) => Promise<UserResponse>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
  hasRole: (...roles: Role[]) => boolean;
}

export const SessionContext = createContext<SessionContextValue | null>(null);
