const configured =
  process.env.API_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  'http://localhost:8000/api/v1';

export const API_BASE_URL = configured.replace(/\/+$/, '');
export const API_ROOT_URL = API_BASE_URL.replace(/\/api\/v1$/, '');

export const SESSION_COOKIE = 'smartquery_session';
export const CSRF_COOKIE = 'smartquery_csrf';
export const CSRF_HEADER = 'x-csrf-token';
