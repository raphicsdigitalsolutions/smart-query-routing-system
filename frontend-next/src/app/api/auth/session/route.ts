import { NextResponse } from 'next/server';
import { serverApi } from '@/lib/api/server';
import { clearSession, ensureCsrfToken, getSessionToken } from '@/lib/auth/cookies';
import type { SessionProbeResponse, UserResponse } from '@/lib/api/types';

export const runtime = 'nodejs';

export async function GET() {
  const csrfToken = await ensureCsrfToken();
  const token = await getSessionToken();

  if (!token) {
    const guest: SessionProbeResponse = { user: null, csrfToken, expiresIn: null };
    return NextResponse.json(guest);
  }

  try {
    const { data } = await serverApi('/auth/me', { token });
    const session: SessionProbeResponse = {
      user: data as UserResponse,
      csrfToken,
      expiresIn: null,
    };
    return NextResponse.json(session);
  } catch {
    await clearSession();
    const guest: SessionProbeResponse = { user: null, csrfToken, expiresIn: null };
    return NextResponse.json(guest);
  }
}
