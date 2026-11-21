import { NextResponse } from 'next/server';
import { z } from 'zod';
import { serverApi } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { ApiError } from '@/lib/api/errors';
import { setSession } from '@/lib/auth/cookies';
import type { LoginResponse, SessionResponse, UserResponse } from '@/lib/api/types';

export const runtime = 'nodejs';

const googleSchema = z.object({
  credential: z.string().min(10).max(20000),
});

/** Exchanges a Google Identity Services credential for an ordinary backend session. */
export async function POST(request: Request) {
  try {
    const parsed = googleSchema.safeParse(await request.json().catch(() => null));
    if (!parsed.success) {
      return NextResponse.json(
        { success: false, error: 'Invalid Google credential', detail: null, code: 'validation_error' },
        { status: 422 },
      );
    }

    const { data } = await serverApi('/auth/google', {
      method: 'POST',
      body: JSON.stringify(parsed.data),
    });

    // Accept the standard login envelope; a session-shaped response is tolerated
    // so the BFF remains compatible with either documented backend variant.
    const payload = data as Partial<LoginResponse> & {
      user?: UserResponse;
      csrfToken?: string;
      expires_in?: number;
    };
    if (!payload?.user) {
      throw new ApiError(502, 'Google sign-in did not return a user.');
    }

    const expiresIn = payload.expires_in ?? 3600;
    let csrfToken: string;
    if (typeof payload.access_token === 'string' && payload.access_token) {
      csrfToken = await setSession(payload.access_token, expiresIn);
    } else if (typeof payload.csrfToken === 'string' && payload.csrfToken) {
      csrfToken = payload.csrfToken;
    } else {
      throw new ApiError(502, 'Google sign-in did not return a session.');
    }

    const session: SessionResponse = {
      user: payload.user,
      csrfToken,
      expiresIn,
    };
    return NextResponse.json(session);
  } catch (error) {
    return errorResponse(error);
  }
}
