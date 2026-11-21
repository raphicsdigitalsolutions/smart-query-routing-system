import 'server-only';

import { API_BASE_URL } from '@/lib/config';
import { ApiError, parseApiError } from './errors';

interface ServerApiResult {
  status: number;
  data: unknown;
}

interface ServerApiOptions extends RequestInit {
  token?: string;
}

export async function serverApi(path: string, options: ServerApiOptions = {}): Promise<ServerApiResult> {
  const { token, headers: incomingHeaders, ...init } = options;
  const headers = new Headers(incomingHeaders);
  headers.set('Accept', 'application/json');

  if (init.body !== undefined && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(0, 'Backend is unreachable.');
  }

  const data = await response.json().catch(() => null);
  if (!response.ok) throw parseApiError(response.status, data);
  return { status: response.status, data };
}

/**
 * Fetch an upstream response without consuming its body. Used by BFF routes that
 * stream binary payloads (for example ticket report downloads).
 */
export async function serverApiRaw(path: string, options: ServerApiOptions = {}): Promise<Response> {
  const { token, headers: incomingHeaders, ...init } = options;
  const headers = new Headers(incomingHeaders);
  headers.set('Accept', '*/*');
  if (token) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers,
      cache: 'no-store',
    });
  } catch {
    throw new ApiError(0, 'Backend is unreachable.');
  }

  if (!response.ok) {
    const payload = await response.clone().json().catch(() => null);
    throw parseApiError(response.status, payload);
  }
  return response;
}

export { ApiError };
