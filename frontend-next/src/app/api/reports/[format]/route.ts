import { NextResponse } from 'next/server';
import { serverApiRaw } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { getSessionToken } from '@/lib/auth/cookies';

export const runtime = 'nodejs';

const ALLOWED_FORMATS = new Set(['pdf', 'xlsx']);

/** Streams backend-generated ticket reports through the BFF without exposing the upstream URL. */
export async function GET(_request: Request, context: { params: Promise<{ format: string }> }) {
  const token = await getSessionToken();
  if (!token) {
    return NextResponse.json(
      { success: false, error: 'Not authenticated', detail: null, code: 'not_authenticated' },
      { status: 401 },
    );
  }

  const { format } = await context.params;
  if (!ALLOWED_FORMATS.has(format)) {
    return NextResponse.json(
      { success: false, error: 'Unsupported report format', detail: null, code: 'validation_error' },
      { status: 400 },
    );
  }

  try {
    const upstream = await serverApiRaw(`/reports/tickets.${format}`, { token });
    const headers = new Headers();
    const contentType = upstream.headers.get('content-type');
    headers.set('Content-Type', contentType ?? (format === 'pdf' ? 'application/pdf' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'));
    const disposition = upstream.headers.get('content-disposition');
    headers.set('Content-Disposition', disposition ?? `attachment; filename="tickets.${format}"`);
    headers.set('Cache-Control', 'no-store');
    return new NextResponse(upstream.body, { status: 200, headers });
  } catch (error) {
    return errorResponse(error);
  }
}
