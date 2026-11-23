import { NextResponse } from 'next/server';
import { z } from 'zod';
import { serverApi } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { setSession } from '@/lib/auth/cookies';
import type { LoginResponse, SessionResponse } from '@/lib/api/types';

export const runtime = 'nodejs';

const registerSchema = z.object({
  full_name: z.string().trim().min(2).max(120),
  email: z.string().trim().max(255).pipe(z.email()),
  password: z.string().min(12).max(128),
});

export async function POST(request: Request) {
  try {
    const parsed = registerSchema.safeParse(await request.json().catch(() => null));
    if (!parsed.success) {
      return NextResponse.json(
        { success: false, error: 'Validation error', detail: z.flattenError(parsed.error), code: 'validation_error' },
        { status: 422 },
      );
    }

    await serverApi('/auth/register', {
      method: 'POST',
      body: JSON.stringify(parsed.data),
    });
    const { data } = await serverApi('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: parsed.data.email, password: parsed.data.password }),
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
