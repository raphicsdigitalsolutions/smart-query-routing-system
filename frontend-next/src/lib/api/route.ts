import 'server-only';

import { NextResponse } from 'next/server';
import { ApiError } from './errors';

export function errorResponse(error: unknown): NextResponse {
  if (error instanceof ApiError) {
    const status = error.status > 0 && error.status < 600 ? error.status : 503;
    return NextResponse.json(
      {
        success: false,
        error: error.message,
        detail: error.detail ?? null,
        code: error.code || (status === 503 ? 'backend_unavailable' : null),
      },
      { status },
    );
  }
  return NextResponse.json(
    {
      success: false,
      error: 'Internal server error',
      detail: null,
      code: 'internal_error',
    },
    { status: 500 },
  );
}
