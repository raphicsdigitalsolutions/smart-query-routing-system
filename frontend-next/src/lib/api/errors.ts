export interface ApiErrorBody {
  success?: false;
  error?: string;
  detail?: unknown;
  code?: string | null;
}

export class ApiError extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown, code: string | null = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
    this.code = code;
  }
}

export function parseApiError(status: number, payload: unknown): ApiError {
  const body = (payload && typeof payload === 'object' ? payload : {}) as ApiErrorBody;
  const message =
    (typeof body.error === 'string' && body.error.trim()) ||
    `Request failed with status ${status}`;
  return new ApiError(status, message, body.detail, body.code ?? null);
}

export function getApiErrorMessage(error: unknown, fallback = 'Something went wrong. Please try again.'): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) {
    if (error.message === 'Failed to fetch' || error.name === 'TypeError') {
      return 'Backend is unreachable. Check that the FastAPI service is running.';
    }
    return error.message || fallback;
  }
  return fallback;
}
