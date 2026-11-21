import 'server-only';

import { serverApi } from '@/lib/api/server';
import type { UserResponse } from '@/lib/api/types';
import { getSessionToken } from './cookies';

export async function getCurrentUser(): Promise<UserResponse | null> {
  const token = await getSessionToken();
  if (!token) return null;

  try {
    const { data } = await serverApi('/auth/me', { token });
    return data as UserResponse;
  } catch {
    return null;
  }
}
