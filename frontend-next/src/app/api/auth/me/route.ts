import { NextResponse } from 'next/server';
import { serverApi } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { getSessionToken } from '@/lib/auth/cookies';

export const runtime = 'nodejs';

export async function GET() {
  try {
    const token = await getSessionToken();
    if (!token) {
      return NextResponse.json(
        { success: false, error: 'Not authenticated', code: 'not_authenticated' },
        { status: 401 },
      );
    }
    const { data } = await serverApi('/auth/me', { token });
    return NextResponse.json(data);
  } catch (error) {
    return errorResponse(error);
  }
}
