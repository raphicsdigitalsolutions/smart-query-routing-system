import { NextResponse } from 'next/server';
import { API_ROOT_URL } from '@/lib/config';
import { errorResponse } from '@/lib/api/route';
import { ApiError, parseApiError } from '@/lib/api/errors';

export const runtime = 'nodejs';

export async function GET() {
  try {
    let response: Response;
    try {
      response = await fetch(`${API_ROOT_URL}/health`, { cache: 'no-store' });
    } catch {
      throw new ApiError(0, 'Backend is unreachable.');
    }
    const data = await response.json().catch(() => null);
    if (!response.ok) throw parseApiError(response.status, data);
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    return errorResponse(error);
  }
}
