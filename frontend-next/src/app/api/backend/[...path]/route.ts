import { NextResponse } from 'next/server';
import { serverApi } from '@/lib/api/server';
import { errorResponse } from '@/lib/api/route';
import { clearSession, getCsrfCookie, getSessionToken } from '@/lib/auth/cookies';
import { csrfTokensMatch } from '@/lib/auth/csrf';
import { CSRF_HEADER } from '@/lib/config';

export const runtime = 'nodejs';

const SAFE_METHODS = new Set(['GET', 'HEAD', 'OPTIONS']);

type RouteContext = { params: Promise<{ path: string[] }> };

async function handleRequest(request: Request, context: RouteContext) {
  const method = request.method.toUpperCase();
  const token = await getSessionToken();

  if (!token) {
    return NextResponse.json(
      { success: false, error: 'Not authenticated', detail: null, code: 'not_authenticated' },
      { status: 401 },
    );
  }

  if (!SAFE_METHODS.has(method)) {
    const cookieToken = await getCsrfCookie();
    if (!csrfTokensMatch(cookieToken, request.headers.get(CSRF_HEADER))) {
      return NextResponse.json(
        { success: false, error: 'Invalid CSRF token', detail: null, code: 'invalid_csrf' },
        { status: 403 },
      );
    }
  }

  const { path } = await context.params;
  const search = new URL(request.url).search;
  const target = `/${path.map((segment) => encodeURIComponent(segment)).join('/')}${search}`;

  try {
    const contentType = request.headers.get('content-type');
    // Multipart bodies carry raw file bytes; text() would corrupt them via UTF-8 decoding.
    const isMultipart = contentType?.toLowerCase().startsWith('multipart/form-data') ?? false;
    const body = SAFE_METHODS.has(method)
      ? undefined
      : isMultipart
        ? await request.arrayBuffer()
        : await request.text();
    const { status, data } = await serverApi(target, {
      method,
      token,
      body: body ? body : undefined,
      headers: contentType ? { 'Content-Type': contentType } : undefined,
    });

    if (data === null || data === undefined) {
      return new NextResponse(null, { status });
    }
    return NextResponse.json(data, { status });
  } catch (error) {
    if (error instanceof Error && error.message === 'Not authenticated') {
      await clearSession();
    }
    const response = errorResponse(error);
    if (response.status === 401) await clearSession();
    return response;
  }
}

export const GET = handleRequest;
export const POST = handleRequest;
export const PATCH = handleRequest;
export const DELETE = handleRequest;
export const OPTIONS = handleRequest;
