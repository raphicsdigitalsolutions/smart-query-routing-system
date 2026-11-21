import { NextResponse } from 'next/server';
import { CSRF_HEADER } from '@/lib/config';
import { clearSession, getCsrfCookie } from '@/lib/auth/cookies';
import { csrfTokensMatch } from '@/lib/auth/csrf';

export const runtime = 'nodejs';

export async function POST(request: Request) {
  const cookieToken = await getCsrfCookie();
  const headerToken = request.headers.get(CSRF_HEADER);
  if (!csrfTokensMatch(cookieToken, headerToken)) {
    return NextResponse.json(
      { success: false, error: 'Invalid CSRF token', code: 'invalid_csrf' },
      { status: 403 },
    );
  }

  await clearSession();
  return NextResponse.json({ success: true });
}
