import { NextResponse } from 'next/server';
import { z } from 'zod';
import { serverApi } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { setSession } from '@/lib/auth/cookies';
import type { LoginResponse, SessionResponse } from '@/lib/api/types';

export const runtime = 'nodejs';

const loginSchema = z.object({
  email: z.string().trim().min(1).max(255),
  password: z.string().min(1).max(128),
});

export async function POST(request: Request) {
  try {
    const parsed = loginSchema.safeParse(await request.json().catch(() => null));
    if (!parsed.success) {
      return NextResponse.json(
        { success: false, error: 'Validation error', detail: z.flattenError(parsed.error), code: 'validation_error' },
        { status: 422 },
      );
    }

    const { data } = await serverApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify(parsed.data),
    });
    const login = data as LoginResponse;
    const csrfToken = await setSession(login.access_token, login.expires_in);

    const session: SessionResponse = {
      user: login.user,
      csrfToken,
      expiresIn: login.expires_in,
    };
    return NextResponse.json(session);
  } catch (error) {
    return errorResponse(error);
  }
}
